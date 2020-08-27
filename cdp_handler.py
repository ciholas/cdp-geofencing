# Ciholas, Inc. - www.ciholas.com 
# Licensed under: creativecommons.org/licenses/by/4.0

import socket
import sys

from cdp import *

from tag import Tag

class CdpHandler:
    """This class handles all functions related to communicating with the NetApp"""
    def __init__(self, ethernet_settings):
        self.known_tags = {}
        try:
            cuwb_input = ethernet_settings['CUWB_Input']
            cuwb_output = ethernet_settings['CUWB_Output']
        except Exception:
            print('''
            Error finding Ethernet settings. Make sure the config file looks similar to the following:

            Ethernet_Settings:
              CUWB_Input:
                IP: 239.255.76.67
                Port: 7667
                Interface: 169.254.177.218
              CUWB_Output:
                IP: 239.255.76.67
                Port: 7668
                Interface: 169.254.177.218
            ''')
        self.cuwb_input = cuwb_input
        self.cuwb_output = cuwb_output
        try:
            self.listen_socket = self.create_socket(cuwb_output['IP'], cuwb_output['Port'], cuwb_output['Interface'])
            self.send_socket = self.create_socket(cuwb_input['IP'], cuwb_input['Port'], cuwb_input['Interface'])
        except Exception:
            print('There was an error setting up the sockets. Please check your Ethernet settings.')
            sys.exit(1)

    def create_socket(self, ip, port, interface):
        """Creates a UDP socket based on the given info"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(ip)+socket.inet_aton(interface))
        return sock

    def close_sockets(self):
        """Closes both sockets created by this class. Meant to be used at the end of the script."""
        self.listen_socket.close()
        self.send_socket.close()

    def process_data(self, zone_set, hysteresis_value):
        """Retrieves the tag's location and passes it on to the tag object for further handling"""
        data, address = self.listen_socket.recvfrom(65536)
        try:
            cdp_packet = cdp.CDP(data)
        except ValueError as e:
            if str(e) == 'Incomplete CDP Packet' or 'Unrecognized String' in str(e) or 'Packet Size Error' in str(e):
                print(e)
            else:
                raise
        else:
            # Process Position V3 (0x0135) data items to detect zone breaches
            for pos_item in cdp_packet.data_items_by_type.get(0x0135, []):
                # If this is the first data from a tag, it creates an object for the tag
                if pos_item.serial_number not in self.known_tags:
                    self.known_tags[pos_item.serial_number] = Tag(pos_item.serial_number, self.send_cdp_packet, zone_set, hysteresis_value)
                self.known_tags[pos_item.serial_number].detect_zone_breaches((pos_item.x, pos_item.y), pos_item.network_time)

    def send_cdp_packet(self, item):
        """Adds a data item to a CDP packet and sends it over the input channel"""
        cdp_packet = CDP()
        cdp_packet.add_data_item(item)
        self.send_socket.sendto(cdp_packet.encode(), (self.cuwb_input['IP'], self.cuwb_input['Port']))
