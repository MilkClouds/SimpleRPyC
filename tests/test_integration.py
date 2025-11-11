"""Integration tests for simplerpc."""

import asyncio
import threading
import time

import pytest

from simplerpc.client.connection import connect, disconnect
from simplerpc.client.patcher import patch_module, unpatch_all
from simplerpc.client.proxy import is_proxy, materialize
from simplerpc.server.server import RPCServer


@pytest.fixture
def server():
    """Start server in background thread."""
    server = RPCServer(host="localhost", port=-1)
    
    # Start server in background thread
    def run_server():
        asyncio.run(server.serve())
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    
    # Wait for server to start
    time.sleep(0.5)
    
    yield server
    
    # Cleanup
    disconnect()
    unpatch_all()


class TestBasicIntegration:
    """Basic integration tests."""

    def test_connect_and_disconnect(self, server):
        """Test basic connection lifecycle."""
        connect("localhost", server.port, token=server.token)
        disconnect()

    def test_import_module(self, server):
        """Test importing a module."""
        connect("localhost", server.port, token=server.token)
        patch_module("os")
        
        import os as remote_os
        assert is_proxy(remote_os)

    def test_simple_function_call(self, server):
        """Test calling a simple function."""
        connect("localhost", server.port, token=server.token)
        patch_module("math")
        
        import math as remote_math
        result = materialize(remote_math.sqrt(16))
        assert result == 4.0


class TestModuleOperations:
    """Test module operations."""

    def test_attribute_access(self, server):
        """Test accessing module attributes."""
        connect("localhost", server.port, token=server.token)
        patch_module("sys")
        
        import sys as remote_sys
        version = materialize(remote_sys.version)
        assert isinstance(version, str)

    def test_function_with_arguments(self, server):
        """Test function calls with arguments."""
        connect("localhost", server.port, token=server.token)
        patch_module("math")
        
        import math as remote_math
        result = materialize(remote_math.pow(2, 3))
        assert result == 8.0

    def test_chained_operations(self, server):
        """Test chained attribute access and calls."""
        connect("localhost", server.port, token=server.token)
        patch_module("os")
        
        import os as remote_os
        path = materialize(remote_os.path.join("a", "b", "c"))
        assert "a" in path and "b" in path and "c" in path


class TestIndexingOperations:
    """Test indexing operations."""

    def test_list_indexing(self, server):
        """Test list indexing."""
        connect("localhost", server.port, token=server.token)
        patch_module("sys")
        
        import sys as remote_sys
        first_path = materialize(remote_sys.path[0])
        assert isinstance(first_path, str)

    def test_dict_indexing(self, server):
        """Test dict indexing."""
        connect("localhost", server.port, token=server.token)
        patch_module("os")
        
        import os as remote_os
        # environ is a dict-like object
        proxy = remote_os.environ["PATH"]
        value = materialize(proxy)
        assert isinstance(value, str)


class TestErrorHandling:
    """Test error handling."""

    def test_attribute_error(self, server):
        """Test AttributeError propagation."""
        connect("localhost", server.port, token=server.token)
        patch_module("os")
        
        import os as remote_os
        from simplerpc.client.proxy import RemoteException
        
        with pytest.raises(RemoteException):
            materialize(remote_os.nonexistent_attribute)

    def test_import_error(self, server):
        """Test ImportError propagation."""
        connect("localhost", server.port, token=server.token)
        from simplerpc.client.proxy import RemoteException
        
        with pytest.raises(RemoteException):
            patch_module("nonexistent_module_xyz")
            import nonexistent_module_xyz  # noqa: F401


class TestComplexScenarios:
    """Test complex scenarios."""

    def test_json_round_trip(self, server):
        """Test JSON serialization round trip."""
        connect("localhost", server.port, token=server.token)
        patch_module("json")
        
        import json as remote_json
        data = {"key": "value", "number": 42}
        json_str = materialize(remote_json.dumps(data))
        result = materialize(remote_json.loads(json_str))
        assert result == data

    def test_multiple_modules(self, server):
        """Test using multiple modules."""
        connect("localhost", server.port, token=server.token)
        patch_module("math")
        patch_module("os")
        
        import math as remote_math
        import os as remote_os
        
        sqrt_result = materialize(remote_math.sqrt(25))
        sep = materialize(remote_os.sep)
        
        assert sqrt_result == 5.0
        assert isinstance(sep, str)

