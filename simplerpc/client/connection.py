"""WebSocket connection management."""

import asyncio
import os
import websockets
from simplerpc.common.serialization import serialize, deserialize


class Connection:
    """Manages WebSocket connection to RPC server."""

    def __init__(self):
        self.ws = None
        self.loop = None
        self.request_id = 0

    async def _connect(self, host: str, port: int, token: str):
        """Establish WebSocket connection."""
        uri = f"ws://{host}:{port}?token={token}"
        self.ws = await websockets.connect(uri)

    def connect(self, host: str, port: int, token: str | None = None):
        """Connect to RPC server."""
        if token is None:
            token = os.environ.get("SIMPLERPC_TOKEN")
            if token is None:
                raise ValueError("Token must be provided or set in SIMPLERPC_TOKEN env var")

        # Create event loop if not exists
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        # Connect
        self.loop.run_until_complete(self._connect(host, port, token))

    async def _send(self, message: dict) -> dict:
        """Send message and receive response."""
        # Add request ID
        message["id"] = str(self.request_id)
        self.request_id += 1

        # Serialize and send
        data = serialize(message)
        await self.ws.send(data)

        # Receive response
        response_data = await self.ws.recv()
        return deserialize(response_data)

    def send(self, message: dict) -> dict:
        """Send message synchronously."""
        return self.loop.run_until_complete(self._send(message))

    async def _disconnect(self):
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()

    def disconnect(self):
        """Disconnect from server."""
        if self.ws:
            self.loop.run_until_complete(self._disconnect())


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
    conn = get_connection()
    conn.connect(host, port, token)


def disconnect():
    """Disconnect from RPC server."""
    global _connection
    if _connection:
        _connection.disconnect()
        _connection = None
