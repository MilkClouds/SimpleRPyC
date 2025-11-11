"""Client execution context."""

import traceback
from typing import Any


class ClientExecutor:
    """Manages execution context for a single client."""

    def __init__(self):
        self.globals = {"__builtins__": __builtins__}
        self.objects = {}  # obj_id -> object
        self.next_obj_id = 0

    def handle_message(self, msg: dict) -> dict:
        """Handle client message and return response."""
        try:
            msg_type = msg["type"]

            if msg_type == "import_module":
                return self._import_module(msg["module"])
            elif msg_type == "getattr":
                return self._getattr(msg["path"], msg.get("obj_id"), msg["attr"])
            elif msg_type == "call":
                return self._call(msg["path"], msg.get("obj_id"), msg["args"], msg["kwargs"])
            elif msg_type == "getitem":
                return self._getitem(msg["obj_id"], msg["key"])
            elif msg_type == "materialize":
                return self._materialize(msg["obj_id"])
            else:
                return {"type": "error", "error": f"Unknown message type: {msg_type}"}

        except Exception as e:
            return {"type": "error", "error": str(e), "traceback": traceback.format_exc()}

    def _import_module(self, module_name: str) -> dict:
        """Import module and return object ID."""
        exec(f"import {module_name}", self.globals)
        module = self.globals[module_name.split(".")[0]]
        obj_id = self._store_object(module)
        return {"type": "success", "obj_id": obj_id}

    def _getattr(self, path: str, obj_id: int | None, attr: str) -> dict:
        """Get attribute from object and return object ID."""
        if obj_id is not None:
            obj = self.objects[obj_id]
        else:
            obj = eval(path, self.globals)

        result = getattr(obj, attr)
        result_id = self._store_object(result)
        return {"type": "success", "obj_id": result_id}

    def _call(self, path: str, obj_id: int | None, args: tuple, kwargs: dict) -> dict:
        """Call function/method and return result object ID."""
        if obj_id is not None:
            # Call on existing object
            obj = self.objects[obj_id]
            # If object is callable, call it directly
            if callable(obj):
                func = obj
            else:
                # Otherwise get method from object
                method_name = path.split(".")[-1].rstrip("()")
                func = getattr(obj, method_name)
        else:
            # Module function call
            func = eval(path, self.globals)

        result = func(*args, **kwargs)
        result_id = self._store_object(result)
        return {"type": "success", "obj_id": result_id}

    def _getitem(self, obj_id: int, key: Any) -> dict:
        """Get item from object and return object ID."""
        obj = self.objects[obj_id]
        result = obj[key]
        result_id = self._store_object(result)
        return {"type": "success", "obj_id": result_id}

    def _materialize(self, obj_id: int) -> dict:
        """Serialize object and return actual value."""
        obj = self.objects[obj_id]

        # Test serialization
        from simplerpc.common.serialization import serialize

        serialize(obj)  # Will raise if not serializable

        return {"type": "success", "value": obj}

    def _store_object(self, obj: Any) -> int:
        """Store object and return its ID."""
        obj_id = self.next_obj_id
        self.next_obj_id += 1
        self.objects[obj_id] = obj
        return obj_id
