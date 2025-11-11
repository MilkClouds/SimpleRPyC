"""SimpleRPC - Simple Remote Procedure Call over WebSocket."""
from simplerpc.client.connection import connect, disconnect
from simplerpc.client.patcher import patch_module
from simplerpc.client.proxy import materialize, is_proxy

__version__ = "0.1.0"

__all__ = [
    'connect',
    'disconnect',
    'patch_module',
    'materialize',
    'is_proxy',
]

