# Tag LEDs
The tag-led geofencer extension allows you to assign colors to all zones in your configuration file. When a tag enters that zone, its LED will display that color for a configurable period of time.

## Usage
All geofencer dependencies need to be installed before running this program. Follow the instructions in the geofencer README for setting up a python virtual environment and installing packages.

The tag-led extension is run with the following command:
```
python tag_leds.py <config file>
```

## Config File
Like the geofencer itself, this program accepts its arguments in the form of a YAML configuration file. It also performs configuration file verification against the schema file at startup. An example configuration file is provided as a starting point.

### Ethernet
#### Input
This program listens for Geofencer Zone Info and Tag Zone Info CDP data items, which are output by the geofencer main program. Therefore, the input stream definition should match the output settings of your geofencer configuration file.

#### Output
The format of the output section is different from the geofencer and the cuwb-viewer passthrough. Rather than sending out CDP packets, the tag-led extension uses the CUWB Manager API to control the tag LEDs, so the required CUWB Manager connection settings must be provided.

* CUWB URL: The URL of the CUWB Manager, typically `http://localhost:5000` unless the CUWB Manager is running on a different PC.
* CUWBNet: The name of the CUWBNet for which the geofencer is running.

### Zones
This list of zones is formatted similarly to the geofencer configuration file. However, instead of providing vertices, z range, and hysteresis, you only provide a `Color` argument. For this extension, the `Color` argument must be one of the following strings (case-insensitive):
* red
* green
* blue
* magenta
* yellow
* white

These are the colors supported by the API, so the selection is limited. If you have a lot of zones, you will need to reuse colors.

### Default Color
Tags that are not located within any zone will be assigned this color. For this extension, this argument is required.

### LED Timeout
This value, in seconds, determines how long the LED pattern lasts on a tag. As set in the API, valid values range from 5 to 1800 seconds.

> Powering the LED is a significant source of battery drain on tags and can have a noticeable effect on 300 series tags such as the PT301. Keep this in mind when setting the LED timeout.

Providing this argument is optional.  By default, the timeout is 30 seconds.

### LED Flashing
The tag LEDs can either display a solid color or flash on and off. If this value is set to `True`, the LEDs will flash on and off; if set to `False`, the color will be solid instead of flashing.

Providing this argument is optional.  By default, the LEDs will be solid.

### Print Output
Setting this argument to `False` stops the process from printing anything to the terminal.

Providing an argument is optional.  By default, printing is enabled.

## Output
When this program runs, it first creates a mapping of zone ID's to zone names for all zones in the configuration file. To do this, it begins by listening for Geofencer Zone Info data items, which contain the zone ID's. Depending on the `Output Interval` setting in the geofencer configuration, this may take a few seconds.

After the mapping is completed, the program prints "All zone info received."  It then begins processing Tag Zone Info data items to determine the appropriate color assignment for each tag.

If a tag is in multiple overlapping zones at the same time, then color is assigned to that tag by the order in which zones appear in the input configuration file. For example, with the following configuration file:
```
Zones:
  Zone A:
    Color: [255, 0, 0] # red
  Zone B:
    Color: [0, 0, 255] # blue
```
If a tag is in both Zone A and Zone B at the same time, then it will be assigned the color red since Zone A appears before Zone B in the configuration file.
