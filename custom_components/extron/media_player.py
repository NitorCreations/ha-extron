import asyncio
import logging

from datetime import timedelta

from bidict import bidict
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyextron import DeviceType, ExtronDevice, HDMISwitcher, SurroundSoundProcessor

from custom_components.extron import DeviceInformation, ExtronConfigEntryRuntimeData
from custom_components.extron.const import CONF_DEVICE_TYPE

logger = logging.getLogger(__name__)

# Don't poll more often than this, the SSP has been seen to lock up when polled frequently (see #24)
SCAN_INTERVAL = timedelta(seconds=30)


def make_source_bidict(num_sources: int, input_names: list[str]) -> bidict:
    # Use user-defined input name for the source when available
    return bidict({i + 1: input_names[i] if i < len(input_names) else str(i + 1) for i in range(num_sources)})


async def async_setup_entry(_hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    # Extract stored runtime data from the entry
    runtime_data: ExtronConfigEntryRuntimeData = entry.runtime_data
    device = runtime_data.device
    device_information = runtime_data.device_information
    input_names = runtime_data.input_names

    # Add entities
    if entry.data[CONF_DEVICE_TYPE] == DeviceType.SURROUND_SOUND_PROCESSOR.value:
        ssp = SurroundSoundProcessor(device)
        async_add_entities([ExtronSurroundSoundProcessor(ssp, device_information, input_names)], update_before_add=True)
    elif entry.data[CONF_DEVICE_TYPE] == DeviceType.HDMI_SWITCHER.value:
        hdmi_switcher = HDMISwitcher(device)
        async_add_entities([ExtronHDMISwitcher(hdmi_switcher, device_information, input_names)], update_before_add=True)


class AbstractExtronMediaPlayerEntity(MediaPlayerEntity):
    def __init__(self, device: ExtronDevice, device_information: DeviceInformation, input_names: list[str]) -> None:
        self._device = device
        self._device_information = device_information
        self._input_names = input_names
        self._device_class = MediaPlayerDeviceClass.RECEIVER
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

        # Volume level (0-100) that has been requested but not yet written to the device, and the task writing it
        self._pending_volume: int | None = None
        self._volume_writer: asyncio.Task | None = None

    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
    )

    def get_device_type(self):
        return DeviceType.SURROUND_SOUND_PROCESSOR

    async def async_update(self):
        try:
            async with self._ssp._device.connection():
                self._source = self._source_bidict.get(await self._ssp.view_input())
                self._muted = await self._ssp.is_muted()
                volume = await self._ssp.get_volume_level()
                # Don't overwrite the optimistic volume with a stale one if a newer level is waiting to be written
                if self._pending_volume is None:
                    self._volume = volume / 100
        except Exception:
            logger.exception("An error occurred while trying to update entity state")
            self._attr_available = False
        else:
            self._attr_available = True

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
        async with self._ssp._device.connection():
            await self._ssp.select_input(self._source_bidict.inverse.get(source))

    async def async_mute_volume(self, mute: bool) -> None:
        async with self._ssp._device.connection():
            await self._ssp.mute() if mute else await self._ssp.unmute()

    async def async_set_volume_level(self, volume: float) -> None:
        # Sliders can call this for every step they're dragged across. Instead of opening a connection for each call
        # and running them one by one (which takes a long time to catch up), only remember the latest requested level
        # and let a single writer task send it, over one connection, until it has caught up.
        self._pending_volume = round(volume * 100)
        self._volume = self._pending_volume / 100
        self.async_write_ha_state()

        if self._volume_writer is None or self._volume_writer.done():
            self._volume_writer = self.hass.async_create_task(self._write_pending_volume())

        await asyncio.shield(self._volume_writer)

    async def _write_pending_volume(self) -> None:
        try:
            # The outer loop catches levels requested while the connection was being closed
            while self._pending_volume is not None:
                async with self._ssp._device.connection():
                    while (level := self._pending_volume) is not None:
                        await self._ssp.set_volume_level(level)

                        # Done unless a new level was requested while we were busy
                        if self._pending_volume == level:
                            self._pending_volume = None
        except Exception:
            self._pending_volume = None
            raise

    async def async_volume_up(self) -> None:
        async with self._ssp._device.connection():
            if int(self._volume * 100) < 100:
                await self._ssp.increment_volume()

    async def async_volume_down(self) -> None:
        async with self._ssp._device.connection():
            if int(self._volume * 100) > 0:
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
        try:
            async with self._hdmi_switcher._device.connection():
                self._source = self._source_bidict.get(await self._hdmi_switcher.view_input())
        except Exception:
            logger.exception("An error occurred while trying to update entity state")
            self._attr_available = False
        else:
            self._attr_available = True

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
        async with self._hdmi_switcher._device.connection():
            await self._hdmi_switcher.select_input(self._source_bidict.inverse.get(source))
