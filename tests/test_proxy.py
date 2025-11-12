"""Tests for simplerpyc.client.proxy module."""

import pytest

from simplerpyc.client.proxy import RemoteException, RPCProxy, is_proxy, materialize


class TestRPCProxy:
    """Test RPCProxy class."""

    def test_init(self, mock_connection):
        """Test RPCProxy initialization."""
        proxy = RPCProxy(path="test.module", obj_id=42, connection=mock_connection)
        assert proxy._rpc_path == "test.module"
        assert proxy._rpc_obj_id == 42
        assert proxy._rpc_connection == mock_connection

    def test_init_defaults(self, mock_connection):
        """Test RPCProxy initialization with defaults."""
        proxy = RPCProxy(connection=mock_connection)
        assert proxy._rpc_path == ""
        assert proxy._rpc_obj_id is None

    def test_getattr_success(self, mock_connection):
        """Test attribute access returns new proxy."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 2}
        proxy = RPCProxy(path="module", obj_id=1, connection=mock_connection)
        result = proxy.attr_name
        assert isinstance(result, RPCProxy)
        assert result._rpc_path == "module.attr_name"
        assert result._rpc_obj_id == 2
        mock_connection.send.assert_called_once_with(
            {"type": "getattr", "path": "module", "obj_id": 1, "attr": "attr_name"}
        )

    def test_getattr_error(self, mock_connection):
        """Test attribute access with error response."""
        mock_connection.send.return_value = {
            "type": "error",
            "exception_type": "builtins.AttributeError",
            "exception_message": "no such attribute",
            "exception_pickle": None,
            "traceback": "Traceback...",
        }
        proxy = RPCProxy(path="module", obj_id=1, connection=mock_connection)
        with pytest.raises(RemoteException) as exc_info:
            _ = proxy.missing_attr
        assert "AttributeError" in str(exc_info.value)
        assert exc_info.value.remote_traceback == "Traceback..."

    def test_call_success(self, mock_connection):
        """Test calling proxy returns new proxy."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 3}
        proxy = RPCProxy(path="module.func", obj_id=2, connection=mock_connection)
        result = proxy(1, 2, key="value")
        assert isinstance(result, RPCProxy)
        assert result._rpc_path == "module.func()"
        assert result._rpc_obj_id == 3
        mock_connection.send.assert_called_once_with(
            {"type": "call", "path": "module.func", "obj_id": 2, "args": (1, 2), "kwargs": {"key": "value"}}
        )

    def test_call_error(self, mock_connection):
        """Test calling proxy with error response."""
        mock_connection.send.return_value = {
            "type": "error",
            "exception_type": "builtins.TypeError",
            "exception_message": "invalid arguments",
            "exception_pickle": None,
            "traceback": None,
        }
        proxy = RPCProxy(path="module.func", obj_id=2, connection=mock_connection)
        with pytest.raises(RemoteException) as exc_info:
            proxy(1, 2)
        assert "TypeError" in str(exc_info.value)

    def test_getitem_success(self, mock_connection):
        """Test indexing proxy returns new proxy."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 4}
        proxy = RPCProxy(path="module.list", obj_id=3, connection=mock_connection)
        result = proxy[0]
        assert isinstance(result, RPCProxy)
        assert result._rpc_path == "module.list[0]"
        assert result._rpc_obj_id == 4
        mock_connection.send.assert_called_once_with({"type": "getitem", "obj_id": 3, "key": 0})

    def test_getitem_error(self, mock_connection):
        """Test indexing proxy with error response."""
        mock_connection.send.return_value = {
            "type": "error",
            "exception_type": "builtins.IndexError",
            "exception_message": "list index out of range",
            "exception_pickle": None,
            "traceback": None,
        }
        proxy = RPCProxy(path="module.list", obj_id=3, connection=mock_connection)
        with pytest.raises(RemoteException):
            _ = proxy[999]

    def test_repr(self, mock_connection):
        """Test proxy string representation."""
        proxy = RPCProxy(path="test.path", obj_id=42, connection=mock_connection)
        assert repr(proxy) == "<RPCProxy: test.path (id=42)>"


class TestRemoteException:
    """Test RemoteException class."""

    def test_init_with_traceback(self):
        """Test RemoteException with traceback."""
        exc = RemoteException("Error message", "Traceback info")
        assert "Error message" in str(exc)
        assert "Traceback info" in str(exc)
        assert exc.remote_traceback == "Traceback info"

    def test_init_without_traceback(self):
        """Test RemoteException without traceback."""
        exc = RemoteException("Error message")
        assert str(exc) == "Error message"
        assert exc.remote_traceback is None

    def test_str_with_traceback(self):
        """Test string representation with traceback."""
        exc = RemoteException("Error message", "Remote traceback:\nLine 1\nLine 2")
        result = str(exc)
        assert "Error message" in result
        assert "Remote traceback:" in result
        assert "Line 1" in result

    def test_str_without_traceback(self):
        """Test string representation without traceback."""
        exc = RemoteException("Error message", None)
        assert str(exc) == "Error message"


class TestMaterialize:
    """Test materialize function."""

    def test_materialize_proxy(self, mock_connection):
        """Test materializing a proxy object."""
        mock_connection.send.return_value = {"type": "success", "value": "actual_value"}
        proxy = RPCProxy(path="test", obj_id=5, connection=mock_connection)
        result = materialize(proxy)
        assert result == "actual_value"
        mock_connection.send.assert_called_once_with({"type": "materialize", "obj_id": 5})

    def test_materialize_non_proxy(self):
        """Test materializing a non-proxy object."""
        regular_obj = {"key": "value"}
        result = materialize(regular_obj)
        assert result is regular_obj

    def test_materialize_error(self, mock_connection):
        """Test materializing with error response."""
        mock_connection.send.return_value = {
            "type": "error",
            "exception_type": "builtins.RuntimeError",
            "exception_message": "Serialization error",
            "exception_pickle": None,
            "traceback": None,
        }
        proxy = RPCProxy(path="test", obj_id=5, connection=mock_connection)
        with pytest.raises(RemoteException):
            materialize(proxy)

    def test_materialize_complex_value(self, mock_connection):
        """Test materializing complex values."""
        complex_value = {"list": [1, 2, 3], "dict": {"nested": True}}
        mock_connection.send.return_value = {"type": "success", "value": complex_value}
        proxy = RPCProxy(path="test", obj_id=6, connection=mock_connection)
        result = materialize(proxy)
        assert result == complex_value


class TestIsProxy:
    """Test is_proxy function."""

    def test_is_proxy_true(self, mock_connection):
        """Test is_proxy returns True for RPCProxy."""
        proxy = RPCProxy(connection=mock_connection)
        assert is_proxy(proxy) is True

    def test_is_proxy_false(self):
        """Test is_proxy returns False for non-proxy objects."""
        assert is_proxy("string") is False
        assert is_proxy(123) is False
        assert is_proxy([1, 2, 3]) is False
        assert is_proxy({"key": "value"}) is False
        assert is_proxy(None) is False


class TestProxyChaining:
    """Test chaining proxy operations."""

    def test_chained_getattr(self, mock_connection):
        """Test chaining attribute access."""
        mock_connection.send.side_effect = [
            {"type": "success", "obj_id": 2},
            {"type": "success", "obj_id": 3},
        ]
        proxy = RPCProxy(path="module", obj_id=1, connection=mock_connection)
        result = proxy.attr1.attr2
        assert result._rpc_path == "module.attr1.attr2"
        assert result._rpc_obj_id == 3

    def test_chained_call_and_getattr(self, mock_connection):
        """Test chaining calls and attribute access."""
        mock_connection.send.side_effect = [
            {"type": "success", "obj_id": 2},
            {"type": "success", "obj_id": 3},
        ]
        proxy = RPCProxy(path="module.func", obj_id=1, connection=mock_connection)
        result = proxy().attr
        assert result._rpc_path == "module.func().attr"
        assert result._rpc_obj_id == 3
