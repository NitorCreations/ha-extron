import asyncio
from asyncio import StreamReader, StreamWriter
from asyncio.exceptions import TimeoutError
from enum import Enum
from typing import Optional


class DeviceType(Enum):
    SURROUND_SOUND_PROCESSOR = 'surround_sound_processor'
    HDMI_SWITCHER = 'hdmi_switcher'
    UNKNOWN = 'unknown'


class ExtronDevice:
    def __init__(self, device_type: DeviceType, host: str, port: int, password: str) -> None:
        self._device_type = device_type
        self._host = host
        self._port = port
        self._password = password
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None

    async def _read_until(self, phrase: str):
        b = bytearray()

        while True:
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
            await asyncio.wait_for(self.attempt_login(), timeout=3)
        except TimeoutError:
            raise RuntimeError('Authentication failed')

    def get_device_type(self):
        return self._device_type

    async def _run_command(self, command: str):
        async with asyncio.Semaphore():
            self._writer.write(f"{command}\n".encode())
            await self._writer.drain()

            return (await self._read_until("\r\n")).strip()

    async def query_model_name(self):
        return await self._run_command("1I")

    async def query_model_description(self):
        return await self._run_command("2I")

    async def query_firmware_version(self):
        return await self._run_command("Q")


class SurroundSoundProcessor(ExtronDevice):
    def __init__(self, host: str, port: int, password: str) -> None:
        super().__init__(DeviceType.SURROUND_SOUND_PROCESSOR, host, port, password)

    async def view_input(self):
        return await self._run_command("$")


class HDMISwitcher(ExtronDevice):
    def __init__(self, host: str, port: int, password: str) -> None:
        super().__init__(DeviceType.HDMI_SWITCHER, host, port, password)

    async def view_input(self):
        return await self._run_command("!")
