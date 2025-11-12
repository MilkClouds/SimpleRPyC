"""SimpleRPyC - Simple Remote Python Call over WebSocket."""

# Version is managed by hatch-vcs from Git tags
try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    # Fallback for editable installs without build
    try:
        from importlib.metadata import version

        __version__ = version("simplerpyc")
    except Exception:
        __version__ = "0.0.0.dev0"


from simplerpyc.client.connection import Connection, connect
from simplerpyc.client.patcher import patch_module
from simplerpyc.client.proxy import is_proxy, materialize

__all__ = [
    "connect",
    "patch_module",
    "Connection",
    "materialize",
    "is_proxy",
]
