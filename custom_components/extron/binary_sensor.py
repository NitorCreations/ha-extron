from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyextron import DeviceType, SurroundSoundProcessor

from custom_components.extron import DeviceInformation, ExtronConfigEntryRuntimeData
from custom_components.extron.const import CONF_DEVICE_TYPE
from custom_components.extron.entity import ExtronSurroundSoundProcessorBinarySensorEntity


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
                InputSourceDetected(ssp, device_information),
                InputHdcpStatus(ssp, device_information),
                OutputSinkDetected(ssp, device_information),
                OutputHdcpStatus(ssp, device_information),
            ],
            update_before_add=True,
        )


class InputSourceDetected(ExtronSurroundSoundProcessorBinarySensorEntity):
    def __init__(self, ssp: SurroundSoundProcessor, device_information: DeviceInformation) -> None:
        super().__init__(ssp, device_information, "input source detected", "input_source_detected")

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def query_is_on(self):
        input_hdcp_status = await self._ssp._device.run_command("\x1b" + "IHDCP")

        return int(input_hdcp_status) > 0


class InputHdcpStatus(ExtronSurroundSoundProcessorBinarySensorEntity):
    def __init__(self, ssp: SurroundSoundProcessor, device_information: DeviceInformation) -> None:
        super().__init__(ssp, device_information, "input HDCP status", "input_hdcp_status")

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def query_is_on(self):
        input_hdcp_status = await self._ssp._device.run_command("\x1b" + "IHDCP")

        return int(input_hdcp_status) == 1


class OutputSinkDetected(ExtronSurroundSoundProcessorBinarySensorEntity):
    def __init__(self, ssp: SurroundSoundProcessor, device_information: DeviceInformation) -> None:
        super().__init__(ssp, device_information, "output sink detected", "output_sink_detected")

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def query_is_on(self):
        output_hdcp_status = await self._ssp._device.run_command("\x1b" + "OHDCP")

        return int(output_hdcp_status) > 0


class OutputHdcpStatus(ExtronSurroundSoundProcessorBinarySensorEntity):
    def __init__(self, ssp: SurroundSoundProcessor, device_information: DeviceInformation) -> None:
        super().__init__(ssp, device_information, "output HDCP status", "output_hdcp_status")

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def query_is_on(self):
        input_hdcp_status = await self._ssp._device.run_command("\x1b" + "OHDCP")

        return int(input_hdcp_status) == 1
