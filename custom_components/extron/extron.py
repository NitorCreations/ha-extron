import asyncio
import logging
from asyncio import StreamReader, StreamWriter
from asyncio.exceptions import TimeoutError
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    SURROUND_SOUND_PROCESSOR = 'surround_sound_processor'
    HDMI_SWITCHER = 'hdmi_switcher'
    UNKNOWN = 'unknown'


@dataclass
class DeviceInformation:
    model_name: str
    model_description: str
    firmware_version: str
    part_number: str
    mac_address: str


class AuthenticationFailed(Exception):
    pass


class ExtronDevice:
    def __init__(self, device_type: DeviceType, host: str, port: int, password: str) -> None:
        self._device_type = device_type
        self._host = host
        self._port = port
        self._password = password
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None
        self._connected = False

    async def _read_until(self, phrase: str) -> str | None:
        b = bytearray()

        while not self._reader.at_eof():
            byte = await self._reader.read(1)
            b += byte

            if b.endswith(phrase.encode()):
                return b.decode()

    async def attempt_login(self):
        await self._read_until("Password:")
        self._writer.write(f"{self._password}\r".encode())
        await self._writer.drain()
        await self._read_until("Login Administrator\r\n")

    async def connect(self):
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)

        try:
            await asyncio.wait_for(self.attempt_login(), timeout=5)
            self._connected = True
            logger.info(f'Connected and authenticated to {self._host}:{self._port}')
        except TimeoutError:
            raise AuthenticationFailed()

    async def disconnect(self):
        self._connected = False
        self._writer.close()
        await self._writer.wait_closed()

    def is_connected(self) -> bool:
        return self._connected

    def get_device_type(self):
        return self._device_type

    async def _run_command_internal(self, command: str):
        self._writer.write(f"{command}\n".encode())
        await self._writer.drain()

        return await self._read_until("\r\n")

    async def _run_command(self, command: str):
        # Serialize all access to the telnet connection
        async with asyncio.Semaphore():
            try:
                response = await asyncio.wait_for(self._run_command_internal(command), timeout=3)

                if response is None:
                    raise RuntimeError('Command failed')
                else:
                    return response.strip()
            except TimeoutError:
                raise RuntimeError('Command timed out')
            except (ConnectionResetError, BrokenPipeError):
                self._connected = False
                logger.warning('Connection seems to be broken, will attempt to reconnect')
            finally:
                if not self._connected:
                    await self.connect()

    async def query_model_name(self):
        return await self._run_command("1I")

    async def query_model_description(self):
        return await self._run_command("2I")

    async def query_firmware_version(self):
        return await self._run_command("Q")

    async def query_part_number(self):
        return await self._run_command("N")

    async def query_mac_address(self):
        return await self._run_command("\x1B" + "CH")

    async def query_device_information(self) -> DeviceInformation:
        return DeviceInformation(
            model_name=await self.query_model_name(),
            model_description=await self.query_model_description(),
            firmware_version=await self.query_firmware_version(),
            part_number=await self.query_part_number(),
            mac_address=await self.query_mac_address(),
        )


class SurroundSoundProcessor(ExtronDevice):
    def __init__(self, host: str, port: int, password: str) -> None:
        super().__init__(DeviceType.SURROUND_SOUND_PROCESSOR, host, port, password)

    async def view_input(self):
        return await self._run_command("$")

    async def mute(self):
        await self._run_command('1Z')

    async def unmute(self):
        await self._run_command('0Z')

    async def is_muted(self) -> bool:
        is_muted = await self._run_command('Z')
        return is_muted == "1"

    async def get_volume_level(self):
        volume = await self._run_command('V')
        return int(volume)

    async def set_volume_level(self, level: int):
        await self._run_command(f'{level}V')

    async def increment_volume(self):
        await self._run_command('+V')

    async def decrement_volume(self):
        await self._run_command('-V')


class HDMISwitcher(ExtronDevice):
    def __init__(self, host: str, port: int, password: str) -> None:
        super().__init__(DeviceType.HDMI_SWITCHER, host, port, password)

    async def view_input(self):
        return await self._run_command("!")
