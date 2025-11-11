"""Serialization using msgpack with numpy support."""

import msgpack
import msgpack_numpy as m

# Patch msgpack to support numpy arrays
m.patch()


def serialize(obj) -> bytes:
    """Serialize object to msgpack bytes."""
    return msgpack.packb(obj, use_bin_type=True)


def deserialize(data: bytes):
    """Deserialize msgpack bytes to object."""
    return msgpack.unpackb(data, raw=False, strict_map_key=False)
