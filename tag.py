# Ciholas, Inc. - www.ciholas.com 
# Licensed under: creativecommons.org/licenses/by/4.0

from cdp import *

from zone import Line

class Tag:
    """Keeps track of a tag's breached zones and configures its LEDs when needed"""
    def __init__(self, serial_number, send_cdp_packet, possible_zones, hysteresis_value):
        self.serial_number = serial_number
        self.send_cdp_packet = send_cdp_packet
        self.possible_zones = possible_zones
        self.breached_zones = None
        self.required_consecutive_breaches = hysteresis_value
        self.consecutive_breaches = 0

    def detect_zone_breaches(self, point, network_time):
        """Figures out where the tag is in relation to each zone"""
        # To make the zone breach detection easier, the point is turned into a very long horizontal ray
        point_ray = Line((point), (point[0] + 999999999999999999999999, point[1]))
        inside_zone_list = []
        outside_name_list = []
        for zone in self.possible_zones:
            if zone.is_inside(point_ray):
                inside_zone_list.append(zone)
            else:
                outside_name_list.append(zone.name)
        self.update_zone_breaches(inside_zone_list, outside_name_list, network_time)

    def update_zone_breaches(self, new_breached_zones, unbreached_zones, network_time):
        """Checks to make sure the tag's zone breaches are up to date"""
        if self.breached_zones != new_breached_zones:
            self.consecutive_breaches += 1
            # For more accurate readings, the tag has to report numerous consecutive changes before any changes are accepted
            if self.consecutive_breaches == self.required_consecutive_breaches:
                print('Tag {} is inside of {} and outside of {} at network time {}.'.format(self.serial_number, ', '.join(map(str, new_breached_zones)), ', '.join(unbreached_zones), network_time))
                self.breached_zones = new_breached_zones
                if self.breached_zones == []:
                    self.reset_led_behavior()
                else:
                    self.set_tag_to_zone_colors()
        else:
            # The location change is no longer consecutive, so the count is reset
            self.consecutive_breaches = 0

    def set_tag_to_zone_colors(self):
        """Takes a list of breached zones and configures its LEDs accordingly"""
        item = SetDiagnosticLED()
        item.destination_group = CiholasSerialNumber(self.serial_number)
        zone_num = 0
        multi_zone_offset = 500 # For multiple zones, we need to space out the colors. The chosen spacing here is 500 ms
        for zone in self.breached_zones:
            # The multi_zone_offset spaces out commands out based off of how many LED commands we need
            item.add_led_states(zone_num * multi_zone_offset, multi_zone_offset, len(self.breached_zones) * multi_zone_offset, zone.color[0], zone.color[1], zone.color[2])
            zone_num += 1
        self.send_cdp_packet(item)

    def reset_led_behavior(self):
        """Resets LED behaviour by sending an empty LED command"""
        item = SetDiagnosticLED()
        item.destination_group = CiholasSerialNumber(self.serial_number)
        self.send_cdp_packet(item)
