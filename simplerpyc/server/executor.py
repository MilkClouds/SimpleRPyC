"""Client execution context."""

from typing import Any


class ClientExecutor:
    """Manages execution context for a single client."""

    def __init__(self):
        """Initialize client executor."""
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
                "get_namespace": lambda: self._get_namespace(),
                "get_builtin": lambda: self._get_builtin(msg["name"]),
                "eval": lambda: self._eval(msg["expr"]),
                "execute": lambda: self._execute(msg["code"]),
                "teleport": lambda: self._teleport(msg["func_bytes"], msg["name"]),
            }
            handler = handlers.get(msg["type"])
            if handler:
                return handler()
            return {"type": "error", "error": f"Unknown message type: {msg['type']}"}
        except Exception as e:
            from simplerpyc.common.serialization import serialize_exception

            return {"type": "error", **serialize_exception(e)}

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

        # Resolve proxy references in args and kwargs
        resolved_args = self._resolve_proxies(args)
        resolved_kwargs = self._resolve_proxies(kwargs)

        # Call the function and get result
        result = func(*resolved_args, **resolved_kwargs)

        # Store and return
        return {"type": "success", "obj_id": self._store_object(result)}

    def _getitem(self, obj_id: int, key: Any) -> dict:
        """Get item from object and return object ID."""
        resolved_key = self._resolve_proxies(key)
        return {"type": "success", "obj_id": self._store_object(self.objects[obj_id][resolved_key])}

    def _materialize(self, obj_id: int) -> dict:
        """Serialize object and return actual value."""
        from simplerpyc.common.serialization import serialize

        obj = self.objects[obj_id]
        serialize(obj)  # Test serialization
        return {"type": "success", "value": obj}

    def _resolve_proxies(self, obj: Any) -> Any:
        """Resolve proxy references and slices to actual objects."""
        # Import here to avoid circular dependency
        from simplerpyc.client.proxy import RPCProxy

        if isinstance(obj, dict):
            if obj.get("__rpc_proxy__"):
                resolved = self.objects[obj["obj_id"]]
                # Ensure we're not returning a proxy object
                if isinstance(resolved, RPCProxy):
                    raise ValueError(f"Server object store contains RPCProxy at id {obj['obj_id']}")
                return resolved
            elif obj.get("__slice__"):
                return slice(obj["start"], obj["stop"], obj["step"])
            return {k: self._resolve_proxies(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return type(obj)(self._resolve_proxies(item) for item in obj)
        # If we somehow got a proxy object directly, raise an error
        elif isinstance(obj, RPCProxy):
            raise ValueError("RPCProxy object found in server-side data")
        return obj

    def _store_object(self, obj: Any) -> int:
        """Store object and return its ID."""
        obj_id = self.next_obj_id
        self.next_obj_id += 1
        self.objects[obj_id] = obj
        return obj_id

    def _get_namespace(self) -> dict:
        """Return namespace keys (not values, to avoid serialization issues)."""
        return {"type": "success", "namespace": {k: str(type(v)) for k, v in self.globals.items()}}

    def _get_builtin(self, name: str) -> dict:
        """Get builtin function/class by name."""
        import builtins

        obj = getattr(builtins, name)
        return {"type": "success", "obj_id": self._store_object(obj)}

    def _eval(self, expr: str) -> dict:
        """Evaluate expression and return object ID."""
        result = eval(expr, self.globals)
        return {"type": "success", "obj_id": self._store_object(result)}

    def _execute(self, code: str) -> dict:
        """Execute code in namespace."""
        exec(code, self.globals)
        return {"type": "success"}

    def _teleport(self, func_bytes: bytes, name: str) -> dict:
        """Deserialize function, add to namespace, and return object ID."""
        import dill

        func = dill.loads(func_bytes)
        self.globals[name] = func
        return {"type": "success", "obj_id": self._store_object(func)}
