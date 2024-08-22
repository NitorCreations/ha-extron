import logging
from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.typing import StateType

from custom_components.extron import ExtronConfigEntryRuntimeData, ExtronDevice, DeviceInformation
from custom_components.extron.const import CONF_DEVICE_TYPE, DOMAIN
from custom_components.extron.extron import SurroundSoundProcessor, DeviceType

logger = logging.getLogger(__name__)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities):
    # Extract stored runtime data from the entry
    runtime_data: ExtronConfigEntryRuntimeData = entry.runtime_data
    device = runtime_data.device
    device_information = runtime_data.device_information
    logger.info(device_information)

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
    _attr_native_unit_of_measurement = '°C'
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str | None:
        mac_address = format_mac(self._device_information.mac_address)

        return f'extron_{mac_address}_temperature'

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, format_mac(self._device_information.mac_address))},
            name=self.name,
            manufacturer='Extron',
            model=self._device_information.model_name,
            sw_version=self._device_information.firmware_version,
            serial_number=self._device_information.part_number,
        )

    @property
    def name(self):
        return f'Extron {self._device_information.model_name} temperature'

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self._native_value

    async def async_update(self):
        self._native_value = await self._ssp.get_temperature()
