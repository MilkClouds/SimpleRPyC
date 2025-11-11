"""Module patching using unittest.mock."""

import sys

from simplerpc.client.connection import get_connection
from simplerpc.client.proxy import RPCProxy


class ModulePatcher:
    """Patches sys.modules to inject RPC proxies."""

    def __init__(self):
        self.original_modules = {}

    def patch_module(self, module_name: str) -> RPCProxy:
        """
        Patch a module in sys.modules with RPC proxy.

        Args:
            module_name: Name of module to patch (e.g., 'simpler_env')

        Returns:
            RPCProxy for the module
        """
        if module_name in self.original_modules:
            return sys.modules[module_name]

        # Request server to import module
        conn = get_connection()
        response = conn.send({"type": "import_module", "module": module_name})

        if response["type"] == "error":
            from simplerpc.client.proxy import RemoteException

            raise RemoteException(response["error"], response.get("traceback"))

        # Create proxy for the module
        proxy = RPCProxy(path=module_name, obj_id=response["obj_id"])

        # Save original module if it exists
        if module_name in sys.modules:
            self.original_modules[module_name] = sys.modules[module_name]
        else:
            self.original_modules[module_name] = None

        # Directly patch sys.modules
        sys.modules[module_name] = proxy

        return proxy

    def unpatch_all(self):
        """Remove all module patches."""
        for module_name, original in self.original_modules.items():
            if original is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original
        self.original_modules.clear()


# Global patcher instance
_patcher = None


def get_patcher() -> ModulePatcher:
    """Get global patcher instance."""
    global _patcher
    if _patcher is None:
        _patcher = ModulePatcher()
    return _patcher


def patch_module(module_name: str) -> RPCProxy:
    """Patch a module with RPC proxy."""
    return get_patcher().patch_module(module_name)


def unpatch_all():
    """Remove all module patches."""
    global _patcher
    if _patcher:
        _patcher.unpatch_all()
