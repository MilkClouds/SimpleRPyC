"""Tests for simplerpyc.server.executor module."""

from unittest.mock import Mock

import pytest

from simplerpyc.client.proxy import RPCProxy
from simplerpyc.server.executor import ClientExecutor


class TestClientExecutor:
    """Test ClientExecutor class."""

    def test_init(self):
        """Test initialization."""
        executor = ClientExecutor()

        assert executor.globals == {"__builtins__": __builtins__}
        assert executor.objects == {}
        assert executor.next_obj_id == 0

    def test_store_object(self):
        """Test storing objects."""
        executor = ClientExecutor()

        obj_id1 = executor._store_object("test_object")
        obj_id2 = executor._store_object([1, 2, 3])

        assert obj_id1 == 0
        assert executor.objects[0] == "test_object"
        assert obj_id2 == 1
        assert executor.objects[1] == [1, 2, 3]
        assert executor.next_obj_id == 2


class TestImportModule:
    """Test import_module handler."""

    def test_builtin_module(self):
        """Test importing builtin module."""
        executor = ClientExecutor()

        response = executor._import_module("os")

        assert response["type"] == "success"
        assert "obj_id" in response
        assert executor.objects[response["obj_id"]].__name__ == "os"

    def test_stdlib_module(self):
        """Test importing stdlib module."""
        executor = ClientExecutor()

        response = executor._import_module("json")

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]].__name__ == "json"

    def test_submodule(self):
        """Test importing submodule."""
        executor = ClientExecutor()

        response = executor._import_module("os.path")

        assert response["type"] == "success"
        # Should return the actual submodule, not the root module
        assert executor.objects[response["obj_id"]].__name__ in ("posixpath", "ntpath")


class TestGetattr:
    """Test getattr handler."""

    def test_from_path(self):
        """Test getattr from path."""
        executor = ClientExecutor()
        executor._import_module("os")

        response = executor._getattr("os", None, "getcwd")

        assert response["type"] == "success"
        assert callable(executor.objects[response["obj_id"]])

    def test_from_obj_id(self):
        """Test getattr from object ID."""
        executor = ClientExecutor()
        test_obj = Mock()
        test_obj.my_attr = "test_value"
        obj_id = executor._store_object(test_obj)

        response = executor._getattr("", obj_id, "my_attr")

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == "test_value"

    def test_nested(self):
        """Test nested attributes."""
        executor = ClientExecutor()
        executor._import_module("os")

        response = executor._getattr("os", None, "path")

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]].__name__ in ("posixpath", "ntpath")


class TestCall:
    """Test call handler."""

    def test_by_path(self):
        """Test call by path."""
        executor = ClientExecutor()
        executor._import_module("os")

        response = executor._call("os.getcwd", None, (), {})

        assert response["type"] == "success"
        assert isinstance(executor.objects[response["obj_id"]], str)

    def test_by_obj_id(self):
        """Test call by object ID."""
        executor = ClientExecutor()
        obj_id = executor._store_object(lambda a, b: a + b)

        response = executor._call("", obj_id, (2, 3), {})

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == 5

    def test_with_args_and_kwargs(self):
        """Test call with args and kwargs."""
        executor = ClientExecutor()
        obj_id = executor._store_object(lambda a, b, c=10: a + b + c)

        response = executor._call("", obj_id, (1, 2), {"c": 3})

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == 6

    def test_method(self):
        """Test calling method."""
        executor = ClientExecutor()
        test_list = [1, 2, 3]
        obj_id = executor._store_object(test_list)

        response = executor._call("test_list.append", obj_id, (4,), {})

        assert response["type"] == "success"
        assert test_list == [1, 2, 3, 4]


class TestGetitem:
    """Test getitem handler."""

    def test_list(self):
        """Test getitem from list."""
        executor = ClientExecutor()
        obj_id = executor._store_object([10, 20, 30])

        response = executor._getitem(obj_id, 1)

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == 20

    def test_dict(self):
        """Test getitem from dict."""
        executor = ClientExecutor()
        obj_id = executor._store_object({"key": "value", "number": 42})

        response = executor._getitem(obj_id, "key")

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == "value"

    def test_string(self):
        """Test getitem from string."""
        executor = ClientExecutor()
        obj_id = executor._store_object("hello")

        response = executor._getitem(obj_id, 0)

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == "h"


class TestMaterialize:
    """Test materialize handler."""

    def test_simple_value(self):
        """Test materialize simple value."""
        executor = ClientExecutor()
        obj_id = executor._store_object(42)

        response = executor._materialize(obj_id)

        assert response["type"] == "success"
        assert response["value"] == 42

    def test_string(self):
        """Test materialize string."""
        executor = ClientExecutor()
        obj_id = executor._store_object("test string")

        response = executor._materialize(obj_id)

        assert response["type"] == "success"
        assert response["value"] == "test string"

    def test_list(self):
        """Test materialize list."""
        executor = ClientExecutor()
        obj_id = executor._store_object([1, 2, 3, 4, 5])

        response = executor._materialize(obj_id)

        assert response["type"] == "success"
        assert response["value"] == [1, 2, 3, 4, 5]

    def test_dict(self):
        """Test materialize dict."""
        executor = ClientExecutor()
        obj_id = executor._store_object({"key": "value", "nested": {"a": 1}})

        response = executor._materialize(obj_id)

        assert response["type"] == "success"
        assert response["value"] == {"key": "value", "nested": {"a": 1}}


class TestHandleMessage:
    """Test handle_message dispatcher."""

    def test_import_module(self):
        """Test import_module message."""
        executor = ClientExecutor()

        response = executor.handle_message({"type": "import_module", "module": "os"})

        assert response["type"] == "success"
        assert "obj_id" in response

    def test_getattr(self):
        """Test getattr message."""
        executor = ClientExecutor()
        executor._import_module("os")

        response = executor.handle_message({"type": "getattr", "path": "os", "obj_id": None, "attr": "getcwd"})

        assert response["type"] == "success"

    def test_call(self):
        """Test call message."""
        executor = ClientExecutor()
        executor._import_module("os")

        response = executor.handle_message(
            {"type": "call", "path": "os.getcwd", "obj_id": None, "args": (), "kwargs": {}}
        )

        assert response["type"] == "success"

    def test_getitem(self):
        """Test getitem message."""
        executor = ClientExecutor()
        obj_id = executor._store_object([1, 2, 3])

        response = executor.handle_message({"type": "getitem", "obj_id": obj_id, "key": 0})

        assert response["type"] == "success"

    def test_materialize(self):
        """Test materialize message."""
        executor = ClientExecutor()
        obj_id = executor._store_object("test")

        response = executor.handle_message({"type": "materialize", "obj_id": obj_id})

        assert response["type"] == "success"
        assert response["value"] == "test"

    def test_unknown_type(self):
        """Test unknown message type."""
        executor = ClientExecutor()

        response = executor.handle_message({"type": "unknown_type"})

        assert response["type"] == "error"
        assert "Unknown message type" in response["error"]

    def test_exception(self):
        """Test message with exception."""
        executor = ClientExecutor()

        response = executor.handle_message({"type": "getitem", "obj_id": 999, "key": 0})

        assert response["type"] == "error"
        assert "exception_type" in response


class TestResolveProxies:
    """Test _resolve_proxies method."""

    def test_resolve_proxy_in_dict_raises_error(self):
        """Test resolving RPCProxy in dict raises ValueError."""
        executor = ClientExecutor()
        mock_proxy = Mock(spec=RPCProxy)
        executor.objects[0] = mock_proxy

        with pytest.raises(ValueError, match="Server object store contains RPCProxy"):
            executor._resolve_proxies({"__rpc_proxy__": True, "obj_id": 0})

    def test_resolve_direct_proxy_raises_error(self):
        """Test resolving direct RPCProxy raises ValueError."""
        executor = ClientExecutor()
        mock_proxy = Mock(spec=RPCProxy)

        with pytest.raises(ValueError, match="RPCProxy object found in server-side data"):
            executor._resolve_proxies(mock_proxy)

    def test_get_namespace(self):
        """Test _get_namespace method."""
        executor = ClientExecutor()
        executor.globals["test_var"] = 42

        result = executor._get_namespace()

        assert result["type"] == "success"
        assert "namespace" in result
        assert "test_var" in result["namespace"]
        assert result["namespace"]["test_var"] == "<class 'int'>"
