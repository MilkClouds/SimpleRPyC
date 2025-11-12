"""WebSocket RPC server."""

import asyncio
import secrets
from urllib.parse import parse_qs, urlparse

import websockets

from simplerpyc.common.serialization import deserialize, serialize
from simplerpyc.server.executor import ClientExecutor


class RPCServer:
    """WebSocket-based RPC server."""

    def __init__(self, host: str = "localhost", port: int = 0):
        """Initialize RPC server.

        Args:
            host: Host to bind to
            port: Port to bind to (0 for auto)
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
        try:
            self.server = await websockets.serve(self.handler, self.host, self.port)
            # Get the actual assigned port from the server socket (important when port=0)
            self.port = next(iter(self.server.sockets)).getsockname()[1]
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
        print("\nSet environment variables:")
        print(f"  export SIMPLERPYC_HOST='{self.host}'")
        print(f"  export SIMPLERPYC_PORT='{self.port}'")
        print(f"  export SIMPLERPYC_TOKEN='{self.token}'")
        print("\nOr connect with:")
        print(f"  simplerpyc.connect('{self.host}', {self.port}, token='{self.token}')")

        # Wait forever (until cancelled)
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            print("\nShutting down server...")
            self.server.close()
            await self.server.wait_closed()
            print("Server stopped.")

    def run(self):
        """Run server (blocking)."""
        try:
            asyncio.run(self.serve())
        except KeyboardInterrupt:
            pass  # Graceful shutdown handled in serve()


def main():
    """Entry point for python -m simplerpyc.server."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="SimpleRPyC Server")
    parser.add_argument("--host", default=os.environ.get("SIMPLERPYC_HOST", "localhost"), help="Host to bind to")
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("SIMPLERPYC_PORT", "0")), help="Port to bind to (0 for auto)"
    )

    args = parser.parse_args()

    server = RPCServer(args.host, args.port)
    server.run()


if __name__ == "__main__":  # pragma: no cover
    main()
