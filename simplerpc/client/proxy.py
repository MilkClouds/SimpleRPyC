"""RPC proxy objects."""

from typing import Any

from simplerpc.client.connection import get_connection


class RPCProxy:
    """Proxy for remote objects. All operations are lazy until materialized."""

    def __init__(self, path: str = "", obj_id: int | None = None):
        object.__setattr__(self, "_rpc_path", path)
        object.__setattr__(self, "_rpc_obj_id", obj_id)
        object.__setattr__(self, "_rpc_connection", get_connection())

    def __getattr__(self, name: str):
        """Attribute access returns new proxy with server-side object."""
        # Handle special attributes locally to avoid unnecessary RPC calls
        # These are commonly accessed by Python internals and libraries for introspection
        if name in ("__spec__", "__path__", "__file__", "__loader__", "__package__"):
            # Return None for module-related special attributes
            # This prevents unnecessary RPC calls during module introspection
            raise AttributeError(f"'{self._rpc_path}' has no attribute '{name}'")

        new_path = f"{self._rpc_path}.{name}" if self._rpc_path else name
        response = self._rpc_connection.send(
            {"type": "getattr", "path": self._rpc_path, "obj_id": self._rpc_obj_id, "attr": name}
        )
        if response["type"] == "error":
            raise RemoteException(response["error"], response.get("traceback"))
        return RPCProxy(path=new_path, obj_id=response["obj_id"])

    def __call__(self, *args, **kwargs):
        """Function/method call returns new proxy with result."""
        response = self._rpc_connection.send(
            {"type": "call", "path": self._rpc_path, "obj_id": self._rpc_obj_id, "args": args, "kwargs": kwargs}
        )
        if response["type"] == "error":
            raise RemoteException(response["error"], response.get("traceback"))
        return RPCProxy(path=f"{self._rpc_path}()", obj_id=response["obj_id"])

    def __getitem__(self, key):
        """Indexing returns new proxy."""
        response = self._rpc_connection.send({"type": "getitem", "obj_id": self._rpc_obj_id, "key": key})
        if response["type"] == "error":
            raise RemoteException(response["error"], response.get("traceback"))
        return RPCProxy(path=f"{self._rpc_path}[{key}]", obj_id=response["obj_id"])

    def __repr__(self):
        """Debug representation."""
        return f"<RPCProxy: {self._rpc_path} (id={self._rpc_obj_id})>"


class RemoteException(Exception):
    """Exception raised on the server side."""

    def __init__(self, message: str, traceback: str | None = None):
        super().__init__(message)
        self.remote_traceback = traceback

    def __str__(self):
        if self.remote_traceback:
            return f"{super().__str__()}\n\nRemote traceback:\n{self.remote_traceback}"
        return super().__str__()


def materialize(obj: Any) -> Any:
    """Convert RPCProxy to actual value by fetching from server."""
    if not isinstance(obj, RPCProxy):
        return obj
    response = obj._rpc_connection.send({"type": "materialize", "obj_id": obj._rpc_obj_id})
    if response["type"] == "error":
        raise RemoteException(response["error"], response.get("traceback"))
    return response["value"]


def is_proxy(obj: Any) -> bool:
    """Check if object is an RPCProxy."""
    return isinstance(obj, RPCProxy)
