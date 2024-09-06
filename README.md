# ha-extron

[![Ruff](https://github.com/NitorCreations/ha-extron/actions/workflows/ruff.yaml/badge.svg)](https://github.com/NitorCreations/ha-extron/actions/workflows/ruff.yaml)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=NitorCreations&repository=https%3A%2F%2Fgithub.com%2FNitorCreations%2Fha-extron)

Home Assistant integration for Extron switchers and audio processors.

## Supported devices

* SSP 200 surround sound processors
* SW HD 4K PLUS Series switchers

## Requirements

Devices must have Telnet access enabled

## Features

Obviously not every single feature can be controlled, only the basics:

* Media player support
  * Source selection
  * Volume control (SSP 200 only)
* Reboot button
* Temperature sensor (SSP 200 only)

The communication is done using Python's `asyncio` and requires no external libraries

## License

GNU GENERAL PUBLIC LICENSE version 3