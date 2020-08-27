# CDP Python Geofencing Tool

This Python script uses CDP to create zones and track where tags are in respect to the zones.

## Getting Started

### Installing

Download all the files from the repository.

Please use a Python virtualenv. You can install it with apt on Ubuntu or pip on MacOS.

### Setup virtualenv
```
virtualenv venv --python=python3
```

### Activate the created virtualenv
```
source venv/bin/activate
```

### Install necessary packages
```
pip install -r requirements.txt
```

### Exit virtualenv
```
deactivate
```

## Usage
Please run from inside the virtualenv. See [Activating the created virtualenv](#activate-the-created-virtualenv) in setup section above.

```
python geofencing.py -h
```

### Configuration

The default config file is geofencing_config.yaml

You can either use or edit this one or make your own.

[Here](./example_config.yaml) is an example config with comments explaining how to properly format one.

## License

This work is licensed under the [Creative Commons Attribution 4.0 International](http://creativecommons.org/licenses/by/4.0/) License.
