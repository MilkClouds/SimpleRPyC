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
            handlers = {
                "import_module": lambda: self._import_module(msg["module"]),
                "getattr": lambda: self._getattr(msg["path"], msg.get("obj_id"), msg["attr"]),
                "call": lambda: self._call(msg["path"], msg.get("obj_id"), msg["args"], msg["kwargs"]),
                "getitem": lambda: self._getitem(msg["obj_id"], msg["key"]),
                "materialize": lambda: self._materialize(msg["obj_id"]),
            }
            handler = handlers.get(msg["type"])
            if handler:
                return handler()
            return {"type": "error", "error": f"Unknown message type: {msg['type']}"}
        except Exception as e:
            return {"type": "error", "error": str(e), "traceback": traceback.format_exc()}

    def _import_module(self, module_name: str) -> dict:
        """Import module and return object ID."""
        exec(f"import {module_name}", self.globals)
        module = self.globals[module_name.split(".")[0]]
        return {"type": "success", "obj_id": self._store_object(module)}

    def _getattr(self, path: str, obj_id: int | None, attr: str) -> dict:
        """Get attribute from object and return object ID."""
        obj = self.objects[obj_id] if obj_id is not None else eval(path, self.globals)
        return {"type": "success", "obj_id": self._store_object(getattr(obj, attr))}

    def _call(self, path: str, obj_id: int | None, args: tuple, kwargs: dict) -> dict:
        """Call function/method and return result object ID."""
        if obj_id is not None:
            obj = self.objects[obj_id]
            func = obj if callable(obj) else getattr(obj, path.split(".")[-1].rstrip("()"))
        else:
            func = eval(path, self.globals)
        return {"type": "success", "obj_id": self._store_object(func(*args, **kwargs))}

    def _getitem(self, obj_id: int, key: Any) -> dict:
        """Get item from object and return object ID."""
        return {"type": "success", "obj_id": self._store_object(self.objects[obj_id][key])}

    def _materialize(self, obj_id: int) -> dict:
        """Serialize object and return actual value."""
        from simplerpc.common.serialization import serialize

        obj = self.objects[obj_id]
        serialize(obj)  # Test serialization
        return {"type": "success", "value": obj}

    def _store_object(self, obj: Any) -> int:
        """Store object and return its ID."""
        obj_id = self.next_obj_id
        self.next_obj_id += 1
        self.objects[obj_id] = obj
        return obj_id
