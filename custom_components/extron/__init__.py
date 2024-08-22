"""The Extron integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.extron.extron import ExtronDevice, DeviceType, AuthenticationFailed

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Extron from a config entry."""
    # Verify we can connect
    try:
        device = ExtronDevice(DeviceType.UNKNOWN, entry.data['host'], entry.data['port'], entry.data['password'])
        await device.connect()
        await device.disconnect()
    except AuthenticationFailed as e:
        raise ConfigEntryNotReady('Invalid credentials') from e
    except Exception as e:
        raise ConfigEntryNotReady('Unable to connect') from e

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
