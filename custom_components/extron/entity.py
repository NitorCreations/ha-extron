import logging

from abc import abstractmethod

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from pyextron import SurroundSoundProcessor

from custom_components.extron import DeviceInformation

logger = logging.getLogger(__name__)


class ExtronSurroundSoundProcessorSensorEntity(SensorEntity):
    def __init__(
        self, ssp: SurroundSoundProcessor, device_information: DeviceInformation, name: str, unique_id: str
    ) -> None:
        self._ssp = ssp
        self._device_information = device_information
        self._name = name
        self._unique_id = unique_id

    @property
    def unique_id(self) -> str | None:
        return f"extron_{self._device_information.mac_address}_{self._unique_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_information.device_info

    @property
    def name(self):
        return f"Extron {self._device_information.model_name} {self._name}"

    @abstractmethod
    async def query_sensor_native_value(self):
        return None

    async def async_update(self):
        try:
            async with self._ssp._device.connection():
                self._attr_native_value = await self.query_sensor_native_value()
        except Exception:
            logger.exception(f"async_update from {self.name} encountered error:")
            self._attr_available = False
        else:
            self._attr_available = True


class ExtronSurroundSoundProcessorBinarySensorEntity(BinarySensorEntity):
    def __init__(
        self, ssp: SurroundSoundProcessor, device_information: DeviceInformation, name: str, unique_id: str
    ) -> None:
        self._ssp = ssp
        self._device_information = device_information
        self._name = name
        self._unique_id = unique_id

    @property
    def unique_id(self) -> str | None:
        return f"extron_{self._device_information.mac_address}_{self._unique_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_information.device_info

    @property
    def name(self):
        return f"Extron {self._device_information.model_name} {self._name}"

    @abstractmethod
    async def query_is_on(self):
        return None

    async def async_update(self):
        try:
            async with self._ssp._device.connection():
                self._attr_is_on = await self.query_is_on()
        except Exception:
            logger.exception(f"async_update from {self.name} encountered error:")
            self._attr_available = False
        else:
            self._attr_available = True
