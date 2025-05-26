# ha-extron

[![Ruff](https://github.com/NitorCreations/ha-extron/actions/workflows/ruff.yaml/badge.svg)](https://github.com/NitorCreations/ha-extron/actions/workflows/ruff.yaml)
[![Tests](https://github.com/NitorCreations/ha-extron/actions/workflows/unittest.yaml/badge.svg)](https://github.com/NitorCreations/ha-extron/actions/workflows/unittest.yaml)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=NitorCreations&repository=https%3A%2F%2Fgithub.com%2FNitorCreations%2Fha-extron)

Home Assistant integration for Extron switchers and audio processors. It uses our 
[pyextron](https://github.com/NitorCreations/pyextron) library under the hood.

## Supported devices

* SSP 200 surround sound processors
* SW HD 4K PLUS Series switchers

## Requirements

Devices must have Telnet access enabled.

## Features

Not every single feature can be controlled, only the basics:

* Media player support
  * Source selection
  * Volume control (SSP 200 only)
* Reboot button
* Temperature sensor (SSP 200 only)

The communication is done using Python's `asyncio` and requires no external libraries.

## Caveats

* SSP 200 surround sound processors seem to stop responding properly (both to commands and to physical interactions 
  like button presses) after some time, requiring a reboot 

## Development

Developing the integration and testing it locally in Home Assistant are two separate tasks.

For development, create a virtual environment (either manually or in an IDE like PyCharm), then install the 
dependencies using `pip install -e .`.

Running the integration involves setting up a Home Assistant development environment and making the integration 
available to it:

1. Clone this repository
2. Set up a Home Assistant [development environment](https://developers.home-assistant.io/docs/development_environment/)
3. Open `devcontainer.json` and add something like this to `mounts`:

```
"source=${localEnv:HOME}/Projects/ha-extron/custom_components/extron,target=${containerWorkspaceFolder}/config/custom_components/extron,type=bind",
```

Repeat this for any other integrations you want to make available in your local Home Assistant environment.

4. Start the development environment and browse to `http://localhost:8123`. If you go to Settings -> Integrations, you should be able to see your 
   custom integrations listed

### Tests

```bash
python3 -m unittest discover -s tests/ -v
```

### Making a new release

1. Update the version number in `manifest.json` and `pyproject.toml`
2. Tag the release
3. Make a GitHub release

The new release should be picked up by HACS momentarily.

## License

GNU GENERAL PUBLIC LICENSE version 3
