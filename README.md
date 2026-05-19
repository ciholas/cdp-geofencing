# Geofencer
This CDP example application allows users to designate "zones" within an active CUWBNet. The application receives tag position data and determines which zones each tag is located in, both printed to the terminal and over CDP.  Other applications can then receive and process the geofencer CDP output data. Two examples of such processing are provided in the `extensions` folder.

Currently, this application will only work in Linux environments.

## Usage
Before running the geofencer or any extensions, a python virtual environment should be created.
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

## Configuration File
Geofencer arguments, such as stream information and zone definitions, should be placed into a configuration file using the YAML file format. An example configuration file (example_config.yaml) provides the YAML structure and can be used as a starting point for creating your own configuration file. In addition, the geofencer.py script validates the input configuration file against the schema (geofencer_config_schema.yaml) to make sure it is of the correct format.  If the configuration contains formatting errors or any required arguments are missing, the script will terminate and display a specific error message identifying each issue.

### Ethernet Settings
#### Input
Since the geofencer listens for position data items, the input stream settings in the configuration file should match the User Stream settings for the CUWBNet that will be used with the geofencer.

#### Output
You can specify a UDP stream for the geofencer to output CDP data. This stream can be different from the input stream settings. Providing the output stream is optional. If omitted, then the input stream settings will be used for output.

### Zones
Zones are defined in the config file with the following format:
```yaml
<Zone Name>:
  Vertices: [[x0, y0], [x1, y1], [x2, y2], ...]
  Z Range: [z_min, z_max]
  Hysteresis: h_value
```

The `<Zone Name>` can be any string, but zone names are limited to **50** characters in length. This is done to limit CDP data item sizes.

**All numeric values (vertices, z range, hysteresis) in the zone definition are in meters!**

#### Vertices
The "shape" or "boundary" of a geofencer zone is defined as a polygon in the XY plane. To define a zone's boundary, provide an ordered list of XY vertices. There must be **at least 3 vertices** provided to create a valid zone.

Important considerations:
* The order of the vertices in the list is important. The zone boundary is created by connecting each vertex to the next vertex in the list with a straight line segment. This process continues for all vertices to define the complete boundary. The boundary is automatically closed by connecting the final vertex back to the first vertex in the list.

* A zone's boundary must be a simple polygon, as in it cannot intersect itself. For example, `[[0, 0], [1, 0], [0, 1], [1, 1]]` is not valid, but switching the order to `[[0, 0], [1, 0], [1, 1], [0, 1]]` makes it valid.

#### Z Range
This is what gives the zones height. A tag's Z coordinate must be within the Z Range to be considered inside the zone.

#### Hysteresis
Hysteresis should be considered a distance value. A tag is considered outside a zone until it enters the boundary defined in the configuration file. However, once a tag is in the zone,  it must exceed the zone's boundary by the hysteresis value for it to leave the zone. This essentially "expands" the zone while the tag is inside of it.

This behavior helps prevent rapid in/out state changes when a tag is positioned near the edge of a zone. Without hysteresis, small amounts of position jitter could cause the tag to repeatedly alternate between inside and outside states. By applying hysteresis, the expanded boundary allows the tag to remain consistently inside the zone despite minor fluctuations in position data.

Providing a hysteresis value is optional. A default value of **0.15m** is used for all zones where hysteresis is not provided. In most scenarios, this value should be more than enough to compensate for normal CUWB System position jitter. Larger hysteresis values may be appropriate in environments where greater positional variation is expected.

### Output Interval
As part of the geofencer output, tag zone information and zone metadata are transmitted as CDP data at a regular interval. This argument sets that interval in seconds.

Providing this argument is optional. If no value is specified, the default output interval is 10 seconds.

### Print Output
Setting this argument to `False`disables terminal output during operation.  However, any errors at startup will still be printed.

Providing an argument is optional. By default, terminal output  is enabled.

## Output
At startup, the geofencer validates all the zones in the configuration file and assigns them integer ID's.  ID's start at **1** and are assigned from top to bottom in the configuration file zone list, incrementing by 1 each time. When all zones are validated and have assigned ID's, a mapping of zone names to ID's is printed to stdout:
```
    1: Zone A
    2: Zone B
```

IIn addition, a Geofencer Zone Info CDP data item is created for each zone and transmitted on the configured output stream.

After initialization is complete, the geofencer main thread begins listening on the input stream for Position V3 data items. For each position item, the program checks its data against each zone in the configuration file to see if the tag is inside any zones. The moment a tag's zone information changes, or when a new tag shows up, that update is printed to the terminal and transmitted as a Tag Zone Info CDP data item.

In the terminal output, the tag's serial number is printed along with a list of zones that the tag is currently occupying.
```
2026-01-27 13:32:59.617524 - 01:12:1A0F: []
2026-01-27 13:34:45.617524 - 01:12:105B: [1, 2]
2026-01-27 13:34:50.617524 - 01:12:1A0F: [1]
2026-01-27 13:35:11.617524 - 01:12:105B: [2]
```

An empty list displayed next to a tag’s serial number indicates that the tag is not currently inside any zones. A list with multiple zone ID's indicates the tag is in multiple zones at the same time due to overlapping zones.

### CDP Output
At an interval defined by the `Output Interval` argument, the following information is periodically transmitted over CDP on the output stream:
1. Geofencer Zone Info data items for all configured zones.
2. Tag Zone Info data items for all tags currently being tracked.

This data can be received and processed by other applications in useful ways. This includes the two example geofencer extensions provided in this repository.

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
