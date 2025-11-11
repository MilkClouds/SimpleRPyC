"""Tests for simplerpc.client.connection module."""

import os
from unittest.mock import AsyncMock, patch

import pytest

from simplerpc.client.connection import Connection, connect, disconnect, get_connection
from simplerpc.common.serialization import serialize


class TestConnection:
    """Test Connection class."""

    def test_init(self):
        """Test Connection initialization."""
        conn = Connection()
        assert conn.ws is None
        assert conn.loop is None

    def test_connect_success(self, mock_websocket):
        """Test successful connection."""
        conn = Connection()

        async def mock_connect(*args, **kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
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
        """Test connection uses token from environment."""
        conn = Connection()

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "env_token"}):
                conn.connect("localhost", 8000)

                assert conn.ws is mock_websocket

    def test_send_message(self, mock_websocket):
        """Test sending a message."""
        conn = Connection()

        # Mock the response
        response_data = serialize({"type": "success", "value": 42})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)

                message = {"type": "test", "data": "hello"}
                result = conn.send(message)

                assert result == {"type": "success", "value": 42}
                mock_websocket.send.assert_called_once()

    def test_disconnect(self, mock_websocket):
        """Test disconnecting."""
        conn = Connection()

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
                conn.connect("localhost", 8000)
                conn.disconnect()

                mock_websocket.close.assert_called_once()

    def test_disconnect_when_not_connected(self):
        """Test disconnect when not connected."""
        conn = Connection()
        conn.disconnect()  # Should not raise


class TestGetConnection:
    """Test get_connection function."""

    def teardown_method(self):
        """Clean up global connection."""
        import simplerpc.client.connection as conn_module

        conn_module._connection = None

    def test_get_connection_creates_singleton(self):
        """Test get_connection creates singleton instance."""
        conn1 = get_connection()
        conn2 = get_connection()

        assert conn1 is conn2
        assert isinstance(conn1, Connection)

    def test_get_connection_returns_same_instance(self):
        """Test multiple calls return same instance."""
        instances = [get_connection() for _ in range(5)]

        assert all(inst is instances[0] for inst in instances)


class TestConnectFunction:
    """Test module-level connect function."""

    def teardown_method(self):
        """Clean up global connection."""
        disconnect()

    def test_connect_creates_connection(self, mock_websocket):
        """Test connect function creates and configures connection."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
                connect("localhost", 8000)

                conn = get_connection()
                assert conn.ws is mock_websocket

    def test_connect_with_explicit_token(self, mock_websocket):
        """Test connect with explicit token parameter."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            connect("localhost", 8000, token="my_token")

            conn = get_connection()
            assert conn.ws is mock_websocket

    def test_connect_default_params(self, mock_websocket):
        """Test connect with default parameters."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
                connect()  # Uses defaults: localhost, 8000

                conn = get_connection()
                assert conn.ws is mock_websocket


class TestDisconnectFunction:
    """Test module-level disconnect function."""

    def test_disconnect_clears_connection(self, mock_websocket):
        """Test disconnect clears global connection."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
                connect("localhost", 8000)

                import simplerpc.client.connection as conn_module

                assert conn_module._connection is not None

                disconnect()

                assert conn_module._connection is None

    def test_disconnect_when_not_connected(self):
        """Test disconnect when no connection exists."""
        disconnect()  # Should not raise

    def test_disconnect_calls_connection_disconnect(self, mock_websocket):
        """Test disconnect calls Connection.disconnect."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
                connect("localhost", 8000)
                disconnect()

                mock_websocket.close.assert_called_once()


class TestConnectionIntegration:
    """Integration tests for connection module."""

    def teardown_method(self):
        """Clean up."""
        disconnect()

    def test_full_connection_lifecycle(self, mock_websocket):
        """Test complete connection lifecycle."""
        response_data = serialize({"type": "success", "obj_id": 1})
        mock_websocket.recv = AsyncMock(return_value=response_data)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
                # Connect
                connect("localhost", 8000)

                # Send message
                conn = get_connection()
                result = conn.send({"type": "test"})
                assert result["type"] == "success"

                # Disconnect
                disconnect()

                # Verify cleanup
                import simplerpc.client.connection as conn_module

                assert conn_module._connection is None

    def test_reconnect_after_disconnect(self, mock_websocket):
        """Test reconnecting after disconnect."""

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
                # First connection
                connect("localhost", 8000)
                conn1 = get_connection()

                # Disconnect
                disconnect()

                # Reconnect
                connect("localhost", 8000)
                conn2 = get_connection()

                # Should be different instances
                assert conn1 is not conn2

    def test_send_multiple_messages(self, mock_websocket):
        """Test sending multiple messages in sequence."""
        responses = [
            serialize({"type": "success", "obj_id": 1}),
            serialize({"type": "success", "obj_id": 2}),
            serialize({"type": "success", "obj_id": 3}),
        ]
        mock_websocket.recv = AsyncMock(side_effect=responses)

        async def mock_connect(*_args, **_kwargs):
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect):
            with patch.dict(os.environ, {"SIMPLERPC_TOKEN": "test_token"}):
                connect("localhost", 8000)
                conn = get_connection()

                result1 = conn.send({"type": "test1"})
                result2 = conn.send({"type": "test2"})
                result3 = conn.send({"type": "test3"})

                assert result1["obj_id"] == 1
                assert result2["obj_id"] == 2
                assert result3["obj_id"] == 3
                assert mock_websocket.send.call_count == 3
