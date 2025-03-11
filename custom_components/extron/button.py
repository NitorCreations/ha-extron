import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from pyextron import ExtronDevice

from custom_components.extron import DeviceInformation, ExtronConfigEntryRuntimeData

logger = logging.getLogger(__name__)

async def async_setup_entry(_hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    # Extract stored runtime data from the entry
    runtime_data: ExtronConfigEntryRuntimeData = entry.runtime_data
    device = runtime_data.device
    device_information = runtime_data.device_information

    # Add entities
    async_add_entities([ExtronRebootButton(device, device_information)])


class ExtronRebootButton(ButtonEntity):
    def __init__(self, device: ExtronDevice, device_information: DeviceInformation) -> None:
        self._device = device
        self._device_information = device_information

    _attr_device_class = ButtonDeviceClass.RESTART

    @property
    def unique_id(self) -> str | None:
        return f"extron_{self._device_information.mac_address}_reboot_button"

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_information.device_info

    @property
    def name(self):
        return f"Extron {self._device_information.model_name} reboot button"

    async def async_press(self) -> None:
        await self._device.reboot()

        # Disconnect immediately so we start attempting to reconnect immediately
        await self._device.disconnect()
