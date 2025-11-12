"""RPC proxy objects."""

from typing import Any


def _raise_deserialized_error(response: dict):
    """Deserialize and raise error."""
    from simplerpyc.common.serialization import deserialize_exception

    exc, cause = deserialize_exception(response)
    if cause:
        raise exc from cause
    raise exc


class RPCProxy:
    """Proxy for remote objects. All operations are lazy until materialized."""

    def __init__(self, path: str = "", obj_id: int | None = None, connection=None):
        object.__setattr__(self, "_rpc_path", path)
        object.__setattr__(self, "_rpc_obj_id", obj_id)
        object.__setattr__(self, "_rpc_connection", connection)

    def __getattr__(self, name: str):
        """Attribute access returns new proxy with server-side object."""
        if name in ("__spec__", "__path__", "__file__", "__loader__", "__package__"):
            raise AttributeError(f"'{self._rpc_path}' has no attribute '{name}'")

        new_path = f"{self._rpc_path}.{name}" if self._rpc_path else name
        response = self._rpc_connection.send(
            {"type": "getattr", "path": self._rpc_path, "obj_id": self._rpc_obj_id, "attr": name}
        )
        if response["type"] == "error":
            _raise_deserialized_error(response)
        return RPCProxy(path=new_path, obj_id=response["obj_id"], connection=self._rpc_connection)

    def __call__(self, *args, **kwargs):
        """Function/method call returns new proxy with result."""
        response = self._rpc_connection.send(
            {"type": "call", "path": self._rpc_path, "obj_id": self._rpc_obj_id, "args": args, "kwargs": kwargs}
        )
        if response["type"] == "error":
            _raise_deserialized_error(response)
        return RPCProxy(path=f"{self._rpc_path}()", obj_id=response["obj_id"], connection=self._rpc_connection)

    def __getitem__(self, key):
        """Indexing returns new proxy."""
        response = self._rpc_connection.send({"type": "getitem", "obj_id": self._rpc_obj_id, "key": key})
        if response["type"] == "error":
            _raise_deserialized_error(response)
        return RPCProxy(path=f"{self._rpc_path}[{key}]", obj_id=response["obj_id"], connection=self._rpc_connection)

    def __repr__(self):
        """Debug representation."""
        return f"<RPCProxy: {self._rpc_path} (id={self._rpc_obj_id})>"


class RemoteException(Exception):
    """Exception from remote server."""

    def __init__(self, message: str, traceback: str | None = None, exception_type: str | None = None):
        super().__init__(message)
        self.remote_traceback = traceback
        self.exception_type = exception_type

    def __str__(self):
        if self.remote_traceback:
            return f"{super().__str__()}\n\nRemote traceback:\n{self.remote_traceback}"
        return super().__str__()

    def __repr__(self):
        if self.exception_type:
            return f"RemoteException({self.exception_type}: {super().__str__()})"
        return f"RemoteException({super().__str__()})"


def materialize(obj: Any) -> Any:
    """Convert RPCProxy to actual value by fetching from server."""
    if not isinstance(obj, RPCProxy):
        return obj
    response = obj._rpc_connection.send({"type": "materialize", "obj_id": obj._rpc_obj_id})
    if response["type"] == "error":
        _raise_deserialized_error(response)
    return response["value"]


def is_proxy(obj: Any) -> bool:
    """Check if object is an RPCProxy."""
    return isinstance(obj, RPCProxy)
