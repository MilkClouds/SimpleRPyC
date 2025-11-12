"""WebSocket connection management."""

import asyncio
import os
import sys

import websockets

from simplerpyc.common.serialization import deserialize, serialize


class _ModulesNamespace:
    """Namespace for accessing remote modules."""

    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)

    def __getattr__(self, name: str):
        """Get remote module by attribute access."""
        from simplerpyc.client.proxy import RPCProxy, _raise_deserialized_error

        response = self._conn.send({"type": "import_module", "module": name})
        if response["type"] == "error":
            _raise_deserialized_error(response)
        return RPCProxy(path=name, obj_id=response["obj_id"], connection=self._conn)

    def __getitem__(self, name: str):
        """Get remote module by bracket notation (for nested imports)."""
        return self.__getattr__(name)


class _BuiltinsNamespace:
    """Namespace for accessing remote builtins."""

    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)

    def __getattr__(self, name: str):
        """Get remote builtin by attribute access."""
        from simplerpyc.client.proxy import RPCProxy, _raise_deserialized_error

        response = self._conn.send({"type": "get_builtin", "name": name})
        if response["type"] == "error":
            _raise_deserialized_error(response)
        return RPCProxy(path=f"builtins.{name}", obj_id=response["obj_id"], connection=self._conn)


class Connection:
    """Manages WebSocket connection to RPC server."""

    def __init__(self):
        self.ws = None
        self.loop = None
        self.modules = _ModulesNamespace(self)
        self.builtins = _BuiltinsNamespace(self)
        self._patched_modules = {}  # Track patched modules for cleanup

    def connect(self, host: str, port: int, token: str | None = None):
        """Connect to RPC server."""
        if token is None:
            token = os.environ.get("SIMPLERPYC_TOKEN")
            if not token:
                raise ValueError("Token must be provided or set in SIMPLERPYC_TOKEN env var")

        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        async def _connect():
            self.ws = await websockets.connect(f"ws://{host}:{port}?token={token}")

        self.loop.run_until_complete(_connect())

    @property
    def namespace(self) -> dict:
        """Get remote namespace (globals)."""
        from simplerpyc.client.proxy import _raise_deserialized_error

        response = self.send({"type": "get_namespace"})
        if response["type"] == "error":
            _raise_deserialized_error(response)
        return response["namespace"]

    def eval(self, expr: str):
        """Evaluate expression on remote."""
        from simplerpyc.client.proxy import RPCProxy, _raise_deserialized_error

        response = self.send({"type": "eval", "expr": expr})
        if response["type"] == "error":
            _raise_deserialized_error(response)
        return RPCProxy(path=f"eval({expr!r})", obj_id=response["obj_id"], connection=self)

    def execute(self, code: str):
        """Execute code on remote."""
        from simplerpyc.client.proxy import _raise_deserialized_error

        response = self.send({"type": "execute", "code": code})
        if response["type"] == "error":
            _raise_deserialized_error(response)

    def teleport(self, func):
        """Send function to remote and return proxy."""
        import dill

        from simplerpyc.client.proxy import RPCProxy, _raise_deserialized_error

        func_bytes = dill.dumps(func)
        response = self.send({"type": "teleport", "func_bytes": func_bytes, "name": func.__name__})
        if response["type"] == "error":
            _raise_deserialized_error(response)
        return RPCProxy(path=func.__name__, obj_id=response["obj_id"], connection=self)

    def patch_module(self, module_name: str):
        """Import remote module and patch sys.modules.

        This method is idempotent - calling it multiple times for the same module
        will not send additional RPC requests.
        """
        from simplerpyc.client.proxy import RPCProxy, _raise_deserialized_error

        # Return existing proxy if already patched
        if module_name in self._patched_modules:
            return sys.modules.get(module_name)

        # Store original module (or None if not imported)
        self._patched_modules[module_name] = sys.modules.get(module_name)

        response = self.send({"type": "import_module", "module": module_name})
        if response["type"] == "error":
            _raise_deserialized_error(response)

        proxy = RPCProxy(path=module_name, obj_id=response["obj_id"], connection=self)
        sys.modules[module_name] = proxy  # type: ignore
        return proxy

    def unpatch_module(self, module_name: str):
        """Restore original module in sys.modules."""
        if module_name in self._patched_modules:
            original = self._patched_modules.pop(module_name)
            if original is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original

    def unpatch_all(self):
        """Restore all patched modules to their original state."""
        for module_name in list(self._patched_modules.keys()):
            self.unpatch_module(module_name)

    def send(self, message: dict) -> dict:
        """Send message synchronously."""

        async def _send():
            await self.ws.send(serialize(message))
            return deserialize(await self.ws.recv())

        return self.loop.run_until_complete(_send())

    def disconnect(self):
        """Disconnect from server."""
        if self.ws:

            async def _disconnect():
                await self.ws.close()

            self.loop.run_until_complete(_disconnect())


def connect(host: str | None = None, port: int | None = None, token: str | None = None) -> Connection:
    """Connect to RPC server and return connection object.

    Args:
        host: Server host (defaults to SIMPLERPYC_HOST env var or "localhost")
        port: Server port (defaults to SIMPLERPYC_PORT env var or 8000)
        token: Authentication token (defaults to SIMPLERPYC_TOKEN env var)
    """
    if host is None:
        host = os.environ.get("SIMPLERPYC_HOST", "localhost")
    if port is None:
        port = int(os.environ.get("SIMPLERPYC_PORT", "8000"))

    conn = Connection()
    conn.connect(host, port, token)
    return conn
