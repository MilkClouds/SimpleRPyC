"""WebSocket RPC server."""

import asyncio
import secrets
from urllib.parse import parse_qs, urlparse

import websockets

from simplerpc.common.serialization import deserialize, serialize
from simplerpc.server.executor import ClientExecutor


class RPCServer:
    """WebSocket-based RPC server."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.token = secrets.token_urlsafe(32)
        self.executors = {}  # websocket -> ClientExecutor

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

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Cleanup
            del self.executors[websocket]
            print(f"Client disconnected: {websocket.remote_address}")

    async def serve(self):
        """Start server."""
        print(f"Starting RPC server on {self.host}:{self.port}")
        print(f"Token: {self.token}")
        print("\nSet environment variable:")
        print(f"  export SIMPLERPC_TOKEN='{self.token}'")
        print("\nOr connect with:")
        print(f"  simplerpc.connect('{self.host}', {self.port}, token='{self.token}')")

        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # Run forever

    def run(self):
        """Run server (blocking)."""
        asyncio.run(self.serve())


def main():
    """Entry point for python -m simplerpc.server."""
    import argparse

    parser = argparse.ArgumentParser(description="SimpleRPC Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")

    args = parser.parse_args()

    server = RPCServer(args.host, args.port)
    server.run()


if __name__ == "__main__":
    main()
