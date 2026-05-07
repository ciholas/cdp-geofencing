# Geofencer
This CDP example application allows you to designate "zones" located within your running CUWBNet.  The application will then receive tag positions and output which zones each tag is located in, both printed to the terminal and over CDP.  Other applications can then receive the geofencer output CDP data and process it in useful ways.  Two examples of such processing are provided in the `extensions` folder.

Currently, this application will only work in Linux environments.

## Usage
Before running the geofencer or any extensions, you should create a python virtual environment.
```
python3 -m virtualenv venv
source venv/bin/activate
```

Once that virtual environment is running, install the dependencies.
```
python -m pip install -r requirements.txt
```

The geofencer is run using the following command:
```
python geofencer.py <config file>
```

## Config File
Geofencer arguments, such as stream information and zone definitions, should be placed into a configuration file using the YAML file format.  An example config file (example_config.yaml) provides the YAML structure and can be used as a starting point for creating your own configuration file.  In addition, the geofencer.py script validates the input config file against the schema (geofencer_config_schema.yaml) to make sure it is of the correct format.  If anything is wrongly formatted in the config, or if any arguments are missing, the script will terminate and output a specific error for each issue.

### Ethernet Settings
#### Input
Since the geofencer listens for position data items, the input stream settings in your config file should match the User Stream settings for the CUWBNet you want to run the geofencer with.

#### Output
You can specify a UDP stream on which the geofencer will output CDP data.  It can be different from the input stream settings.  Providing the output stream is optional.  If omitted, then the input stream settings will be used for output.

### Zones
Zones are defined in the config file with the following format:
```yaml
<Zone Name>:
  Vertices: [[x0, y0], [x1, y1], [x2, y2], ...]
  Z Range: [z_min, z_max]
  Hysteresis: h_value
```

The `<Zone Name>` can be any string, but zone names are limited to **50** characters in length.  This is done to limit CDP data item sizes.

**All numeric values (vertices, z range, hysteresis) in the zone definition are in meters!**

#### Vertices
The "shape" or "boundary" of a geofencer zone is defined as a polygon in the XY plane.  To define a zone's boundary, provide an ordered list of XY vertices.  There must be **at least 3 vertices** provided to create a valid zone.

Important considerations:
* Order matters when defining the vertices list.  The zone boundary is defined by connecting a straight line from one vertex in the list to the next one in the list.  This is done for every vertex in the list to define all the edges of the boundary.  Also, the boundary is automatically closed by connecting the last vertex to the first vertex.
* A zone's boundary must be a simple polygon, as in it cannot intersect itself.  For example, `[[0, 0], [1, 0], [0, 1], [1, 1]]` is not valid, but switching the order to `[[0, 0], [1, 0], [1, 1], [0, 1]]` makes it valid.

#### Z Range
This is what gives the zones height.  A tag's Z coordinate must be within the Z Range to be considered inside the zone.

#### Hysteresis
Hysteresis should be considered a distance value.  The way it works is that a tag is outside a zone until it enters the boundary defined in the config file.  However, once a tag is in the zone, for it to leave the zone, it must exceed the zone's boundary by the hysteresis value.  This essentially "expands" the zone while the tag is inside of it.

The problem this solves is for when a tag is right on a zone's boundary.  Without hysteresis, due to jitter in position data, the tag would be reported as in/out/in/out, etc.  With hysteresis, the zone boundary has now expanded and the tag will be inside the zone consistently even if there is jitter.

Providing hysteresis is optional.  A default value of **0.15m** is used for all zones where hysteresis is not provided.  This should be more than enough to cover the position jitter in the CUWB System in most scenarios.  Consider providing a larger value in your config for zones that are placed in an environment that will have more jitter.

### Output Interval
Part of the geofencer output is that tag zone information and zone metadata is output as CDP data at a regular interval.  This argument sets that interval in seconds.

Providing this argument is optional.  The default output interval is 10 seconds.

### Print Output
Setting this argument to `False` stops the process from printing anything to the terminal.  However, any errors at startup will still be printed.

Providing argument is optional.  By default, printing is enabled.

## Output
At startup, the geofencer validates all the zones in the config file and assigns them integer ID's.  ID's start at **1** and are assigned from top to bottom in the config file zone list, incrementing by 1 each time.  When all zones are validated and have assigned ID's, a mapping of zone names to ID's is printed to stdout:
```
    1: Zone A
    2: Zone B
```

In addition, a Geofencer Zone Info CDP data item is created for each zone and sent on the output stream.

After that's done, the geofencer main thread begins listening on the input stream for Position V3 data items.  For each position item, the program checks its data against each zone in the config file to see if the tag is inside any zones.  The moment a tag's zone information changes, or when a new tag shows up, that update is printed to the terminal and output as a Tag Zone Info CDP data item.

For the terminal print, the tag's serial number is printed along with a list of zones that the tag is currently in.
```
2026-01-27 13:32:59.617524 - 01:12:1A0F: []
2026-01-27 13:34:45.617524 - 01:12:105B: [1, 2]
2026-01-27 13:34:50.617524 - 01:12:1A0F: [1]
2026-01-27 13:35:11.617524 - 01:12:105B: [2]
```

An empty list next to the serial number means that tag is in no zones.  A list with multiple ID's means the tag is in multiple zones at the same time (due to overlapping zones).

### CDP Output
At an interval defined by `Output Interval` argument, the following information is regularly output over CDP on the output stream:
1. Geofencer Zone Info data items for all zones.
2. Tag Zone Info data items for all tags that have been heard from.

This data can be received by other applications that can process this data in useful ways.  This includes the two example geofencer extensions provided in this repo.

Definitions for the above data items are given below.  Both packets have [cdp-py](https://github.com/ciholas/cdp-py) definitions, and examples of decoding them are provided in the extensions.

#### Geofencer Zone Info
| Field | Description | Example |
| ----- | ----------- | ------- |
| Zone ID | Integer ID of this zone. | 1 |
| Zone Name | Name of this zone. | "Restricted Zone" |
| Z Min | Minimum Z value in mm. | -1500 |
| Z Max | Maximum Z value in mm. | 10000 |
| Hysteresis | Hysteresis value in mm. | 500 |
| Vertices | Ordered list of XY vertices, in mm, that define the zone's boundary. |  [[6220, 8500], [6300, 5810], [3425, 5567], [3600, 8580]] |

#### Tag Zone Info
| Field | Description | Example |
| ----- | ----------- | ------- |
| Serial Number | The serial number of this tag. | 01:12:105B |
| Zone List | List of Zone ID's.  At the time this packet is sent, the tag is in each of these zones. | [1, 5] |
