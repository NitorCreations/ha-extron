"""The Extron integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.extron.extron import ExtronDevice, DeviceType, AuthenticationFailed, DeviceInformation

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


@dataclass
class ExtronConfigEntryRuntimeData:
    device: ExtronDevice
    device_information: DeviceInformation


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Extron from a config entry."""
    # Verify we can connect to the device
    try:
        device = ExtronDevice(entry.data['host'], entry.data['port'], entry.data['password'])
        await device.connect()
    except AuthenticationFailed as e:
        raise ConfigEntryNotReady('Invalid credentials') from e
    except Exception as e:
        raise ConfigEntryNotReady('Unable to connect') from e

    # Store the device and information about as runtime data in the entry
    device_information = await device.query_device_information()
    entry.runtime_data = ExtronConfigEntryRuntimeData(device, device_information)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
