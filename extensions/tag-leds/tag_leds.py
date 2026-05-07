import json
import netifaces
import requests
import warnings
import signal
import socket
import sys
import yamale
from argparse import ArgumentParser
from cdp import *

SCHEMA_FILEPATH           = './tag_led_schema.yaml'
CDP_PACKET_MAX_SIZE       = 65536
CONTENT_TYPE              = {'Content-Type': 'application/json'}
ACTION                    = 'set_led'
DEFAULT_PRINT_OUTPUT_FLAG = True
DEFAULT_LED_FLASHING_FLAG = False # By default, LEDs will not flash
DEFAULT_LED_TIMEOUT       = 30    # By default, LEDs on tags will timeout after 30 seconds

# config keys must match the schema
ETHERNET_SETTINGS_KEY = 'Ethernet Settings'
INPUT_KEY             = 'Input'
IP_KEY                = 'IP'
PORT_KEY              = 'Port'
INTERFACE_KEY         = 'Interface'
OUTPUT_KEY            = 'Output'
CUWB_URL_KEY          = 'CUWB URL'
CUWBNET_KEY           = 'CUWBNet'
LED_FLASHING_KEY      = 'LED Flashing'
LED_TIMEOUT_KEY       = 'LED Timeout'
ZONES_KEY             = 'Zones'
DEFAULT_COLOR_KEY     = 'Default Color'
COLOR_KEY             = 'Color'
PRINT_OUTPUT_KEY      = 'Print Output'

class Zone:
    def __init__(self, zone_id=0, color='', info_received=False):
        self.id = zone_id
        self.color = color
        self.info_received = info_received

def check_response(status_code, message, request_type):
    try:
        if (status_code < 200) or (status_code > 299):
            warnings.warn(UserWarning('JSON {}: Error Message {} - {}'.format(request_type, status_code, message)))
        return status_code, message
    except ValueError:
        warnings.warn(UserWarning('JSON {}: Error Message {} - Unable to decode message'.format(request_type, status_code)))
        return status_code

def post_request(url, body):
    response = requests.post(url, data=body, headers=CONTENT_TYPE)
    return check_response(response.status_code, response.json(), 'Post Request')

def send_device_command(serial_number, args):
    url = '{}/cuwbnets/{}/devices/{}/action'.format(g_cuwb_url, g_cuwbnet_name, serial_number)
    body = json.dumps(args)
    return post_request(url, body)

def determine_tag_color(zones):
    tag_color_str = g_config[DEFAULT_COLOR_KEY]
    # priority of tag color is assigned highest to lowest in the order of the zones of the config file
    for zone_name, zone_config in g_config[ZONES_KEY].items():
        zone_id = g_zone_name_info_mapping[zone_name].id
        if zone_id in zones:
            tag_color_str = zone_config[COLOR_KEY]
            break
    return tag_color_str

def print_output(msg):
    if g_print_output:
        print(msg)

def signal_handler(signal, frame):
    g_receive_socket.close()
    print('Done')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ==================== PARSE ARGUMENTS ====================
arg_parser = ArgumentParser()
arg_parser.add_argument('config_file')
args = arg_parser.parse_args()

# validate that the given config file fits the schema
config_data = yamale.make_data(args.config_file)
schema = yamale.make_schema(SCHEMA_FILEPATH)
try:
    yamale.validate(schema, config_data)
except ValueError as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)

# extract config from yamale.make_data output
g_config = config_data[0][0]

if PRINT_OUTPUT_KEY in g_config:
    g_print_output = g_config[PRINT_OUTPUT_KEY]
else:
    g_print_output = DEFAULT_PRINT_OUTPUT_FLAG

# create receive socket
receive_ip = g_config[ETHERNET_SETTINGS_KEY][INPUT_KEY][IP_KEY]
receive_port = g_config[ETHERNET_SETTINGS_KEY][INPUT_KEY][PORT_KEY]
receive_interface = g_config[ETHERNET_SETTINGS_KEY][INPUT_KEY][INTERFACE_KEY]

g_receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
g_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
g_receive_socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(receive_ip) + socket.inet_aton(receive_interface))

nic_name = None
for ifc in netifaces.interfaces():
    for ifc_info in netifaces.ifaddresses(ifc).get(netifaces.AF_INET, []):
        if 'addr' in ifc_info:
            if ifc_info['addr'] == receive_interface:
                nic_name = ifc
if nic_name is not None:
    g_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, nic_name.encode("utf-8"))

try:
    g_receive_socket.bind((receive_ip, receive_port))
    print_output(f'Listening on IP: {receive_ip}, Port: {receive_port}, Interface: {receive_interface}')
except:
    print(f'ERROR: Could not open socket - {receive_ip}:{receive_port}')
    sys.exit(1)

# extract output info
g_cuwbnet_name = g_config[ETHERNET_SETTINGS_KEY][OUTPUT_KEY][CUWBNET_KEY]
g_cuwb_url = g_config[ETHERNET_SETTINGS_KEY][OUTPUT_KEY][CUWB_URL_KEY]
print_output(f'Outputting LED commands to CUWBNet "{g_cuwbnet_name}" at address "{g_cuwb_url}"')

if LED_FLASHING_KEY in g_config:
    g_led_flashing = g_config[LED_FLASHING_KEY]
else:
    g_led_flashing = DEFAULT_LED_FLASHING_FLAG

if LED_TIMEOUT_KEY in g_config:
    g_led_timeout_s = g_config[LED_TIMEOUT_KEY]
else:
    g_led_timeout_s = DEFAULT_LED_TIMEOUT


# ================== RECEIVE ZONE ID's ====================
g_zone_name_info_mapping = {}

for zone_name, zone_info in g_config[ZONES_KEY].items():
    color = zone_info[COLOR_KEY]
    g_zone_name_info_mapping[zone_name] = Zone(color=color)

# listen for geofencer zone info data items until ID's for all zones in the config file are received
all_zone_info_received = False
while not all_zone_info_received:
    data, address = g_receive_socket.recvfrom(CDP_PACKET_MAX_SIZE)
    cdp_packet = CDP(data)

    for zone_info in cdp_packet.data_items_by_type.get(GeofencerZoneInfo.type, []):
        zone_name = zone_info.zone_name
        if zone_name in g_zone_name_info_mapping:
            g_zone_name_info_mapping[zone_name].id = zone_info.zone_id
            g_zone_name_info_mapping[zone_name].info_received = True

    # determine if we've received all zone info
    all_zone_info_received = True
    for zone in g_zone_name_info_mapping.values():
        all_zone_info_received = all_zone_info_received and zone.info_received

print_output('All zone info received')

# ==================== MAIN PROGRAM ====================
# this map will store serial numbers with currently assigned colors
g_tag_color_map = {}

# main loop
while True:
    data, address = g_receive_socket.recvfrom(CDP_PACKET_MAX_SIZE)
    cdp_packet = CDP(data)

    for tag_zone_info in cdp_packet.data_items_by_type.get(TagZoneInfo.type, []):
        serial_number = tag_zone_info.serial_number
        tag_color_str = determine_tag_color(tag_zone_info.zone_list)

        # if this tag color is already assigned to this tag, then continue without sending a new command
        if ((serial_number in g_tag_color_map) and (tag_color_str == g_tag_color_map[serial_number])):
            continue

        g_tag_color_map[serial_number] = tag_color_str

        device_command_json_args = {
            'action': ACTION,
            'color': tag_color_str.lower(),                    # make the string lowercase for JSON
            'mode': ('flash' if g_led_flashing else 'solid'),
            'timeout': g_led_timeout_s
        }

        send_device_command(serial_number, device_command_json_args)
