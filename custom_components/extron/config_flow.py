"""Config flow for Extron integration."""

import logging

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import selector

from .const import CONF_DEVICE_TYPE, CONF_HOST, CONF_PASSWORD, CONF_PORT, DOMAIN, OPTION_INPUT_NAMES
from .extron import AuthenticationError, DeviceType, ExtronDevice

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=23): int,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEVICE_TYPE): selector(
            {
                "select": {
                    "options": [
                        {"label": "HDMI Switcher", "value": DeviceType.HDMI_SWITCHER.value},
                        {"label": "Surround Sound Processor", "value": DeviceType.SURROUND_SOUND_PROCESSOR.value},
                    ]
                }
            }
        ),
    }
)


class ExtronConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Extron."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                # Try to connect to the device
                extron_device = ExtronDevice(user_input["host"], user_input["port"], user_input["password"])
                await extron_device.connect()

                # Make a title for the entry
                model_name = await extron_device.query_model_name()
                title = f"Extron {model_name}"

                # Make a unique ID for the entry, prevent adding the same device twice
                unique_id = format_mac(await extron_device.query_mac_address())
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Disconnect, we'll connect again later, this was just for validation
                await extron_device.disconnect()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except (BrokenPipeError, ConnectionError, OSError):  # all technically OSError
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow"""
        return ExtronOptionsFlowHandler(config_entry)


class ExtronOptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage optional settings for the entry."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        OPTION_INPUT_NAMES, default=self.config_entry.options.get(OPTION_INPUT_NAMES)
                    ): selector({"text": {"multiple": True}}),
                }
            ),
        )
