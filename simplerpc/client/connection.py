"""WebSocket connection management."""

import asyncio
import os

import websockets

from simplerpc.common.serialization import deserialize, serialize


class Connection:
    """Manages WebSocket connection to RPC server."""

    def __init__(self):
        self.ws = None
        self.loop = None

    def connect(self, host: str, port: int, token: str | None = None):
        """Connect to RPC server."""
        if token is None:
            token = os.environ.get("SIMPLERPC_TOKEN")
            if not token:
                raise ValueError("Token must be provided or set in SIMPLERPC_TOKEN env var")

        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        async def _connect():
            self.ws = await websockets.connect(f"ws://{host}:{port}?token={token}")

        self.loop.run_until_complete(_connect())

    def send(self, message: dict) -> dict:
        """Send message synchronously."""

        async def _send():
            await self.ws.send(serialize(message))
            return deserialize(await self.ws.recv())

        return self.loop.run_until_complete(_send())

    def disconnect(self):
        """Disconnect from server."""
        if self.ws:

            async def _disconnect():
                await self.ws.close()

            self.loop.run_until_complete(_disconnect())


# Global connection instance
_connection = None


def get_connection() -> Connection:
    """Get global connection instance."""
    global _connection
    if _connection is None:
        _connection = Connection()
    return _connection


def connect(host: str = "localhost", port: int = 8000, token: str | None = None):
    """Connect to RPC server."""
    get_connection().connect(host, port, token)


def disconnect():
    """Disconnect from RPC server."""
    global _connection
    if _connection:
        _connection.disconnect()
        _connection = None
