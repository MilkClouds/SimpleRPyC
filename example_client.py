"""Example client demonstrating simplerpc usage."""

import atexit

import simplerpc
from simplerpc import materialize

# Connect to server (token auto-detected from SIMPLERPC_TOKEN env var)
conn = simplerpc.connect("localhost", 8000)
atexit.register(conn.disconnect)

# Patch modules - client doesn't need them installed locally
simplerpc.patch_module(conn, "os")
simplerpc.patch_module(conn, "sys")
simplerpc.patch_module(conn, "json")

# Now we can import and use them as if they were local
import json as remote_json  # noqa: E402
import os as remote_os  # noqa: E402
import sys as remote_sys  # noqa: E402

print("=== SimpleRPC Example ===\n")

# Example 1: Simple function call
print("1. Calling os.getcwd()...")
cwd_proxy = remote_os.getcwd()
print(f"   Result is proxy: {simplerpc.is_proxy(cwd_proxy)}")
cwd = materialize(cwd_proxy)
print(f"   Current directory: {cwd}\n")

# Example 2: Attribute access and indexing
print("2. Accessing sys.path...")
path_proxy = remote_sys.path
print(f"   sys.path is proxy: {simplerpc.is_proxy(path_proxy)}")
first_item = materialize(path_proxy[0])
print(f"   First item: {first_item}\n")

# Example 3: Complex operations
print("3. JSON operations...")
data = {"name": "SimpleRPC", "version": "0.1.0", "features": ["websocket", "msgpack", "lazy"]}
json_str_proxy = remote_json.dumps(data, indent=2)
json_str = materialize(json_str_proxy)
print(f"   Serialized JSON:\n{json_str}\n")

# Example 4: Chained operations
print("4. Chained operations...")
env_proxy = remote_os.environ
home_proxy = env_proxy.get("HOME", "not set")
home = materialize(home_proxy)
print(f"   HOME environment variable: {home}\n")

# Example 5: List operations
print("5. List operations...")
path_list = materialize(remote_sys.path)
print(f"   sys.path has {len(path_list)} entries")
print(f"   First 3: {path_list[:3]}\n")

print("=== All examples completed successfully! ===")
