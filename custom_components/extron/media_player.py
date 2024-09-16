import logging

from bidict import bidict
from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from custom_components.extron import DeviceInformation, ExtronConfigEntryRuntimeData
from custom_components.extron.const import CONF_DEVICE_TYPE
from custom_components.extron.extron import DeviceType, ExtronDevice, HDMISwitcher, SurroundSoundProcessor

logger = logging.getLogger(__name__)


def make_source_bidict(num_sources: int, input_names: list[str]) -> bidict:
    # Use user-defined input name for the source when available
    return bidict({i + 1: input_names[i] if i < len(input_names) else str(i + 1) for i in range(num_sources)})


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities):
    # Extract stored runtime data from the entry
    runtime_data: ExtronConfigEntryRuntimeData = entry.runtime_data
    device = runtime_data.device
    device_information = runtime_data.device_information
    input_names = runtime_data.input_names

    # Add entities
    if entry.data[CONF_DEVICE_TYPE] == DeviceType.SURROUND_SOUND_PROCESSOR.value:
        ssp = SurroundSoundProcessor(device)
        async_add_entities([ExtronSurroundSoundProcessor(ssp, device_information, input_names)])
    elif entry.data[CONF_DEVICE_TYPE] == DeviceType.HDMI_SWITCHER.value:
        hdmi_switcher = HDMISwitcher(device)
        async_add_entities([ExtronHDMISwitcher(hdmi_switcher, device_information, input_names)])


class AbstractExtronMediaPlayerEntity(MediaPlayerEntity):
    def __init__(self, device: ExtronDevice, device_information: DeviceInformation, input_names: list[str]) -> None:
        self._device = device
        self._device_information = device_information
        self._input_names = input_names
        self._device_class = "receiver"
        self._state = MediaPlayerState.PLAYING

    def get_device_type(self):
        return DeviceType.UNKNOWN

    @property
    def device_class(self):
        return self._device_class

    @property
    def unique_id(self) -> str | None:
        device_type = self.get_device_type()
        mac_address = self._device_information.mac_address

        return f"extron_{device_type.value}_{mac_address}_media_player"

    @property
    def state(self):
        return self._state

    @property
    def available(self) -> bool:
        return self._device.is_connected()

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_information.device_info

    @property
    def name(self):
        return f"Extron {self._device_information.model_name} media player"


class ExtronSurroundSoundProcessor(AbstractExtronMediaPlayerEntity):
    def __init__(self, ssp: SurroundSoundProcessor, device_information: DeviceInformation, input_names: list[str]):
        super().__init__(ssp.get_device(), device_information, input_names)
        self._ssp = ssp

        self._source = None
        self._source_bidict = self.create_source_bidict()
        self._volume = None
        self._muted = False

    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
    )

    def get_device_type(self):
        return DeviceType.SURROUND_SOUND_PROCESSOR

    async def async_update(self):
        self._source = self._source_bidict.get(await self._ssp.view_input())
        self._muted = await self._ssp.is_muted()
        volume = await self._ssp.get_volume_level()
        self._volume = volume / 100

    @property
    def volume_level(self):
        return self._volume

    @property
    def volume_step(self):
        return 0.01

    @property
    def is_volume_muted(self):
        return self._muted

    @property
    def source(self):
        return self._source

    @property
    def source_list(self):
        return list(self._source_bidict.values())

    def create_source_bidict(self) -> bidict:
        return make_source_bidict(5, self._input_names)

    async def async_select_source(self, source):
        await self._ssp.select_input(self._source_bidict.inverse.get(source))
        self._source = source

    async def async_mute_volume(self, mute: bool) -> None:
        await self._ssp.mute() if mute else await self._ssp.unmute()

    async def async_set_volume_level(self, volume: float) -> None:
        await self._ssp.set_volume_level(int(volume * 100))

    async def async_volume_up(self) -> None:
        await self._ssp.increment_volume()

    async def async_volume_down(self) -> None:
        await self._ssp.decrement_volume()


class ExtronHDMISwitcher(AbstractExtronMediaPlayerEntity):
    def __init__(
        self, hdmi_switcher: HDMISwitcher, device_information: DeviceInformation, input_names: list[str]
    ) -> None:
        super().__init__(hdmi_switcher.get_device(), device_information, input_names)
        self._hdmi_switcher = hdmi_switcher

        self._state = MediaPlayerState.PLAYING
        self._source = None
        self._source_bidict = self.create_source_bidict()

    _attr_supported_features = MediaPlayerEntityFeature.SELECT_SOURCE

    def get_device_type(self):
        return DeviceType.HDMI_SWITCHER

    async def async_update(self):
        self._source = self._source_bidict.get(await self._hdmi_switcher.view_input())

    @property
    def source(self):
        return self._source

    @property
    def source_list(self):
        return list(self._source_bidict.values())

    def create_source_bidict(self) -> bidict:
        model_name = self._device_information.model_name
        sw = model_name.split(" ")[0]

        if sw == "SW2":
            num_sources = 2
        elif sw == "SW4":
            num_sources = 4
        elif sw == "SW6":
            num_sources = 6
        else:
            num_sources = 8

        return make_source_bidict(num_sources, self._input_names)

    async def async_select_source(self, source: str):
        await self._hdmi_switcher.select_input(self._source_bidict.inverse.get(source))
        self._source = source
