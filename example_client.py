"""Example client demonstrating simplerpyc usage."""

import atexit

import simplerpyc
from simplerpyc import materialize

# ============================================================================
# Setup: Connect to server and patch modules
# ============================================================================

# Connect to server (token auto-detected from SIMPLERPYC_TOKEN env var)
conn = simplerpyc.connect("localhost", 8000)
atexit.register(conn.disconnect)

# Patch modules - client doesn't need them installed locally
simplerpyc.patch_module(conn, "os")
simplerpyc.patch_module(conn, "numpy")

# Import patched modules as if they were local
import os as remote_os  # noqa: E402

import numpy as remote_np  # noqa: E402

# ============================================================================
# Example 1: Understanding Proxies
# ============================================================================

# Everything returns a proxy by default (lazy evaluation)
cwd_proxy = remote_os.getcwd()
print(f"{simplerpyc.is_proxy(cwd_proxy)=}")

# Materialize to get actual value
cwd = materialize(cwd_proxy)
print(f"{simplerpyc.is_proxy(cwd)=}")
print(f"{cwd=}")


# ============================================================================
# Example 2: NumPy Array Operations (1D and 2D)
# ============================================================================

# Create 1D array
arr_proxy = remote_np.array([1, 2, 3, 4, 5])
arr_local = materialize(arr_proxy)
print(f"\n{arr_local=}")

# Option 1: Compute mean on remote proxy
mean_remote = materialize(remote_np.mean(arr_proxy))
print(f"{mean_remote=}")

# Option 2: Compute mean on materialized local array
mean_local = materialize(remote_np.mean(arr_local))
print(f"{mean_local=}")

# Create and manipulate 2D array
matrix = materialize(remote_np.arange(12).reshape(3, 4))
print(f"\n{matrix=}")


# ============================================================================
# Example 3: Remote Code Execution (eval & execute)
# ============================================================================

# Execute code remotely (no return value)
conn.execute("import random; random.seed(42)")

# Evaluate expression remotely (returns proxy)
random_num = materialize(conn.eval("random.randint(1, 100)"))
print(f"\n{random_num=}")


# ============================================================================
# Example 4: Nested Data Structures with NumPy
# ============================================================================

# Create nested structure remotely using eval
nested = materialize(
    conn.eval("""
{
    'metadata': {'name': 'experiment_1', 'version': 1.0},
    'arrays': [numpy.array([1.0, 2.0, 3.0]), numpy.array([[4, 5], [6, 7]])],
    'coordinates': (numpy.array([10, 20, 30]), numpy.array([40, 50, 60])),
    'scalar': 42,
}
""")
)

print(f"\n{nested=}")


print("\n=== All examples completed successfully! ===")
