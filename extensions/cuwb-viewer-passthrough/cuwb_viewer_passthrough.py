import netifaces
import signal
import socket
import sys
import yamale
from argparse import ArgumentParser
from cdp import *

SCHEMA_FILEPATH = './cuwb_viewer_passthrough_schema.yaml'
CDP_PACKET_MAX_SIZE = 65536
ZONE_NOT_IN_CONFIG_COLOR = [200, 200, 200] # For zones that we receive info on that aren't in the config file, they'll be assigned this color
TAG_COLOR_ALPHA_VALUE = 255  # Tags will be colored with this alpha value in the CUWB Viewer
ZONE_COLOR_ALPHA_VALUE = 128 # zones will be colored with this alpha value in the CUWB Viewer
RED_INDEX = 0
GREEN_INDEX = 1
BLUE_INDEX = 2
DEFAULT_PRINT_OUTPUT_FLAG = True

# config keys must match the schema
ETHERNET_SETTINGS_KEY = 'Ethernet Settings'
INPUT_STREAM_KEY      = 'Input'
OUTPUT_STREAM_KEY     = 'Output'
IP_KEY                = 'IP'
PORT_KEY              = 'Port'
INTERFACE_KEY         = 'Interface'
ZONES_KEY             = 'Zones'
DEFAULT_COLOR_KEY     = 'Default Color'
COLOR_KEY             = 'Color'
PRINT_OUTPUT_KEY      = 'Print Output'

class Zone:
    def __init__(self, zone_id=0, info_received=False, red=0, blue=0, green=0, z_min=0, z_max=0, vertices=[]):
        self.id = zone_id
        self.info_received = info_received
        self.red = red
        self.green = green
        self.blue = blue
        self.z_min = z_min
        self.z_max = z_max
        self.vertices = vertices

def send_cdp(msgs):
    send_packet = CDP()
    send_packet.add_data_items(msgs)
    g_send_socket.sendto(send_packet.encode(), (g_send_ip, g_send_port))

def m_to_mm(meters):
    return int(meters * 1000)

def mm_to_m(millimeters):
    return millimeters / 1000

def print_output(msg):
    if g_print_output:
        print(msg)

def determine_tag_color(zones):
    if DEFAULT_COLOR_KEY in g_config:
        tag_color = g_config[DEFAULT_COLOR_KEY]
    else:
        tag_color = None
    # priority of tag color is assigned highest to lowest in the order of the zones of the config file
    for zone_name, zone_config in g_config[ZONES_KEY].items():
        zone_id = g_zone_name_info_mapping[zone_name].id
        if zone_id in zones:
            tag_color = zone_config[COLOR_KEY]
            break
    return tag_color

def signal_handler(signal, frame):
    # send ClearObject data items for every zone
    for zone_name in g_zone_name_info_mapping.keys():
        clear_object_data_item = ClearObject()
        clear_object_data_item.name = zone_name
        send_cdp([clear_object_data_item])

    # send ClearDeviceColor data item for all devices
    clear_device_color_data_item = ClearDeviceColor()
    clear_device_color_data_item.serial_number = CiholasSerialNumber(0)
    clear_device_color_data_item.flags = 0x80 # clear all device colors
    send_cdp([clear_device_color_data_item])

    # close sockets
    g_receive_socket.close()
    g_send_socket.close()

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
receive_ip = g_config[ETHERNET_SETTINGS_KEY][INPUT_STREAM_KEY][IP_KEY]
receive_port = g_config[ETHERNET_SETTINGS_KEY][INPUT_STREAM_KEY][PORT_KEY]
receive_interface = g_config[ETHERNET_SETTINGS_KEY][INPUT_STREAM_KEY][INTERFACE_KEY]

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

# create transmit socket
if OUTPUT_STREAM_KEY in g_config[ETHERNET_SETTINGS_KEY]:
    g_send_ip = g_config[ETHERNET_SETTINGS_KEY][OUTPUT_STREAM_KEY][IP_KEY]
    g_send_port = g_config[ETHERNET_SETTINGS_KEY][OUTPUT_STREAM_KEY][PORT_KEY]
    g_send_interface = g_config[ETHERNET_SETTINGS_KEY][OUTPUT_STREAM_KEY][INTERFACE_KEY]
else:
    g_send_ip = receive_ip
    g_send_port = receive_port
    g_send_interface = receive_interface

g_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
g_send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
g_send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
g_send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
g_send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

if sys.platform == 'win32':
    g_send_socket.bind((g_send_interface, g_send_port)) #bind to a free port
else:
    g_send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    g_send_socket.bind((g_send_interface, g_send_port)) #bind to a free port

g_send_socket.setblocking(False)

print_output(f'Sending on IP: {g_send_ip}, Port: {g_send_port}, Interface: {g_send_interface}')

# ================== RECEIVE ZONE INFORMATION ====================
g_zone_name_info_mapping = {}

for zone_name, zone_info in g_config[ZONES_KEY].items():
    zone_red_value = zone_info[COLOR_KEY][RED_INDEX]
    zone_green_value = zone_info[COLOR_KEY][GREEN_INDEX]
    zone_blue_value = zone_info[COLOR_KEY][BLUE_INDEX]
    g_zone_name_info_mapping[zone_name] = Zone(red=zone_red_value, green=zone_green_value, blue=zone_blue_value)

# listen for geofencer zone info data items until ID's for all zones in the config file are received
all_zone_info_received = False
while not all_zone_info_received:
    data, address = g_receive_socket.recvfrom(CDP_PACKET_MAX_SIZE)
    cdp_packet = CDP(data)

    for zone_info in cdp_packet.data_items_by_type.get(GeofencerZoneInfo.type, []):
        zone_name = zone_info.zone_name
        if zone_name not in g_zone_name_info_mapping:
            # we will still send a DrawPrism data item for this zone even though it's not in the config
            g_zone_name_info_mapping[zone_name] = Zone(red=ZONE_NOT_IN_CONFIG_COLOR[RED_INDEX], green=ZONE_NOT_IN_CONFIG_COLOR[GREEN_INDEX], blue=ZONE_NOT_IN_CONFIG_COLOR[BLUE_INDEX])

        g_zone_name_info_mapping[zone_name].id = zone_info.zone_id
        g_zone_name_info_mapping[zone_name].z_min = zone_info.z_min
        g_zone_name_info_mapping[zone_name].z_max = zone_info.z_max
        g_zone_name_info_mapping[zone_name].vertices = zone_info.vertices
        g_zone_name_info_mapping[zone_name].info_received = True

    # determine if we've received all zone info
    all_zone_info_received = True
    for zone in g_zone_name_info_mapping.values():
        all_zone_info_received = all_zone_info_received and zone.info_received

print_output('All zone info received')

# ================== OUTPUT DRAW PRISM DATA ITEMS ==================
for name, info in g_zone_name_info_mapping.items():
    # create DrawPrism data item
    draw_prism_data_item = DrawPrism()
    draw_prism_data_item.name = name
    draw_prism_data_item.red = info.red
    draw_prism_data_item.green = info.green
    draw_prism_data_item.blue = info.blue
    draw_prism_data_item.alpha = ZONE_COLOR_ALPHA_VALUE
    draw_prism_data_item.z_min = info.z_min
    draw_prism_data_item.z_max = info.z_max
    draw_prism_data_item.vertices = info.vertices
    send_cdp([draw_prism_data_item])

# ================== MAIN PROGRAM ====================
# this map will store serial numbers with currently assigned colors
g_tag_color_map = {}

# main loop
while True:
    data, address = g_receive_socket.recvfrom(CDP_PACKET_MAX_SIZE)
    cdp_packet = CDP(data)

    for tag_zone_info in cdp_packet.data_items_by_type.get(TagZoneInfo.type, []):
        serial_number = tag_zone_info.serial_number
        tag_color = determine_tag_color(tag_zone_info.zone_list)

        # if this tag color is already assigned to this tag, then continue without sending a new color data item
        if ((serial_number in g_tag_color_map) and (tag_color == g_tag_color_map[serial_number])):
            continue

        g_tag_color_map[serial_number] = tag_color

        if tag_color != None:
            tag_color_packet = DeviceColor()
            tag_color_packet.serial_number = serial_number
            tag_color_packet.red = tag_color[RED_INDEX]
            tag_color_packet.green = tag_color[GREEN_INDEX]
            tag_color_packet.blue = tag_color[BLUE_INDEX]
            tag_color_packet.alpha = TAG_COLOR_ALPHA_VALUE
        else:
            tag_color_packet = ClearDeviceColor()
            tag_color_packet.serial_number = serial_number
            tag_color_packet.flags = 0

        send_cdp([tag_color_packet])
