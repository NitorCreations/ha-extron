import logging

from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyextron import DeviceType, SurroundSoundProcessor

from custom_components.extron import DeviceInformation, ExtronConfigEntryRuntimeData
from custom_components.extron.const import CONF_DEVICE_TYPE
from custom_components.extron.entity import ExtronSurroundSoundProcessorSensorEntity

logger = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    # Extract stored runtime data from the entry
    runtime_data: ExtronConfigEntryRuntimeData = entry.runtime_data
    device = runtime_data.device
    device_information = runtime_data.device_information

    # Add entities
    if entry.data[CONF_DEVICE_TYPE] == DeviceType.SURROUND_SOUND_PROCESSOR.value:
        ssp = SurroundSoundProcessor(device)
        async_add_entities(
            [
                ExtronDeviceTemperature(ssp, device_information),
                ExtronInputResolution(ssp, device_information),
                ExtronHdmiLoopThrough(ssp, device_information),
            ],
            update_before_add=True,
        )

def parse_incoming_line_count(incoming_line_count: str) -> str:
    parts = incoming_line_count.split("*")

    return f"{parts[3]} x {parts[0]} @ {int(float(parts[1]))} Hz"

class ExtronDeviceTemperature(ExtronSurroundSoundProcessorSensorEntity):
    def __init__(self, ssp: SurroundSoundProcessor, device_information: DeviceInformation) -> None:
        super().__init__(ssp, device_information, "temperature", "temperature")

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_state_class = SensorStateClass.MEASUREMENT

    async def query_sensor_native_value(self):
        return await self._ssp.get_temperature()


class ExtronInputResolution(ExtronSurroundSoundProcessorSensorEntity):
    def __init__(self, ssp: SurroundSoundProcessor, device_information: DeviceInformation) -> None:
        super().__init__(ssp, device_information, "input resolution", "input_resolution")

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def query_sensor_native_value(self):
        return parse_incoming_line_count(await self._ssp._device.run_command("34I"))


class ExtronHdmiLoopThrough(ExtronSurroundSoundProcessorSensorEntity):
    def __init__(self, ssp: SurroundSoundProcessor, device_information: DeviceInformation) -> None:
        super().__init__(ssp, device_information, "HDMI loop thru", "hdmi_loop_thru")

        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["No audio", "Follow input", "Downmix"]
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def query_sensor_native_value(self):
        value = await self._ssp._device.run_command("\x1b" + "LOUT")

        return self._attr_options[int(value)]
