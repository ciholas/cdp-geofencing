# Ciholas, Inc. - www.ciholas.com 
# Licensed under: creativecommons.org/licenses/by/4.0

import argparse

from cdp_handler import CdpHandler
from config_handler import ConfigHandler

parser = argparse.ArgumentParser(description='Track tags in relation to given zones')
parser.add_argument('--file', type=str, help='The name of the YAML file to get zones from. (ie: my_zone_file.yaml)', default='geofencing_config.yaml')
args = parser.parse_args()

if __name__ == '__main__':
    config = ConfigHandler(args.file)
    network_connection = CdpHandler(config.ethernet_settings)
    while True:
        try:
            network_connection.process_data(config.zones, config.hysteresis_value)
        except KeyboardInterrupt:
            for tag in network_connection.known_tags.values():
                tag.reset_led_behavior()
            network_connection.close_sockets()
            raise
