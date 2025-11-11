"""Integration tests for simplerpc."""

import asyncio
import sys
import threading
import time

import pytest

from simplerpc.client.connection import connect
from simplerpc.client.proxy import is_proxy, materialize
from simplerpc.server.server import RPCServer


@pytest.fixture
def server():
    """Start server in background thread."""
    server = RPCServer(host="localhost", port=-1)

    def run_server():
        asyncio.run(server.serve())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(0.5)

    yield server


class TestBasicIntegration:
    """Basic integration tests."""

    def test_connect_and_disconnect(self, server):
        """Test basic connection lifecycle."""
        conn = connect("localhost", server.port, token=server.token)
        conn.disconnect()

    def test_modules_namespace(self, server):
        """Test accessing remote modules via conn.modules."""
        conn = connect("localhost", server.port, token=server.token)
        remote_os = conn.modules.os

        assert is_proxy(remote_os)

    def test_simple_function_call(self, server):
        """Test calling a simple function."""
        conn = connect("localhost", server.port, token=server.token)
        remote_math = conn.modules.math
        result = materialize(remote_math.sqrt(16))
        assert result == 4.0

    def test_builtins_namespace(self, server):
        """Test accessing remote builtins."""
        conn = connect("localhost", server.port, token=server.token)
        remote_len = conn.builtins.len
        result = materialize(remote_len([1, 2, 3]))
        assert result == 3

    def test_eval(self, server):
        """Test eval method."""
        conn = connect("localhost", server.port, token=server.token)
        result = materialize(conn.eval("2 + 3"))
        assert result == 5

    def test_execute(self, server):
        """Test execute method."""
        conn = connect("localhost", server.port, token=server.token)
        conn.execute("x = 42")
        result = materialize(conn.eval("x"))
        assert result == 42

    def test_teleport(self, server):
        """Test teleport method."""
        conn = connect("localhost", server.port, token=server.token)

        def square(x):
            return x**2

        remote_square = conn.teleport(square)
        result = materialize(remote_square(5))
        assert result == 25


class TestModuleOperations:
    """Test module operations."""

    def test_attribute_access(self, server):
        """Test accessing module attributes."""
        conn = connect("localhost", server.port, token=server.token)
        remote_sys = conn.modules.sys
        version = materialize(remote_sys.version)
        assert isinstance(version, str)

    def test_function_with_arguments(self, server):
        """Test function calls with arguments."""
        conn = connect("localhost", server.port, token=server.token)
        remote_math = conn.modules.math
        result = materialize(remote_math.pow(2, 3))
        assert result == 8.0

    def test_chained_operations(self, server):
        """Test chained attribute access and calls."""
        conn = connect("localhost", server.port, token=server.token)
        remote_os = conn.modules.os
        path = materialize(remote_os.path.join("a", "b", "c"))
        assert "a" in path and "b" in path and "c" in path


class TestIndexingOperations:
    """Test indexing operations."""

    def test_list_indexing(self, server):
        """Test list indexing."""
        conn = connect("localhost", server.port, token=server.token)
        remote_sys = conn.modules.sys
        first_path = materialize(remote_sys.path[0])
        assert isinstance(first_path, str)

    def test_dict_indexing(self, server):
        """Test dict indexing."""
        conn = connect("localhost", server.port, token=server.token)
        remote_os = conn.modules.os
        proxy = remote_os.environ["PATH"]
        value = materialize(proxy)
        assert isinstance(value, str)


class TestErrorHandling:
    """Test error handling."""

    def test_attribute_error(self, server):
        """Test AttributeError propagation."""
        conn = connect("localhost", server.port, token=server.token)
        remote_os = conn.modules.os

        from simplerpc.client.proxy import RemoteException

        with pytest.raises(RemoteException) as exc_info:
            materialize(remote_os.nonexistent_attribute)

        assert hasattr(exc_info.value, "remote_traceback")
        assert isinstance(exc_info.value.__cause__, AttributeError)

    def test_import_error(self, server):
        """Test ImportError propagation."""
        conn = connect("localhost", server.port, token=server.token)
        from simplerpc.client.proxy import RemoteException

        with pytest.raises(RemoteException) as exc_info:
            conn.modules.nonexistent_module_xyz

        assert hasattr(exc_info.value, "remote_traceback")
        assert isinstance(exc_info.value.__cause__, (ModuleNotFoundError, ImportError))


class TestComplexScenarios:
    """Test complex scenarios."""

    def test_json_round_trip(self, server):
        """Test JSON serialization round trip."""
        conn = connect("localhost", server.port, token=server.token)
        remote_json = conn.modules.json
        data = {"key": "value", "number": 42}
        json_str = materialize(remote_json.dumps(data))
        result = materialize(remote_json.loads(json_str))
        assert result == data

    def test_multiple_modules(self, server):
        """Test using multiple modules."""
        conn = connect("localhost", server.port, token=server.token)
        remote_math = conn.modules.math
        remote_os = conn.modules.os
        sqrt_result = materialize(remote_math.sqrt(25))
        sep = materialize(remote_os.sep)
        assert sqrt_result == 5.0
        assert isinstance(sep, str)

    def test_patch_module(self, server):
        """Test patch_module for sys.modules patching."""
        conn = connect("localhost", server.port, token=server.token)
        conn.patch_module("math")

        import math as remote_math

        result = materialize(remote_math.sqrt(16))
        assert result == 4.0
        sys.modules.pop("math", None)
