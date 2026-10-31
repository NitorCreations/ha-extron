import asyncio

from datetime import timedelta
from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant, callback
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pyextron import ResponseError
from pytelnetdevice import TelnetDevice
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.extron.const import DOMAIN
from custom_components.extron.media_player import SCAN_INTERVAL
from tests.fake_extron import FakeExtron

ENTITY_ID = "media_player.extron_ssp_200_media_player"


async def setup_integration(hass: HomeAssistant, fake_extron: FakeExtron) -> None:
    # Provides homeassistant.update_entity
    assert await async_setup_component(hass, "homeassistant", {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "127.0.0.1",
            "port": fake_extron.port,
            "password": fake_extron.password,
            "device_type": "surround_sound_processor",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def wait_for_volume_level(hass: HomeAssistant, level: float, timeout: float = 2) -> None:
    # Polling runs as a background task, which hass.async_block_till_done() doesn't wait for
    async with asyncio.timeout(timeout):
        while volume_level(hass) != level:
            await asyncio.sleep(0.01)


def volume_level(hass: HomeAssistant) -> float | None:
    return hass.states.get(ENTITY_ID).attributes.get("volume_level")


async def set_volume(hass: HomeAssistant, level: float, blocking: bool = True) -> None:
    await hass.services.async_call(
        "media_player", "volume_set", {"entity_id": ENTITY_ID, "volume_level": level}, blocking=blocking
    )


async def drag_slider(hass: HomeAssistant, start: int, end: int, interval: float) -> None:
    # Like a slider that calls volume_set (without waiting) for every step it's dragged across
    for pct in range(start, end + 1):
        await set_volume(hass, pct / 100, blocking=False)
        await asyncio.sleep(interval)
    await hass.async_block_till_done()


async def test_slider_drag_is_coalesced(hass: HomeAssistant, fake_extron: FakeExtron):
    fake_extron.login_delay = 0.05
    fake_extron.command_delay = 0.02
    await setup_integration(hass, fake_extron)
    connections_before = fake_extron.connections

    await drag_slider(hass, 20, 60, interval=0)

    assert fake_extron.volume == 60
    assert volume_level(hass) == 0.6
    # Without coalescing this would be 41 set commands, each on its own connection
    set_commands = fake_extron.volume_set_commands()
    assert set_commands[-1] == "60V"
    assert len(set_commands) <= 3
    # The writer connection plus the refresh after the service calls
    assert fake_extron.connections - connections_before <= 3


async def test_slow_slider_drag_follows_without_queueing(hass: HomeAssistant, fake_extron: FakeExtron):
    fake_extron.login_delay = 0.05
    fake_extron.command_delay = 0.02
    await setup_integration(hass, fake_extron)
    connections_before = fake_extron.connections

    start = asyncio.get_running_loop().time()
    await drag_slider(hass, 20, 60, interval=0.01)
    elapsed = asyncio.get_running_loop().time() - start

    assert fake_extron.volume == 60
    assert volume_level(hass) == 0.6
    # All steps are written over a handful of connections instead of logging in for each one
    assert fake_extron.connections - connections_before <= 5
    # Sending 41 commands, each with its own login, would take at least 41 * (0.05 + 0.02) = 2.9 s
    assert elapsed < 2


async def test_volume_does_not_jump_back_while_dragging(hass: HomeAssistant, fake_extron: FakeExtron):
    fake_extron.login_delay = 0.05
    fake_extron.command_delay = 0.05
    await setup_integration(hass, fake_extron)

    levels = []

    @callback
    def record_level(event):
        if event.data["entity_id"] == ENTITY_ID:
            levels.append(event.data["new_state"].attributes.get("volume_level"))

    hass.bus.async_listen("state_changed", record_level)

    async def poll_repeatedly():
        for _ in range(10):
            await hass.services.async_call("homeassistant", "update_entity", {"entity_id": ENTITY_ID}, blocking=True)

    await asyncio.gather(drag_slider(hass, 20, 60, interval=0.01), poll_repeatedly())

    # Neither the polling nor the refreshes after each service call may show an older level than what was requested
    assert levels == sorted(levels)
    assert levels[-1] == 0.6


async def test_volume_is_reported_optimistically(hass: HomeAssistant, fake_extron: FakeExtron):
    await setup_integration(hass, fake_extron)
    fake_extron.login_delay = 0.5

    await set_volume(hass, 0.8, blocking=False)
    await asyncio.sleep(0.1)

    assert fake_extron.volume == 50
    assert volume_level(hass) == 0.8

    await hass.async_block_till_done()
    assert fake_extron.volume == 80
    assert volume_level(hass) == 0.8


async def test_level_requested_while_disconnecting_is_written(hass: HomeAssistant, fake_extron: FakeExtron):
    await setup_integration(hass, fake_extron)

    disconnecting = asyncio.Event()
    original_disconnect = TelnetDevice.disconnect

    async def slow_disconnect(self):
        disconnecting.set()
        await asyncio.sleep(0.2)
        await original_disconnect(self)

    with patch.object(TelnetDevice, "disconnect", slow_disconnect):
        await set_volume(hass, 0.3, blocking=False)
        await disconnecting.wait()
        await set_volume(hass, 0.4, blocking=False)
        await hass.async_block_till_done()

    assert fake_extron.volume_set_commands() == ["30V", "40V"]
    assert fake_extron.volume == 40
    assert volume_level(hass) == 0.4


@pytest.mark.parametrize("percent", range(101))
async def test_volume_level_is_rounded(hass: HomeAssistant, fake_extron: FakeExtron, percent: int):
    await setup_integration(hass, fake_extron)

    # e.g. 0.29 * 100 == 28.999999999999996, which used to be truncated to 28
    await set_volume(hass, percent / 100)

    assert fake_extron.volume == percent


async def test_failed_volume_set_recovers(hass: HomeAssistant, fake_extron: FakeExtron):
    await setup_integration(hass, fake_extron)
    fake_extron.failing_commands = {"70V"}

    with pytest.raises(ResponseError):
        await set_volume(hass, 0.7)

    # The level the device actually has is shown again, and new levels can still be set
    await hass.services.async_call("homeassistant", "update_entity", {"entity_id": ENTITY_ID}, blocking=True)
    assert volume_level(hass) == 0.5

    await set_volume(hass, 0.6)
    assert fake_extron.volume == 60
    assert volume_level(hass) == 0.6


async def test_volume_knob_change_shows_up_on_next_poll(hass: HomeAssistant, fake_extron: FakeExtron):
    await setup_integration(hass, fake_extron)
    assert volume_level(hass) == 0.5

    fake_extron.turn_knob(35)
    async_fire_time_changed(hass, dt_util.utcnow() + SCAN_INTERVAL + timedelta(seconds=1))

    await wait_for_volume_level(hass, 0.35)
