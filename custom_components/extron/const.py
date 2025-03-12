"""Constants for the Extron integration."""

from datetime import timedelta

DOMAIN = "extron"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_PASSWORD = "password"
CONF_DEVICE_TYPE = "device_type"

OPTION_INPUT_NAMES = "input_names"

# Poll entities every 30 seconds
SCAN_INTERVAL = timedelta(minutes=30)
