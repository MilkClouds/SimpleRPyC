"""SimpleRPC - Simple Remote Procedure Call over WebSocket."""

# Version is managed by hatch-vcs from Git tags
try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    # Fallback for editable installs without build
    try:
        from importlib.metadata import version

        __version__ = version("simplerpc")
    except Exception:
        __version__ = "0.0.0.dev0"


from simplerpc.client.connection import Connection, connect
from simplerpc.client.patcher import patch_module
from simplerpc.client.proxy import is_proxy, materialize

__version__ = "0.1.0"

__all__ = [
    "connect",
    "patch_module",
    "Connection",
    "materialize",
    "is_proxy",
]
