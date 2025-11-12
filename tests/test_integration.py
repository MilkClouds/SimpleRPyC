"""Integration tests for simplerpyc."""

import asyncio
import threading
import time

import pytest

from simplerpyc.client.connection import connect
from simplerpyc.client.proxy import is_proxy, materialize
from simplerpyc.server.server import RPCServer


@pytest.fixture
def server():
    """Start server."""
    server = RPCServer(host="localhost", port=-1)

    def run_server():
        asyncio.run(server.serve())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(0.5)

    yield server


@pytest.fixture
def conn(server):
    """Create connection."""
    connection = connect("localhost", server.port, token=server.token)
    yield connection
    connection.unpatch_all()
    connection.disconnect()


class TestBasicIntegration:
    """Basic integration tests."""

    def test_connect(self, conn):
        """Test connection."""
        assert conn is not None

    def test_modules(self, conn):
        """Test modules namespace."""
        assert is_proxy(conn.modules.os)

    def test_function_call(self, conn):
        """Test function call."""
        assert materialize(conn.modules.math.sqrt(16)) == 4.0

    def test_builtins(self, conn):
        """Test builtins."""
        assert materialize(conn.builtins.len([1, 2, 3])) == 3

    def test_eval(self, conn):
        """Test eval."""
        assert materialize(conn.eval("2 + 3")) == 5

    def test_execute(self, conn):
        """Test execute."""
        conn.execute("x = 42")
        assert materialize(conn.eval("x")) == 42

    def test_teleport(self, conn):
        """Test teleport."""
        remote_square = conn.teleport(lambda x: x**2)
        assert materialize(remote_square(5)) == 25


class TestModuleOperations:
    """Test module operations."""

    def test_attribute_access(self, conn):
        """Test attribute access."""
        version = materialize(conn.modules.sys.version)
        assert isinstance(version, str)

    def test_function_with_args(self, conn):
        """Test function with args."""
        assert materialize(conn.modules.math.pow(2, 3)) == 8.0

    def test_chained_operations(self, conn):
        """Test chained operations."""
        path = materialize(conn.modules.os.path.join("a", "b", "c"))
        assert "a" in path and "b" in path and "c" in path


class TestIndexingOperations:
    """Test indexing operations."""

    def test_list_indexing(self, conn):
        """Test list indexing."""
        first_path = materialize(conn.modules.sys.path[0])
        assert isinstance(first_path, str)

    def test_dict_indexing(self, conn):
        """Test dict indexing."""
        value = materialize(conn.modules.os.environ["PATH"])
        assert isinstance(value, str)


class TestErrorHandling:
    """Test error handling."""

    def test_attribute_error(self, conn):
        """Test AttributeError."""
        from simplerpyc.client.proxy import RemoteException

        with pytest.raises(RemoteException) as exc_info:
            materialize(conn.modules.os.nonexistent_attribute)

        assert hasattr(exc_info.value, "remote_traceback")
        assert isinstance(exc_info.value.__cause__, AttributeError)

    def test_import_error(self, conn):
        """Test ImportError."""
        from simplerpyc.client.proxy import RemoteException

        with pytest.raises(RemoteException) as exc_info:
            conn.modules.nonexistent_module_xyz

        assert hasattr(exc_info.value, "remote_traceback")
        assert isinstance(exc_info.value.__cause__, (ModuleNotFoundError, ImportError))


class TestComplexScenarios:
    """Test complex scenarios."""

    def test_json_round_trip(self, conn):
        """Test JSON round trip."""
        remote_json = conn.modules.json
        data = {"key": "value", "number": 42}
        json_str = materialize(remote_json.dumps(data))
        result = materialize(remote_json.loads(json_str))
        assert result == data

    def test_multiple_modules(self, conn):
        """Test multiple modules."""
        assert materialize(conn.modules.math.sqrt(25)) == 5.0
        assert isinstance(materialize(conn.modules.os.sep), str)

    def test_patch_module(self, conn):
        """Test patch_module."""
        conn.patch_module("math")

        import math as remote_math

        assert materialize(remote_math.sqrt(16)) == 4.0


class TestServerErrors:
    """Test server error handling."""

    def test_invalid_token(self):
        """Test connection with invalid token."""
        import websockets

        server = RPCServer(host="localhost", port=-1)

        def run_server():
            asyncio.run(server.serve())

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        time.sleep(0.5)

        async def test_invalid():
            uri = f"ws://localhost:{server.port}?token=invalid_token"
            with pytest.raises(websockets.exceptions.ConnectionClosedError):
                async with websockets.connect(uri) as ws:
                    await ws.recv()

        asyncio.run(test_invalid())

    def test_port_exhaustion(self):
        """Test port exhaustion error."""
        from unittest.mock import patch

        server = RPCServer(host="localhost", port=-1)

        async def mock_serve_fail(*args, **kwargs):
            raise OSError("Port in use")

        with patch("websockets.serve", side_effect=mock_serve_fail):
            with pytest.raises(RuntimeError, match="No available port found"):
                asyncio.run(server.serve())

    def test_specific_port_failure(self):
        """Test specific port binding failure."""
        from unittest.mock import patch

        server = RPCServer(host="localhost", port=8888)

        async def mock_serve_fail(*args, **kwargs):
            raise OSError("Port in use")

        with patch("websockets.serve", side_effect=mock_serve_fail):
            with pytest.raises(RuntimeError, match="Failed to bind to localhost:8888"):
                asyncio.run(server.serve())

    def test_connection_closed(self, server):
        """Test connection closed handling."""
        import websockets

        async def test_disconnect():
            uri = f"ws://localhost:{server.port}?token={server.token}"
            async with websockets.connect(uri) as ws:
                await ws.close()

        asyncio.run(test_disconnect())
        time.sleep(0.1)
