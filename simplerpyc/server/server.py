"""WebSocket RPC server."""

import asyncio
import secrets
from urllib.parse import parse_qs, urlparse

import websockets

from simplerpyc.common.serialization import deserialize, serialize
from simplerpyc.server.executor import ClientExecutor


class RPCServer:
    """WebSocket-based RPC server."""

    def __init__(self, host: str = "localhost", port: int = -1):
        """Initialize RPC server.

        Args:
            host: Host to bind to
            port: Port to bind to (-1 for auto)
        """
        self.host = host
        self.port = port
        self.token = secrets.token_urlsafe(32)
        self.executors = {}  # websocket -> ClientExecutor
        self.server = None

    async def handler(self, websocket):
        """Handle client connection."""
        # Verify token from request URI
        path = websocket.request.path if hasattr(websocket, "request") else websocket.path
        query = parse_qs(urlparse(path).query)
        client_token = query.get("token", [None])[0]

        if client_token != self.token:
            await websocket.close(1008, "Invalid token")
            return

        # Create executor for this client
        executor = ClientExecutor()
        self.executors[websocket] = executor

        print(f"Client connected: {websocket.remote_address}")

        try:
            async for message_data in websocket:
                # Deserialize message
                message = deserialize(message_data)

                # Handle message
                response = executor.handle_message(message)

                # Send response
                response_data = serialize(response)
                await websocket.send(response_data)

        except websockets.ConnectionClosed:
            pass
        finally:
            # Cleanup
            del self.executors[websocket]
            print(f"Client disconnected: {websocket.remote_address}")

    async def serve(self):
        """Start server."""
        # Auto-seek port if port=-1
        if self.port == -1:
            port = 8000
            while True:
                try:
                    self.server = await websockets.serve(self.handler, self.host, port)
                    self.port = port
                    break
                except OSError:
                    port += 1
                    if port > 9000:
                        raise RuntimeError("No available port found between 8000-9000")
        else:
            # Use specified port, panic if fails
            try:
                self.server = await websockets.serve(self.handler, self.host, self.port)
            except OSError as e:
                raise RuntimeError(f"Failed to bind to {self.host}:{self.port}") from e

        print("=" * 70)
        print("⚠️  SECURITY WARNING")
        print("=" * 70)
        print("This server uses UNENCRYPTED WebSocket (ws://) connections.")
        print("Tokens and data are transmitted in PLAINTEXT.")
        print("Only use in TRUSTED PRIVATE NETWORKS (localhost, private LAN, VPN).")
        print("DO NOT expose to public internet!")
        print("=" * 70)
        print()
        print(f"Starting RPC server on {self.host}:{self.port}")
        print(f"Token: {self.token}")
        print("\nSet environment variable:")
        print(f"  export SIMPLERPYC_TOKEN='{self.token}'")
        print("\nOr connect with:")
        print(f"  simplerpyc.connect('{self.host}', {self.port}, token='{self.token}')")

        await asyncio.Future()  # Run forever

    def run(self):
        """Run server (blocking)."""
        asyncio.run(self.serve())


def main():
    """Entry point for python -m simplerpyc.server."""
    import argparse

    parser = argparse.ArgumentParser(description="SimpleRPyC Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=-1, help="Port to bind to (-1 for auto)")

    args = parser.parse_args()

    server = RPCServer(args.host, args.port)
    server.run()


if __name__ == "__main__":
    main()
