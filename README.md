# SimpleRPyC

[![CI](https://github.com/milkclouds/simplerpyc/actions/workflows/ci.yml/badge.svg)](https://github.com/milkclouds/simplerpyc/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/milkclouds/simplerpyc/branch/main/graph/badge.svg)](https://codecov.io/gh/milkclouds/simplerpyc)
[![pypi](https://img.shields.io/pypi/v/simplerpyc.svg)](https://pypi.python.org/pypi/simplerpyc)
[![Python Versions](https://img.shields.io/pypi/pyversions/simplerpyc.svg)](https://pypi.org/project/simplerpyc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

SimpleRPyC (pronounced *simple-are-pie-see*), short for **Simple Remote Python Call**, is a WebSocket-based RPC library for Python. Inspired by [RPyC](https://github.com/tomerfiliba-org/rpyc), it uses transparent [proxy objects](https://en.wikipedia.org/wiki/Proxy_pattern) to let you interact with remote Python objects as if they were local—leveraging Python's dynamic nature to bridge processes and machines seamlessly. Additionally, SimpleRPyC provides convenient module patching that allows you to use existing code with minimal changes.

Unlike traditional RPC libraries that use custom protocols, SimpleRPyC is built on **WebSocket** (standard, debuggable protocol) and **[msgpack](https://msgpack.org/)** (efficient binary serialization). This choice enables seamless numpy array transfers between different numpy versions (1.x ↔ 2.x), which is critical for running modern ML code alongside legacy environments.

## Why SimpleRPyC?

**Problem**: Running code with incompatible dependencies in the same process.

For example, robotics simulation environments like [SimplerEnv](https://github.com/simpler-env/SimplerEnv) (a robot manipulation benchmark) require `numpy<2.0`, but modern RL policies require `numpy>=2.0`. You can't install both in the same environment.

**Solution**: Run them in separate processes and communicate via RPC.

## Why Not Alternatives?

| Feature | SimpleRPyC | [RPyC](https://github.com/tomerfiliba-org/rpyc) | [Pyro5](https://github.com/irmen/Pyro5) | [zero](https://github.com/Ananto30/zero) |
|---------|-----------|------|-------|------|
| Transport | WebSocket | TCP + custom protocol | TCP + custom protocol | ZMQ |
| Serialization | [msgpack](https://msgpack.org/) | brine (custom) | [serpent](https://github.com/irmen/Serpent) | [msgspec](https://jcristharif.com/msgspec/) |
| NumPy support | ✅ Built-in | ✅ Yes | ❌ [No](https://github.com/irmen/Pyro5/blob/6bfe2e523f93d205ea7a97ec9e1e01d7437821fd/docs/source/tipstricks.rst?plain=1#L357-L390) | ❌ No |
| NumPy 1.x ↔ 2.x | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Multiple args | ✅ `f(a,b,c)` | ✅ Yes | ✅ Yes | ❌ No |
| Module patching | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| Proxy objects | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |

**[RPyC](https://github.com/tomerfiliba-org/rpyc)**: Uses TCP with custom framing/channel layer and "brine" serialization. Supports numpy arrays but breaks when transferring between numpy 1.x and 2.x due to pickle format changes. Custom serialization format makes it hard to add additional features.

**[Pyro5](https://github.com/irmen/Pyro5)**: Uses TCP with custom wire protocol and serpent serializer. [No built-in numpy support](https://github.com/irmen/Pyro5/blob/6bfe2e523f93d205ea7a97ec9e1e01d7437821fd/docs/source/tipstricks.rst?plain=1#L357-L390) - requires manual workarounds that don't handle numpy 1.x ↔ 2.x transfers.

**[zero](https://github.com/Ananto30/zero)**: Promising msgspec+ZMQ stack, but doesn't support multiple arguments (`remote_fn(a, b, c)` fails) or proxy objects.

<!-- TODO: pydantic support, add content for dataclasses-like types(already supported since we use msgpack) -->
<!-- TODO: more practical demo, e.g. remote RL env demo -->

## Features

- **WebSocket Transport**: Standard protocol, easy to debug, works through firewalls
- **[msgpack](https://msgpack.org/) + NumPy**: Efficient binary serialization with cross-version numpy compatibility via [msgpack-numpy](https://github.com/lebedov/msgpack-numpy)
- **Transparent Proxies**: Remote objects behave like local objects
- **Explicit Materialization**: Control when to transfer data from server (`materialize()`)
- **Flexible API**: Module patching (`import os`) or explicit access (`conn.modules.os`)
- **Function Teleportation**: Send local functions to remote server with `conn.teleport()` using [dill](https://github.com/uqfoundation/dill)
- **Remote Execution**: Run arbitrary code on server with `conn.eval()` and `conn.execute()`

## ⚠️ Security Warning

**SimpleRPyC uses unencrypted WebSocket connections (`ws://`).** The authentication token and all data are transmitted in plaintext, making them vulnerable to network sniffing and man-in-the-middle attacks.

**Use SimpleRPyC only in trusted, private networks** (e.g., localhost, private LANs, VPNs). **DO NOT expose SimpleRPyC servers to the public internet** or use it over untrusted networks.

For production use over untrusted networks, consider:
- Running SimpleRPyC only on `localhost` and using SSH tunneling for remote access
- Deploying within a private network or VPN
- Adding TLS/SSL encryption layer (e.g., reverse proxy with nginx/caddy)

## Installation

```bash
pip install simplerpyc
```

## Quick Start

### 1. Start the Server

```bash
python -m simplerpyc.server
```

The server will print a token. Set it as environment variable:
```bash
export SIMPLERPYC_TOKEN='<TOKEN_FROM_SERVER>'
```

### 2. Use the Client

SimpleRPyC provides two API styles - choose what fits your use case:

#### Style 1: Module Patching (Import-like)

```python
import simplerpyc
from simplerpyc import materialize

# Connect to server
conn = simplerpyc.connect("localhost", 8000)

# Patch modules to use remote versions
simplerpyc.patch_module(conn, "os")
simplerpyc.patch_module(conn, "numpy")

# Import and use as if they were local
import os
import numpy as np

cwd = materialize(os.getcwd())
arr = materialize(np.array([1, 2, 3]))

conn.disconnect()
```

#### Style 2: Explicit Remote Access

```python
from simplerpyc import connect, materialize

# Connect to server
conn = connect("localhost", 8000)

# Access remote modules explicitly
remote_os = conn.modules.os
remote_np = conn.modules.numpy

# Everything returns proxies by default
cwd = materialize(remote_os.getcwd())
arr = materialize(remote_np.array([1, 2, 3]))

conn.disconnect()
```

## Examples

See [`example_client.py`](example_client.py) for comprehensive examples including:
- Understanding proxies and materialization
- NumPy array operations (1D and 2D)
- Remote code execution (`eval` and `execute`)
- Nested data structures with NumPy arrays

## Core Concepts

### Transparent Proxies

All remote operations return `RPCProxy` objects that behave like the actual objects:

```python
# Remote function call returns proxy
arr_proxy = remote_np.array([1, 2, 3])  # RPCProxy, not actual array

# Proxy supports attribute access, method calls, indexing
mean_proxy = arr_proxy.mean()           # RPCProxy
item_proxy = arr_proxy[0]               # RPCProxy

# Chain operations without network round-trips
result_proxy = remote_np.array([1, 2, 3]).reshape(3, 1).mean()  # Still proxy
```

### Explicit Materialization

Use `materialize()` to transfer data from server to client:

```python
# Materialize when you need actual values
arr = materialize(arr_proxy)            # numpy array
mean = materialize(mean_proxy)          # float
item = materialize(item_proxy)          # int

# Materialize complex structures
env = simpler_env.make('...')           # RPCProxy
obs, reward, done, truncated, info = materialize(env.step(action))  # actual values
```

**Design principle**: Minimize network transfers by keeping operations on server until results are needed.

## API Reference

### Connection

```python
from simplerpyc import connect

conn = connect(host="localhost", port=8000, token=None)
# Token auto-detected from SIMPLERPYC_TOKEN env var if not provided
```

### Basic API

**Module Patching:**
```python
import simplerpyc

simplerpyc.patch_module(conn, "os")      # Patch sys.modules
import os                                # Now uses remote version
```

**Namespace Access:**
```python
remote_os = conn.modules.os             # Access remote module
remote_len = conn.builtins.len          # Access remote builtin
```

**Utility Functions:**
```python
from simplerpyc import materialize, is_proxy

value = materialize(proxy)              # Convert proxy to actual value
is_remote = is_proxy(obj)               # Check if object is a proxy
```

### Advanced Features

**Remote Code Execution:**
```python
# Evaluate expression
result = materialize(conn.eval("2 + 3"))  # 5

# Execute code (no return value)
conn.execute("x = 42")
x = materialize(conn.eval("x"))           # 42
```

**Function Teleportation:**
```python
# Send local function to remote
def square(x):
    return x ** 2

remote_square = conn.teleport(square)
result = materialize(remote_square(5))    # 25
```

**Connection Management:**
```python
conn.disconnect()                         # Close connection
```

## Server

```bash
python -m simplerpyc.server [--host HOST] [--port PORT]
```

The server will print a token. Set it as environment variable:
```bash
export SIMPLERPYC_TOKEN='<TOKEN_FROM_SERVER>'
```

## Design Decisions

### Why WebSocket?

- **Standard protocol**: Works with existing infrastructure (proxies, load balancers)
- **Bidirectional**: Server can push data to client (future feature)
- **Debuggable**: Easy to inspect with browser dev tools or Wireshark
- **Firewall-friendly**: Uses standard HTTP ports

### Why [msgpack](https://msgpack.org/) + [msgpack-numpy](https://github.com/lebedov/msgpack-numpy)?

- **Efficient**: Binary format, smaller than JSON
- **NumPy support**: Native serialization for numpy arrays
- **Cross-version**: Works between numpy 1.x and 2.x (unlike pickle)
- **Language-agnostic**: Can implement clients in other languages

### Why Proxy-based Design?

Inspired by [RPyC](https://github.com/tomerfiliba-org/rpyc)'s elegant proxy pattern:

- **Transparent**: Remote objects behave like local objects
- **Efficient**: Chain operations on server without network round-trips
- **Explicit control**: User decides when to transfer data with `materialize()`

Unlike RPyC, we use WebSocket transport and msgpack serialization for better numpy compatibility.

## Architecture

```
simplerpyc/
├── client/
│   ├── connection.py    # WebSocket connection management
│   ├── proxy.py         # Minimal RPCProxy implementation
│   └── patcher.py       # sys.modules patching
├── server/
│   ├── server.py        # WebSocket server
│   └── executor.py      # Per-client execution context
└── common/
    └── serialization.py # msgpack with numpy support
```

## Requirements

**Python 3.10+** is required. Python 3.9 is not supported due to:
- WebSocket concurrency issues with nested asyncio event loops in synchronous RPC context
- `nest_asyncio` compatibility issues causing `ConcurrencyError` in websockets

## License

MIT
