"""Serialization using msgpack with numpy support."""

import msgpack
import msgpack_numpy as m

# Patch msgpack to support numpy arrays
m.patch()


def _convert_proxies(obj):
    """Convert RPCProxy objects and slices to serializable references."""
    # Avoid circular import
    from simplerpc.client.proxy import RPCProxy

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
