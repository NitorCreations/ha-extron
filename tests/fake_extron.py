"""A minimal fake Extron SSP telnet server for tests.

Emulates the login handshake and the subset of SIS commands the integration uses, and records every connection and
command so tests can assert on how the integration talks to the device.
"""

import asyncio
import time

from dataclasses import dataclass, field

BANNER = b"(c) Copyright 2025, Extron Electronics, SSP 200, V1.00, 60-1234-01\r\nFri, 31 Oct 2026 12:00:00\r\n\r\n"


@dataclass
class LoggedCommand:
    at: float
    connection: int
    command: str


@dataclass
class FakeExtron:
    password: str = "extron"
    # Simulated latency of the login handshake and of each command
    login_delay: float = 0.0
    command_delay: float = 0.0

    volume: int = 50
    muted: bool = False
    input: int = 1

    # Commands that should get an error response
    failing_commands: set[str] = field(default_factory=set)

    connections: int = 0
    active_connections: int = 0
    max_active_connections: int = 0
    commands: list[LoggedCommand] = field(default_factory=list)

    _server: asyncio.Server | None = None

    @property
    def port(self) -> int:
        return self._server.sockets[0].getsockname()[1]

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)

    async def stop(self) -> None:
        self._server.close()
        await self._server.wait_closed()

    def turn_knob(self, volume: int) -> None:
        """Simulate someone changing the volume from the front panel."""
        self.volume = volume

    def volume_set_commands(self) -> list[str]:
        return [c.command for c in self.commands if c.command.endswith("V") and c.command[:-1].isdigit()]

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.connections += 1
        connection = self.connections
        self.active_connections += 1
        self.max_active_connections = max(self.max_active_connections, self.active_connections)

        try:
            writer.write(BANNER + b"Password:")
            await writer.drain()

            password = (await reader.readline()).decode().strip()
            await asyncio.sleep(self.login_delay)
            if password != self.password:
                writer.write(b"\r\nPassword:")
                await writer.drain()
                return

            writer.write(b"\r\nLogin Administrator\r\n")
            await writer.drain()

            while line := await reader.readline():
                command = line.decode().rstrip("\r\n")
                self.commands.append(LoggedCommand(time.monotonic(), connection, command))
                await asyncio.sleep(self.command_delay)
                writer.write(f"{self._respond(command)}\r\n".encode())
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            self.active_connections -= 1
            writer.close()

    def _respond(self, command: str) -> str:
        if command in self.failing_commands:
            return "E13"

        static = {
            "1I": "SSP 200",
            "*Q": "1.00.0000",
            "N": "60-1234-01",
            "\x1bCH": "00-05-A6-00-00-01",
            "\x1bCI": "127.0.0.1",
            "\x1b20STAT": "40",
            "34I": "1125*60.00*2200*1920",
            "\x1bLOUT": "1",
            "\x1bIHDCP": "1",
            "\x1bOHDCP": "1",
        }
        if command in static:
            return static[command]

        if command == "V":
            return str(self.volume)
        if command == "+V":
            self.volume = min(100, self.volume + 1)
            return f"Vol{self.volume}"
        if command == "-V":
            self.volume = max(0, self.volume - 1)
            return f"Vol{self.volume}"
        if command.endswith("V") and command[:-1].isdigit():
            self.volume = max(0, min(100, int(command[:-1])))
            return f"Vol{self.volume}"
        if command == "Z":
            return "1" if self.muted else "0"
        if command in ("0Z", "1Z"):
            self.muted = command == "1Z"
            return f"Amt{int(self.muted)}"
        if command == "$":
            return str(self.input)
        if command.endswith("$") and command[:-1].isdigit():
            self.input = int(command[:-1])
            return f"In{self.input} Aud"

        return "E10"
