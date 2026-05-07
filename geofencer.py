import netifaces
import signal
import socket
import sys
import yamale
from argparse import ArgumentParser
from cdp import *
from datetime import datetime
from threading import Thread
from shapely import Polygon, Point
from time import sleep

SCHEMA_FILEPATH = './geofencer_config_schema.yaml'
CDP_PACKET_MAX_SIZE = 65536
DEFAULT_HYSTERESIS = 0.15
DEFAULT_OUTPUT_INTERVAL = 10
DEFAULT_PRINT_OUTPUT_FLAG = True
Z_MIN_INDEX = 0
Z_MAX_INDEX = 1
ZONE_ID_START = 1

# config keys must match the schema
ETHERNET_SETTINGS_KEY = 'Ethernet Settings'
INPUT_STREAM_KEY      = 'Input'
OUTPUT_STREAM_KEY     = 'Output'
IP_KEY                = 'IP'
PORT_KEY              = 'Port'
INTERFACE_KEY         = 'Interface'
OUTPUT_INTERVAL_KEY   = 'Output Interval'
PRINT_OUTPUT_KEY      = 'Print Output'
ZONES_KEY             = 'Zones'
VERTICES_KEY          = 'Vertices'
Z_RANGE_KEY           = 'Z Range'
HYSTERESIS_KEY        = 'Hysteresis'

class Zone:
    def __init__(self, name, zone_id, vertices, z_range, hysteresis_z_range, boundary, hysteresis_boundary):
        self.name = name
        self.id = zone_id
        self.vertices = vertices
        self.z_range = z_range
        self.hysteresis_z_range = hysteresis_z_range
        self.boundary = boundary
        self.hysteresis_boundary = hysteresis_boundary

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

def determine_zones(posn_data_item):
    tag_serial_number = posn_data_item.serial_number

    # determine the zones the tag is currently in
    tag_xy = Point(mm_to_m(posn_data_item.x), mm_to_m(posn_data_item.y))
    tag_current_zones = []
    for zone in g_zones:
        # Is the tag already in this zone? If so, use the hysteresis zone.  If not, use the nominal zone
        if ((tag_serial_number in g_tag_zone_info_map) and (zone.id in g_tag_zone_info_map[tag_serial_number])):
            within_xy_bounds = zone.hysteresis_boundary.contains(tag_xy)
            within_z_bounds = zone.hysteresis_z_range[Z_MIN_INDEX] <= mm_to_m(posn_data_item.z) <= zone.hysteresis_z_range[Z_MAX_INDEX]
        else:
            within_xy_bounds = zone.boundary.contains(tag_xy)
            within_z_bounds = zone.z_range[Z_MIN_INDEX] <= mm_to_m(posn_data_item.z) <= zone.z_range[Z_MAX_INDEX]

        if within_xy_bounds and within_z_bounds:
            tag_current_zones.append(zone.id)

    if (tag_serial_number not in g_tag_zone_info_map) or (g_tag_zone_info_map[tag_serial_number] != tag_current_zones):
        # Update stored zone list for this tag
        g_tag_zone_info_map[tag_serial_number] = tag_current_zones

        # print new zone info to output
        print_output(f'{datetime.now()} - {tag_serial_number}: {g_tag_zone_info_map[tag_serial_number]}')

        # send new CDP for this tag
        tag_zone_info = TagZoneInfo()
        tag_zone_info.serial_number = tag_serial_number
        tag_zone_info.zone_list = tag_current_zones
        send_cdp([tag_zone_info])

# SIGINT signal handler
def signal_handler(signal, frame):
    global g_cdp_output_running
    g_cdp_output_running = False
    g_cdp_output_thread.join()
    g_receive_socket.close()
    g_send_socket.close()
    print_output('Done')
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
    print(str(e))
    sys.exit(1)

# extract config from yamale.make_data output
g_config = config_data[0][0]

if OUTPUT_INTERVAL_KEY in g_config:
    g_output_interval = g_config[OUTPUT_INTERVAL_KEY]
else:
    g_output_interval = DEFAULT_OUTPUT_INTERVAL

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
    send_interface = g_config[ETHERNET_SETTINGS_KEY][OUTPUT_STREAM_KEY][INTERFACE_KEY]
else:
    g_send_ip = receive_ip
    g_send_port = receive_port
    send_interface = receive_interface

g_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
g_send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
g_send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
g_send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
g_send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

if sys.platform == 'win32':
    g_send_socket.bind((send_interface, g_send_port)) #bind to a free port
else:
    g_send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    g_send_socket.bind((send_interface, g_send_port)) #bind to a free port

g_send_socket.setblocking(False)

print_output(f'Sending on IP: {g_send_ip}, Port: {g_send_port}, Interface: {send_interface}')

# ==================== VALIDATE ZONES, POPULATE ZONE DATA ====================
invalid_zone_detected = False
g_zones = []
g_zone_data_items = []
zone_id = ZONE_ID_START
for zone_name, zone_data in g_config[ZONES_KEY].items():
    zone_vertices = zone_data[VERTICES_KEY]
    hysteresis_value = zone_data[HYSTERESIS_KEY] if (HYSTERESIS_KEY in zone_data) else DEFAULT_HYSTERESIS
    z_range = zone_data[Z_RANGE_KEY]

    # zone boundaries are created as Polygon objects from the shapely library
    zone_boundary = Polygon(zone_vertices)

    # validate zone coordinates
    if not zone_boundary.is_simple:
        print(f'ERROR: Provided zone "{zone_name}" intersects itself! Please check the order of the provided vertices.')
        invalid_zone_detected = True
        continue

    # print zone name to ID mapping, output zone info CDP data items
    print_output(f'{zone_id:>5}: {zone_name}')

    # apply hysteresis to the boundary using the shapely.buffer function
    hysteresis_zone_boundary = zone_boundary.buffer(hysteresis_value)

    # create z range with hysteresis applied
    hysteresis_z_range = [z_range[Z_MIN_INDEX] - hysteresis_value, z_range[Z_MAX_INDEX] + hysteresis_value]

    # create Zone object and add it to the g_zones list
    g_zones.append(Zone(
        name                = zone_name,
        vertices            = zone_vertices,
        zone_id             = zone_id,
        z_range             = z_range,
        hysteresis_z_range  = hysteresis_z_range,
        boundary            = zone_boundary,
        hysteresis_boundary = hysteresis_zone_boundary
    ))

    # create GeofencerZoneInfo CDP data item
    data_item = GeofencerZoneInfo()
    data_item.zone_id = zone_id
    data_item.zone_name = zone_name
    data_item.z_min = m_to_mm(z_range[Z_MIN_INDEX])
    data_item.z_max = m_to_mm(z_range[Z_MAX_INDEX])
    data_item.hysteresis = m_to_mm(hysteresis_value)

    # the data item vertices attribute will be assigned by mapping the config list of vertices to a list of XyCoordinate cdp-py structures
    zone_vertices_mm = list(map(lambda vertex: XyCoordinate(m_to_mm(vertex[0]), m_to_mm(vertex[1])), zone_vertices))
    data_item.vertices = zone_vertices_mm

    # send data item to output stream
    send_cdp([data_item])

    # append data item to global list for later usage
    g_zone_data_items.append(data_item)

    # increment zone ID
    zone_id += 1

if invalid_zone_detected:
    print('Aborting')
    sys.exit(1)

# ==================== OUTPUT CDP DATA ====================
g_tag_zone_info_map = {} # This will be a mapping of tag serial numbers to the zones that tag is in according to its most recent position data
g_cdp_output_running = True
def cdp_output_all_data():
    # simple while loop that just sends out the zone info and the current tag zones
    while g_cdp_output_running:
        sleep(g_output_interval)

        for zone_info in g_zone_data_items:
            send_cdp([zone_info])

        for serial_number, zones in g_tag_zone_info_map.items():
            tag_zone_info = TagZoneInfo()
            tag_zone_info.serial_number = serial_number
            tag_zone_info.zone_list = zones
            send_cdp([tag_zone_info])

g_cdp_output_thread = Thread(target=cdp_output_all_data)

# ==================== MAIN CODE - LISTEN FOR POSITIONS, DETERMINE ZONES ====================
# start cdp output thread
g_cdp_output_thread.start()

# main loop
while True:
    data, address = g_receive_socket.recvfrom(CDP_PACKET_MAX_SIZE)
    cdp_packet = CDP(data)

    for posn in cdp_packet.data_items_by_type.get(PositionV3.type, []):
        determine_zones(posn)
