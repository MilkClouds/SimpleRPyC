"""Module patching utilities."""

import sys


def patch_module(conn, module_name: str):
    """Patch a module in sys.modules with RPC proxy.

    Args:
        conn: Connection object
        module_name: Name of module to patch

    Returns:
        RPCProxy for the module
    """
    return conn.patch_module(module_name)


def unpatch_module(module_name: str):
    """Remove module patch from sys.modules."""
    sys.modules.pop(module_name, None)
