# CUWB Viewer Passthrough
![](./img/cuwb_viewer_loop.gif)

The cuwb-viewer passthrough geofencer extension allows you to view the zones you've created in your config file in the CUWB Viewer.  You can assign a color to all zones in your config file, and they will show up in the CUWB Viewer with those colors.  Tags entering a zone will also be assigned the same color as the zone.

>Rendering of geofencer zones is only supported in CUWB Viewer version **2.1.4** or newer, so make sure you're CUWB Viewer installation is updated before running this extension.

## Usage
All geofencer dependencies need to be installed before running this extension.  Follow the instructions in the geofencer README for setting up a python virtual environment and installing packages.

Also before running this extension, the CUWB Viewer needs to be running and listening on the same UDP settings as the output stream you configure for this extension.  If not, then the CUWB Viewer will not hear about the zones from this extension and therefore will not render them.

The cuwb-viewer passthrough is run with the following command:
```
python cuwb_viewer_passthrough.py <config file>
```

## Config File
Like the geofencer itself, the cuwb-viewer passthrough extension takes its arguments in the form of a YAML config file.  This extension also performs config file verification against the schema file at startup.  An example config file is provided to serve as a starting point.

### Ethernet
#### Input
The cuwb-viewer passthrough listens for Geofencer Zone Info and Tag Zone Info CDP data items, which are output by the geofencer main program.  Therefore, the input stream definition should match the output settings of your geofencer config file.

#### Output
The cuwb-viewer passthrough will output its own CDP data items on this stream.  As was said above, the CUWB Viewer application itself should be listening on whatever stream you set as the output, that way it can receive the zone information and tag color data items.

Providing this setting is optional.  If omitted, then the input stream will also be used for output.

### Zones
This list of zones is formatted similarly to the geofencer config file.  However, instead of providing vertices, z range, and hysteresis, you only provide a `Color` argument.  For this extension, the `Color` argument is an RGB code.  The specific format is a list of 3 integers ranging from 0 to 255.

In the CUWB Viewer, each zone will be colored according to its `Color` argument, and the tag rendering in the viewer will be assigned this color when it enters the zone.  Zones will appear slightly transulcent in the CUWB Viewer to increase visibility of tags that are inside of it.

> Though it's not a part of the config file, it's quite easy to change the translucency of the zones in the CUWB Viewer if you wish to do so.  Simply look for the `ZONE_COLOR_ALPHA_VALUE` constant definition in `cuwb_viewer_passthrough.py` and update that value.  The default is 128, you can set it to any number from 0 to 255 (0 = fully transparent, 255 = opaque).  Bear in mind that this value applies to all zones globally.

### Default Color
For tags that are not in any zone, they will be assigned this color in the CUWB Viewer.

Providing this argument is optional.  If omitted, tags will have their custom color removed in the CUWB Viewer and will go back to their defualt CUWB Viewer color (typically blue).

### Print Output
Setting this argument to `False` stops the process from printing anything to the terminal.

Providing argument is optional.  By default, printing is enabled.

## Output
When this program runs, it first needs to create a mapping of zone ID's to names for all the zones in its config file.  So it begins by listening for Geofencer Zone Info data items which contain the zone ID's.  It may take some amount of time doing this, depending on what the `Output Interval` setting is in your geofencer config file.

While the program is listening for zone info, if it hears a Geofencer Zone Info data item for any zone that is not in its config file, then it will still send data to the CUWB Viewer to render that zone.  It'll be given a gray color.

After the mapping is completed, it will print "All zone info received."  At that point, the program sends all zone info to the CUWB Viewer for it to render the zones.  Also, the program will start listening for Tag Zone Info data items and using those to determine which color the tag should be assigned.

If a tag is in multiple zones at the same time (due to overlapping zones), then color is assigned to that tag by the order in which zones appear in the input config file.  For example, with the following config file:
```
Zones:
  Zone A:
    Color: [255, 0, 0] # red
  Zone B:
    Color: [0, 0, 255] # blue
```
If a tag is in both Zone A and Zone B at the same time, then it will be assigned the color red since Zone A appears before Zone B in the config file.

## Note on Program Halt
If you stop this program with the typical Ctrl+C, commands will be sent to the CUWB Viewer to remove all zones and remove all custom colors from the devices.  So it's a convenient way to reset the CUWB Viewer scene back to what it appeared as before you started the cuwb-viewer passthrough extension.

## Note on Existing CUWB Viewer Objects
If you have an imported object in your running CUWB Viewer environment, let's say its name is "Box".  If you run the CUWB Viewer Passthrough script with a zone that is also named "Box", then the existing "Box" object in the CUWB Viewer will be deleted and replaced with the "Box" zone.
