# ha-extron

[![Ruff](https://github.com/NitorCreations/ha-extron/actions/workflows/ruff.yaml/badge.svg)](https://github.com/NitorCreations/ha-extron/actions/workflows/ruff.yaml)
[![Tests](https://github.com/NitorCreations/ha-extron/actions/workflows/unittest.yaml/badge.svg)](https://github.com/NitorCreations/ha-extron/actions/workflows/unittest.yaml)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=NitorCreations&repository=https%3A%2F%2Fgithub.com%2FNitorCreations%2Fha-extron)

Home Assistant integration for Extron switchers and audio processors.

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

## Development

For local development, 
use [uv](https://github.com/astral-sh/uv) to handle the Python dependencies and virtual env.
Install uv with their standalone installer script or with package managers like homebrew.

Use `uv sync` to automatically create a virtual env and install the dependencies.

Update all dependencies with `uv lock --upgrade`.

### Tests

```bash
# Using uv managed virtual env
uv run python -m unittest discover -s tests/ -v
# Manually activated virtual env with necessary dependencies
python3 -m unittest discover -s tests/ -v
```

### Making a new release

1. Update the version number in `manifest.json` and `pyproject.toml`
2. Tag the release
3. Make a GitHub release

The new release should be picked up by HACS momentarily.

## License

GNU GENERAL PUBLIC LICENSE version 3
