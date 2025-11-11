"""Module patching."""

import sys

from simplerpc.client.connection import get_connection
from simplerpc.client.proxy import RPCProxy, _raise_deserialized_error

# Track original modules
_original_modules = {}


def patch_module(module_name: str) -> RPCProxy:
    """Patch a module in sys.modules with RPC proxy."""
    if module_name in _original_modules:
        return sys.modules[module_name]  # type: ignore

    # Request server to import module
    response = get_connection().send({"type": "import_module", "module": module_name})
    if response["type"] == "error":
        _raise_deserialized_error(response)

    # Create proxy for the module
    proxy = RPCProxy(path=module_name, obj_id=response["obj_id"])

    # Save original module if it exists
    _original_modules[module_name] = sys.modules.get(module_name)

    # Patch sys.modules
    sys.modules[module_name] = proxy  # type: ignore

    return proxy


def unpatch_all():
    """Remove all module patches."""
    for module_name, original in _original_modules.items():
        if original is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original
    _original_modules.clear()
