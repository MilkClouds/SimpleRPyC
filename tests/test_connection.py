"""Tests for simplerpyc.client.connection module."""

import os
from unittest.mock import AsyncMock, patch

import pytest

from simplerpyc.client.connection import Connection, connect
from simplerpyc.client.proxy import RemoteException
from simplerpyc.common.serialization import serialize


class TestConnection:
    """Test Connection class."""

    def test_init(self):
        """Test initialization."""
        conn = Connection()

        assert conn.ws is None
        assert conn.loop is None

    def test_connect_success(self, mock_websocket):
        """Test successful connection."""
        conn = Connection()

        async def mock_connect(*args, **kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)

                assert conn.ws is mock_websocket
                assert conn.loop is not None

    def test_connect_with_token(self, mock_websocket):
        """Test connection with explicit token."""
        conn = Connection()

        async def mock_connect(*args, **kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            conn.connect("localhost", 8000, token="explicit_token")

            assert conn.ws is mock_websocket

    def test_connect_no_token_error(self):
        """Test connection fails without token."""
        conn = Connection()

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Token must be provided"):
                conn.connect("localhost", 8000)

    def test_connect_from_env_token(self, mock_websocket):
        """Test connection uses environment token."""
        conn = Connection()

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "env_token"}):
                conn.connect("localhost", 8000)

                assert conn.ws is mock_websocket

    def test_send(self, mock_websocket):
        """Test send message."""
        conn = Connection()
        response_data = serialize({"type": "success", "value": 42})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)

                result = conn.send({"type": "test", "data": "hello"})

                assert result == {"type": "success", "value": 42}
                mock_websocket.send.assert_called_once()

    def test_disconnect(self, mock_websocket):
        """Test disconnect."""
        conn = Connection()

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                conn.disconnect()

                mock_websocket.close.assert_called_once()

    def test_disconnect_when_not_connected(self):
        """Test disconnect when not connected."""
        conn = Connection()
        conn.disconnect()


class TestConnectFunction:
    """Test module-level connect function."""

    def test_connect_creates_connection(self, mock_websocket):
        """Test connect function."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn = connect("localhost", 8000)

                assert conn.ws is mock_websocket
                assert isinstance(conn, Connection)

    def test_connect_with_token(self, mock_websocket):
        """Test connect with explicit token."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            conn = connect("localhost", 8000, token="my_token")
            assert conn.ws is mock_websocket

    def test_connect_defaults(self, mock_websocket):
        """Test connect with defaults."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn = connect()
                assert conn.ws is mock_websocket

    def test_connect_with_env_vars(self, mock_websocket):
        """Test connect with environment variables."""

        async def mock_connect(url, *_args, **_kwargs):
            # Verify the URL contains the correct host and port from env vars
            assert "testhost" in url
            assert "9999" in url
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(
                os.environ,
                {
                    "SIMPLERPYC_HOST": "testhost",
                    "SIMPLERPYC_PORT": "9999",
                    "SIMPLERPYC_TOKEN": "test_token",
                },
            ):
                conn = connect()
                assert conn.ws is mock_websocket

    def test_connect_explicit_overrides_env(self, mock_websocket):
        """Test that explicit parameters override environment variables."""

        async def mock_connect(url, *_args, **_kwargs):
            # Verify the URL contains the explicit values, not env vars
            assert "explicit_host" in url
            assert "7777" in url
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(
                os.environ,
                {
                    "SIMPLERPYC_HOST": "env_host",
                    "SIMPLERPYC_PORT": "9999",
                    "SIMPLERPYC_TOKEN": "env_token",
                },
            ):
                conn = connect("explicit_host", 7777, token="explicit_token")
                assert conn.ws is mock_websocket


class TestConnectionIntegration:
    """Integration tests."""

    def test_full_lifecycle(self, mock_websocket):
        """Test full connection lifecycle."""
        response_data = serialize({"type": "success", "obj_id": 1})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn = connect("localhost", 8000)
                result = conn.send({"type": "test"})

                assert result["type"] == "success"

                conn.disconnect()

    def test_multiple_connections(self, mock_websocket):
        """Test multiple connections."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn1 = connect("localhost", 8000)
                conn2 = connect("localhost", 8000)

                assert conn1 is not conn2

    def test_multiple_messages(self, mock_websocket):
        """Test sending multiple messages."""
        responses = [
            serialize({"type": "success", "obj_id": 1}),
            serialize({"type": "success", "obj_id": 2}),
            serialize({"type": "success", "obj_id": 3}),
        ]
        mock_websocket.recv = AsyncMock(side_effect=responses)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn = connect("localhost", 8000)
                result1 = conn.send({"type": "test1"})
                result2 = conn.send({"type": "test2"})
                result3 = conn.send({"type": "test3"})

                assert result1["obj_id"] == 1
                assert result2["obj_id"] == 2
                assert result3["obj_id"] == 3
                assert mock_websocket.send.call_count == 3


class TestModulesNamespace:
    """Test _ModulesNamespace."""

    def test_getattr_success(self, mock_websocket):
        """Test getattr success."""
        conn = Connection()
        response_data = serialize({"type": "success", "obj_id": 1})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                proxy = conn.modules.os
                assert proxy._rpc_obj_id == 1

    def test_getitem_success(self, mock_websocket):
        """Test getitem success."""
        conn = Connection()
        response_data = serialize({"type": "success", "obj_id": 2})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                proxy = conn.modules["sys"]
                assert proxy._rpc_obj_id == 2


class TestBuiltinsNamespace:
    """Test _BuiltinsNamespace."""

    def test_getattr_success(self, mock_websocket):
        """Test getattr success."""
        conn = Connection()
        response_data = serialize({"type": "success", "obj_id": 3})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                proxy = conn.builtins.print
                assert proxy._rpc_obj_id == 3

    def test_getattr_error(self, mock_websocket):
        """Test getattr error."""
        conn = Connection()
        response_data = serialize(
            {
                "type": "error",
                "exception_type": "AttributeError",
                "exception_message": "builtin not found",
                "traceback": None,
                "exception_pickle": None,
            }
        )
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                with pytest.raises(RemoteException):
                    conn.builtins.nonexistent


class TestConnectionMethods:
    """Test Connection methods."""

    def test_namespace_success(self, mock_websocket):
        """Test namespace property."""
        conn = Connection()
        response_data = serialize({"type": "success", "namespace": {"x": 1, "y": 2}})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                ns = conn.namespace
                assert ns == {"x": 1, "y": 2}

    def test_namespace_error(self, mock_websocket):
        """Test namespace error."""
        conn = Connection()
        response_data = serialize(
            {
                "type": "error",
                "exception_type": "RuntimeError",
                "exception_message": "namespace error",
                "traceback": None,
                "exception_pickle": None,
            }
        )
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                with pytest.raises(RemoteException):
                    conn.namespace

    def test_eval_success(self, mock_websocket):
        """Test eval success."""
        conn = Connection()
        response_data = serialize({"type": "success", "obj_id": 5})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                result = conn.eval("1 + 1")
                assert result._rpc_obj_id == 5

    def test_eval_error(self, mock_websocket):
        """Test eval error."""
        conn = Connection()
        response_data = serialize(
            {
                "type": "error",
                "exception_type": "SyntaxError",
                "exception_message": "invalid syntax",
                "traceback": None,
                "exception_pickle": None,
            }
        )
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                with pytest.raises(RemoteException):
                    conn.eval("invalid syntax")

    def test_execute_success(self, mock_websocket):
        """Test execute success."""
        conn = Connection()
        response_data = serialize({"type": "success"})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                conn.execute("x = 1")

    def test_execute_error(self, mock_websocket):
        """Test execute error."""
        conn = Connection()
        response_data = serialize(
            {
                "type": "error",
                "exception_type": "NameError",
                "exception_message": "name not defined",
                "traceback": None,
                "exception_pickle": None,
            }
        )
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                with pytest.raises(RemoteException):
                    conn.execute("undefined_var")

    def test_teleport_success(self, mock_websocket):
        """Test teleport success."""
        conn = Connection()
        response_data = serialize({"type": "success", "obj_id": 6})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)

                def my_func():
                    return 42

                result = conn.teleport(my_func)
                assert result._rpc_obj_id == 6

    def test_teleport_error(self, mock_websocket):
        """Test teleport error."""
        conn = Connection()
        response_data = serialize(
            {
                "type": "error",
                "exception_type": "RuntimeError",
                "exception_message": "teleport failed",
                "traceback": None,
                "exception_pickle": None,
            }
        )
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)

                def my_func():
                    return 42

                with pytest.raises(RemoteException):
                    conn.teleport(my_func)

    def test_patch_module_success(self, mock_websocket):
        """Test patch_module success."""
        import sys

        conn = Connection()
        response_data = serialize({"type": "success", "obj_id": 7})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                original_module = sys.modules.get("fake_module")
                try:
                    proxy = conn.patch_module("fake_module")
                    assert proxy._rpc_obj_id == 7
                    assert sys.modules["fake_module"] == proxy
                finally:
                    if original_module is None:
                        sys.modules.pop("fake_module", None)
                    else:
                        sys.modules["fake_module"] = original_module

    def test_patch_module_idempotent(self, mock_websocket):
        """Test patch_module is idempotent."""
        import sys

        conn = Connection()
        response_data = serialize({"type": "success", "obj_id": 8})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                original_module = sys.modules.get("fake_module2")
                try:
                    proxy1 = conn.patch_module("fake_module2")
                    proxy2 = conn.patch_module("fake_module2")
                    assert proxy1 == proxy2
                    assert mock_websocket.send.call_count == 1
                finally:
                    if original_module is None:
                        sys.modules.pop("fake_module2", None)
                    else:
                        sys.modules["fake_module2"] = original_module

    def test_patch_module_error(self, mock_websocket):
        """Test patch_module error."""
        conn = Connection()
        response_data = serialize(
            {
                "type": "error",
                "exception_type": "ImportError",
                "exception_message": "module not found",
                "traceback": None,
                "exception_pickle": None,
            }
        )
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                with pytest.raises(RemoteException):
                    conn.patch_module("nonexistent_module")

    def test_unpatch_module(self, mock_websocket):
        """Test unpatch_module."""
        import sys

        conn = Connection()
        response_data = serialize({"type": "success", "obj_id": 9})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                original_module = sys.modules.get("fake_module3")
                try:
                    conn.patch_module("fake_module3")
                    assert "fake_module3" in sys.modules
                    conn.unpatch_module("fake_module3")
                    assert "fake_module3" not in sys.modules
                finally:
                    if original_module is not None:
                        sys.modules["fake_module3"] = original_module

    def test_connect_runtime_error(self, mock_websocket):
        """Test connect with RuntimeError."""
        conn = Connection()

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPYC_TOKEN": "test_token"}):
                with patch("asyncio.get_event_loop", side_effect=RuntimeError("no event loop")):
                    conn.connect("localhost", 8000)
                    assert conn.loop is not None
