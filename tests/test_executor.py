"""Tests for simplerpyc.server.executor module."""

from unittest.mock import Mock

from simplerpyc.server.executor import ClientExecutor


class TestClientExecutor:
    """Test ClientExecutor class."""

    def test_init(self):
        """Test executor initialization."""
        executor = ClientExecutor()
        assert executor.globals == {"__builtins__": __builtins__}
        assert executor.objects == {}
        assert executor.next_obj_id == 0

    def test_store_object(self):
        """Test storing objects."""
        executor = ClientExecutor()

        obj1 = "test_object"
        obj_id1 = executor._store_object(obj1)

        assert obj_id1 == 0
        assert executor.objects[0] == obj1
        assert executor.next_obj_id == 1

        obj2 = [1, 2, 3]
        obj_id2 = executor._store_object(obj2)

        assert obj_id2 == 1
        assert executor.objects[1] == obj2
        assert executor.next_obj_id == 2


class TestImportModule:
    """Test import_module handler."""

    def test_import_builtin_module(self):
        """Test importing a built-in module."""
        executor = ClientExecutor()

        response = executor._import_module("os")

        assert response["type"] == "success"
        assert "obj_id" in response
        assert executor.objects[response["obj_id"]].__name__ == "os"

    def test_import_stdlib_module(self):
        """Test importing a standard library module."""
        executor = ClientExecutor()

        response = executor._import_module("json")

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]].__name__ == "json"

    def test_import_submodule(self):
        """Test importing a submodule."""
        executor = ClientExecutor()

        response = executor._import_module("os.path")

        assert response["type"] == "success"
        # Should store the top-level module
        assert executor.objects[response["obj_id"]].__name__ == "os"


class TestGetattr:
    """Test getattr handler."""

    def test_getattr_from_path(self):
        """Test getting attribute using path."""
        executor = ClientExecutor()

        # First import os
        import_response = executor._import_module("os")  # noqa: F841

        # Then get getcwd attribute
        response = executor._getattr("os", None, "getcwd")

        assert response["type"] == "success"
        assert callable(executor.objects[response["obj_id"]])

    def test_getattr_from_obj_id(self):
        """Test getting attribute using object ID."""
        executor = ClientExecutor()

        # Store an object
        test_obj = Mock()
        test_obj.my_attr = "test_value"
        obj_id = executor._store_object(test_obj)

        # Get attribute
        response = executor._getattr("", obj_id, "my_attr")

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == "test_value"

    def test_getattr_nested(self):
        """Test getting nested attributes."""
        executor = ClientExecutor()

        # Import os
        executor._import_module("os")

        # Get os.path
        response = executor._getattr("os", None, "path")

        assert response["type"] == "success"
        assert (
            executor.objects[response["obj_id"]].__name__ == "posixpath"
            or executor.objects[response["obj_id"]].__name__ == "ntpath"
        )


class TestCall:
    """Test call handler."""

    def test_call_function_by_path(self):
        """Test calling a function using path."""
        executor = ClientExecutor()

        # Import os
        executor._import_module("os")

        # Call os.getcwd()
        response = executor._call("os.getcwd", None, (), {})

        assert response["type"] == "success"
        assert isinstance(executor.objects[response["obj_id"]], str)

    def test_call_function_by_obj_id(self):
        """Test calling a function using object ID."""
        executor = ClientExecutor()

        # Store a callable
        def test_func(a, b):
            return a + b

        obj_id = executor._store_object(test_func)

        # Call it
        response = executor._call("", obj_id, (2, 3), {})

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == 5

    def test_call_with_args_and_kwargs(self):
        """Test calling with both args and kwargs."""
        executor = ClientExecutor()

        def test_func(a, b, c=10):
            return a + b + c

        obj_id = executor._store_object(test_func)

        response = executor._call("", obj_id, (1, 2), {"c": 3})

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == 6

    def test_call_method_on_object(self):
        """Test calling a method on an object."""
        executor = ClientExecutor()

        # Store an object with a method
        test_list = [1, 2, 3]
        obj_id = executor._store_object(test_list)

        # Call append method
        response = executor._call("test_list.append", obj_id, (4,), {})

        assert response["type"] == "success"
        assert test_list == [1, 2, 3, 4]


class TestGetitem:
    """Test getitem handler."""

    def test_getitem_list(self):
        """Test getting item from list."""
        executor = ClientExecutor()

        test_list = [10, 20, 30]
        obj_id = executor._store_object(test_list)

        response = executor._getitem(obj_id, 1)

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == 20

    def test_getitem_dict(self):
        """Test getting item from dict."""
        executor = ClientExecutor()

        test_dict = {"key": "value", "number": 42}
        obj_id = executor._store_object(test_dict)

        response = executor._getitem(obj_id, "key")

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == "value"

    def test_getitem_string(self):
        """Test getting character from string."""
        executor = ClientExecutor()

        test_str = "hello"
        obj_id = executor._store_object(test_str)

        response = executor._getitem(obj_id, 0)

        assert response["type"] == "success"
        assert executor.objects[response["obj_id"]] == "h"


class TestMaterialize:
    """Test materialize handler."""

    def test_materialize_simple_value(self):
        """Test materializing a simple value."""
        executor = ClientExecutor()

        obj_id = executor._store_object(42)

        response = executor._materialize(obj_id)

        assert response["type"] == "success"
        assert response["value"] == 42

    def test_materialize_string(self):
        """Test materializing a string."""
        executor = ClientExecutor()

        obj_id = executor._store_object("test string")

        response = executor._materialize(obj_id)

        assert response["type"] == "success"
        assert response["value"] == "test string"

    def test_materialize_list(self):
        """Test materializing a list."""
        executor = ClientExecutor()

        test_list = [1, 2, 3, 4, 5]
        obj_id = executor._store_object(test_list)

        response = executor._materialize(obj_id)

        assert response["type"] == "success"
        assert response["value"] == test_list

    def test_materialize_dict(self):
        """Test materializing a dict."""
        executor = ClientExecutor()

        test_dict = {"key": "value", "nested": {"a": 1}}
        obj_id = executor._store_object(test_dict)

        response = executor._materialize(obj_id)

        assert response["type"] == "success"
        assert response["value"] == test_dict


class TestHandleMessage:
    """Test handle_message dispatcher."""

    def test_handle_import_module(self):
        """Test handling import_module message."""
        executor = ClientExecutor()

        msg = {"type": "import_module", "module": "os"}
        response = executor.handle_message(msg)

        assert response["type"] == "success"
        assert "obj_id" in response

    def test_handle_getattr(self):
        """Test handling getattr message."""
        executor = ClientExecutor()

        executor._import_module("os")

        msg = {"type": "getattr", "path": "os", "obj_id": None, "attr": "getcwd"}
        response = executor.handle_message(msg)

        assert response["type"] == "success"

    def test_handle_call(self):
        """Test handling call message."""
        executor = ClientExecutor()

        executor._import_module("os")

        msg = {"type": "call", "path": "os.getcwd", "obj_id": None, "args": (), "kwargs": {}}
        response = executor.handle_message(msg)

        assert response["type"] == "success"

    def test_handle_getitem(self):
        """Test handling getitem message."""
        executor = ClientExecutor()

        obj_id = executor._store_object([1, 2, 3])

        msg = {"type": "getitem", "obj_id": obj_id, "key": 0}
        response = executor.handle_message(msg)

        assert response["type"] == "success"

    def test_handle_materialize(self):
        """Test handling materialize message."""
        executor = ClientExecutor()

        obj_id = executor._store_object("test")

        msg = {"type": "materialize", "obj_id": obj_id}
        response = executor.handle_message(msg)

        assert response["type"] == "success"
        assert response["value"] == "test"

    def test_handle_unknown_message_type(self):
        """Test handling unknown message type."""
        executor = ClientExecutor()

        msg = {"type": "unknown_type"}
        response = executor.handle_message(msg)

        assert response["type"] == "error"
        assert "Unknown message type" in response["error"]

    def test_handle_message_with_exception(self):
        """Test handling message that raises exception."""
        executor = ClientExecutor()

        msg = {"type": "getitem", "obj_id": 999, "key": 0}
        response = executor.handle_message(msg)

        assert response["type"] == "error"
        assert "exception_type" in response
        assert "exception_message" in response
        assert "traceback" in response
