import logging

from datetime import date, datetime, timedelta
from decimal import Decimal

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType
from pyextron import DeviceType, SurroundSoundProcessor

from custom_components.extron import DeviceInformation, ExtronConfigEntryRuntimeData
from custom_components.extron.const import CONF_DEVICE_TYPE

logger = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities):
    # Extract stored runtime data from the entry
    runtime_data: ExtronConfigEntryRuntimeData = entry.runtime_data
    device = runtime_data.device
    device_information = runtime_data.device_information

    # Add entities
    if entry.data[CONF_DEVICE_TYPE] == DeviceType.SURROUND_SOUND_PROCESSOR.value:
        ssp = SurroundSoundProcessor(device)
        async_add_entities([ExtronDeviceTemperature(ssp, device_information)])


class ExtronDeviceTemperature(SensorEntity):
    def __init__(self, ssp: SurroundSoundProcessor, device_information: DeviceInformation) -> None:
        self._ssp = ssp
        self._device_information = device_information

        self._native_value = None

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str | None:
        return f"extron_{self._device_information.mac_address}_temperature"

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_information.device_info

    @property
    def name(self):
        return f"Extron {self._device_information.model_name} temperature"

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self._native_value

    async def async_update(self):
        try:
            async with self._ssp._device.connection():
                self._native_value = await self._ssp.get_temperature()
        except Exception:
            logger.exception(f"async_update from {self.name} encountered error:")
            self._attr_available = False
        else:
            self._attr_available = True
