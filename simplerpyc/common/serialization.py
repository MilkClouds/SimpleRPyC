"""Serialization using msgpack with numpy support and dill for exceptions."""

import logging
import traceback

import dill
import msgpack
import msgpack_numpy as m

logger = logging.getLogger(__name__)

# Patch msgpack to support numpy arrays
m.patch()


def _convert_proxies(obj):
    """Convert RPCProxy objects and slices to serializable references."""
    # Avoid circular import
    from simplerpyc.client.proxy import RPCProxy

    if isinstance(obj, RPCProxy):
        return {"__rpc_proxy__": True, "obj_id": obj._rpc_obj_id}
    elif isinstance(obj, slice):
        return {"__slice__": True, "start": obj.start, "stop": obj.stop, "step": obj.step}
    elif isinstance(obj, dict):
        return {k: _convert_proxies(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_convert_proxies(item) for item in obj)
    return obj


def serialize(obj) -> bytes:
    """Serialize object to msgpack bytes, converting RPCProxy to references."""
    converted = _convert_proxies(obj)
    return msgpack.packb(converted, use_bin_type=True)


def deserialize(data: bytes):
    """Deserialize msgpack bytes to object."""
    return msgpack.unpackb(data, raw=False, strict_map_key=False)


def serialize_exception(exc: Exception) -> dict:
    """Serialize exception with dill."""
    try:
        exception_pickle = dill.dumps(exc)
    except Exception as e:
        logger.warning(f"Failed to serialize exception with dill: {e!r}. Falling back to basic exception info.")
        exception_pickle = None

    return {
        "exception_type": f"{exc.__class__.__module__}.{exc.__class__.__name__}",
        "exception_message": str(exc),
        "exception_pickle": exception_pickle,
        "traceback": traceback.format_exc(),
    }


def deserialize_exception(exc_data: dict) -> tuple[Exception, Exception | None]:
    """Deserialize exception. Returns (RemoteException, original_exception)."""
    from simplerpyc.client.proxy import RemoteException

    exc_type = exc_data.get("exception_type", "Exception")
    exc_message = exc_data.get("exception_message", "Unknown error")
    exc_traceback = exc_data.get("traceback")

    remote_exc = RemoteException(f"{exc_type}: {exc_message}", traceback=exc_traceback, exception_type=exc_type)

    if exc_data.get("exception_pickle"):
        try:
            original_exc = dill.loads(exc_data["exception_pickle"])
            return (remote_exc, original_exc)
        except Exception as e:
            logger.warning(
                f"Failed to deserialize exception with dill: {e!r}. RemoteException will be raised without a cause."
            )

    return (remote_exc, None)
