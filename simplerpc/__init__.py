"""SimpleRPC - Simple Remote Procedure Call over WebSocket."""

from simplerpc.client.connection import connect, disconnect
from simplerpc.client.patcher import patch, patch_module
from simplerpc.client.proxy import is_proxy, materialize

__version__ = "0.1.0"

__all__ = [
    "connect",
    "disconnect",
    "patch",
    "patch_module",
    "materialize",
    "is_proxy",
]
