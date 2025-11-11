"""RPC proxy objects using unittest.mock."""

from typing import Any
from unittest.mock import MagicMock

from simplerpc.client.connection import get_connection


class RPCProxy(MagicMock):
    """Proxy for remote objects. All operations are lazy until materialized."""

    def __init__(self, path: str = "", obj_id: int | None = None, **kwargs):
        super().__init__(**kwargs)
        self._rpc_path = path
        self._rpc_obj_id = obj_id
        self._rpc_connection = get_connection()

    def _get_child_mock(self, **kw):
        """Create child mock as RPCProxy."""
        name = kw.get("name", "")
        new_path = f"{self._rpc_path}.{name}" if self._rpc_path else name
        return RPCProxy(path=new_path, obj_id=self._rpc_obj_id, **kw)

    def __getattr__(self, name: str):
        """Attribute access returns new proxy with server-side object."""
        if name.startswith("_"):
            return super().__getattr__(name)

        new_path = f"{self._rpc_path}.{name}" if self._rpc_path else name

        # Send getattr request to server to get actual object ID
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

        # Return proxy for the result
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
        msg = super().__str__()
        if self.remote_traceback:
            return f"{msg}\n\nRemote traceback:\n{self.remote_traceback}"
        return msg


def materialize(obj: Any) -> Any:
    """
    Convert RPCProxy to actual value by fetching from server.
    Non-proxy objects are returned as-is.

    Args:
        obj: RPCProxy or regular object

    Returns:
        Actual value from server (for proxies) or original object

    Examples:
        >>> result = env.step(action)  # RPCProxy
        >>> obs, reward, done, truncated, info = materialize(result)
        >>> obs = materialize(result[0])  # Partial materialization
    """
    if not isinstance(obj, RPCProxy):
        return obj

    response = obj._rpc_connection.send({"type": "materialize", "obj_id": obj._rpc_obj_id})

    if response["type"] == "error":
        raise RemoteException(response["error"], response.get("traceback"))

    return response["value"]


def is_proxy(obj: Any) -> bool:
    """Check if object is an RPCProxy."""
    return isinstance(obj, RPCProxy)
