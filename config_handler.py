# Ciholas, Inc. - www.ciholas.com 
# Licensed under: creativecommons.org/licenses/by/4.0

import sys

import yaml

from zone import Zone


class ConfigHandler:
    """Converts a yaml file into a Python object"""
    def __init__(self, file_name):
        try:
            with open(file_name, 'r') as open_file:
                config_dict = yaml.safe_load(open_file)
        except Exception as e:
            print('There was an error loading the given file. Ensure file name was entered correctly and was a YAML file.')
            print(e)
            sys.exit(1)
        try:
            zone_dict = config_dict['Zones']
        except Exception:
            print('Zones not found. Please make sure zones are present and formatted correctly.')
            sys.exit(1)
        try:
            self.ethernet_settings = config_dict['Ethernet_Settings']
        except Exception:
            print('Network info not found. Please make sure info is present and formatted correctly.')
            sys.exit(1)
        try:
            self.hysteresis_value = int(config_dict['Hysteresis_Value'])
        except Exception:
            print('Hysteresis Value not found. The default value of 5 will be used.')
            self.hysteresis_value = 5
        if self.hysteresis_value < 0:
            print('Hysteresis value is less than 0. The default value of 5 will be used.')
            self.hysteresis_value = 5
        zone_list = []
        for name, data in zone_dict.items():
            if type(name) is not str:
                print('Zone {} rejected. Zone name was not a string'.format(name))
            else:
                try:
                    vertices = data['Vertices']
                    color = data['RGB']
                except Exception:
                    print('Zone {} rejected. Vertices and RGB Color were either named incorrectly or not present'.format(name))
                else:
                    if type(color) != list:
                        print('Zone {} rejected. RGB values were not in a list'.format(name))
                    elif len(color) != 3:
                        print('Zone {} rejected. RGB list should consist of 3 values'.format(name))
                    elif type(vertices) != list:
                        print('Zone {} rejected. Zone points were not in a list'.format(name))
                    elif len(vertices) < 3:
                        print('Zone {} rejected. Not enough points to make a polygon'.format(name))
                    else:
                        vertex_num = 0
                        for vertex in vertices:
                            vertex_num += 1
                            if type(vertex) != list:
                                print('Zone {} rejected. Each point needs to be a list in the form of [x, y]'.format(name))
                                break
                            elif len(vertex) != 2:
                                print('Zone {} rejected. Each point should have exactly two coordinates'.format(name))
                                break
                            elif (type(vertex[0]) is not float and type(vertex[0]) is not int) or (type(vertex[1]) is not float and type(vertex[1]) is not int):
                                print('Zone {} rejected. A point should consist of two floats and/or integers'.format(name))
                                break
                            elif vertex_num == len(vertices):
                                print('Zone {} accepted.'.format(name))
                                zone_list.append(Zone(name, vertices, color))
        if len(zone_list) > 0:
            self.zones = zone_list
        else:
            print('Error: There were no usable zones.')
            sys.exit(1)
