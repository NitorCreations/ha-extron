"""The Extron integration."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo, format_mac

from custom_components.extron.extron import AuthenticationError, ExtronDevice

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SENSOR, Platform.BUTTON]


@dataclass
class DeviceInformation:
    mac_address: str
    model_name: str
    device_info: DeviceInfo


@dataclass
class ExtronConfigEntryRuntimeData:
    device: ExtronDevice
    device_information: DeviceInformation


async def get_device_information(device: ExtronDevice) -> DeviceInformation:
    mac_address = await device.query_mac_address()
    model_name = await device.query_model_name()
    firmware_version = await device.query_firmware_version()
    part_number = await device.query_part_number()

    device_info = DeviceInfo(
        identifiers={(DOMAIN, format_mac(mac_address))},
        name=f"Extron {model_name}",
        manufacturer="Extron",
        model=model_name,
        sw_version=firmware_version,
        serial_number=part_number,
    )

    return DeviceInformation(mac_address=format_mac(mac_address), model_name=model_name, device_info=device_info)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Extron from a config entry."""
    # Verify we can connect to the device
    try:
        device = ExtronDevice(entry.data["host"], entry.data["port"], entry.data["password"])
        await device.connect()
    except AuthenticationError as e:
        raise ConfigEntryNotReady('Invalid credentials') from e
    except Exception as e:
        raise ConfigEntryNotReady("Unable to connect") from e

    # Store the device and information about as runtime data in the entry
    device_information = await get_device_information(device)
    entry.runtime_data = ExtronConfigEntryRuntimeData(device, device_information)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
