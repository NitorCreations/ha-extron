"""The Extron integration."""

import logging

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo, format_mac

from custom_components.extron.const import OPTION_INPUT_NAMES
from custom_components.extron.extron import AuthenticationError, ExtronDevice

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SENSOR, Platform.BUTTON]
_LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceInformation:
    mac_address: str
    model_name: str
    device_info: DeviceInfo


@dataclass
class ExtronConfigEntryRuntimeData:
    device: ExtronDevice
    device_information: DeviceInformation
    input_names: list[str]


async def get_device_information(device: ExtronDevice) -> DeviceInformation:
    mac_address = await device.query_mac_address()
    model_name = await device.query_model_name()
    firmware_version = await device.query_firmware_version()
    part_number = await device.query_part_number()
    ip_address = await device.query_ip_address()

    device_info = DeviceInfo(
        identifiers={(DOMAIN, format_mac(mac_address))},
        name=f"Extron {model_name}",
        manufacturer="Extron",
        model=model_name,
        sw_version=firmware_version,
        serial_number=part_number,
        configuration_url=f"http://{ip_address}/",
    )

    return DeviceInformation(mac_address=format_mac(mac_address), model_name=model_name, device_info=device_info)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Extron from a config entry."""
    # Verify we can connect to the device
    try:
        device = ExtronDevice(entry.data["host"], entry.data["port"], entry.data["password"])
        await device.connect()
    except AuthenticationError as e:
        raise ConfigEntryNotReady("Invalid credentials") from e
    except Exception as e:
        raise ConfigEntryNotReady("Unable to connect") from e

    # Store runtime information
    device_information = await get_device_information(device)
    input_names = entry.options.get(OPTION_INPUT_NAMES, [])
    entry.runtime_data = ExtronConfigEntryRuntimeData(device, device_information, input_names)

    # Register a listener for option updates
    entry.async_on_unload(entry.add_update_listener(entry_update_listener))

    _LOGGER.info(f"Initializing entry with runtime data: {entry.runtime_data}")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def entry_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    # Reload the entry when options have been changed
    await hass.config_entries.async_reload(config_entry.entry_id)
