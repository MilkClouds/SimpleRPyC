# SimpleRPC

[![CI](https://github.com/milkclouds/simplerpc/actions/workflows/ci.yml/badge.svg)](https://github.com/milkclouds/simplerpc/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/milkclouds/simplerpc/branch/main/graph/badge.svg)](https://codecov.io/gh/milkclouds/simplerpc)
[![pypi](https://img.shields.io/pypi/v/simplerpc.svg)](https://pypi.python.org/pypi/simplerpc)
[![Python Versions](https://img.shields.io/pypi/pyversions/simplerpc.svg)](https://pypi.org/project/simplerpc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Simple Remote Procedure Call over WebSocket with lazy evaluation and explicit materialization.

- **Where is it used?**: I wrote this library to separate RL environment execution from RL policy. e.g. [SimplerEnv](https://github.com/simpler-env/SimplerEnv) requires `numpy<2.0` but common RL policies nowaday requires `numpy>=2.0`. This library allows us to run environment in separate process with `numpy<2.0` while keeping policy in main process with `numpy>=2.0`.
- **Why you should use it instead of alternatives?**: Some similar projects, [RPyC](https://github.com/tomerfiliba-org/rpyc) and [Pyro5](https://github.com/irmen/Pyro5), requires you to write your code in a way that it can be executed remotely. But they adopt custom serde logic, does not support numpy array transport between `numpy<2.0` and `numpy>=2.0`. [zero](https://github.com/Ananto30/zero) is one promising candidate with [msgspec](https://jcristharif.com/msgspec/) serde and [zmq](https://zeromq.org/) transport. However they does not even support multiple argument(e.g. `remote_fn(a,b,c)`) for remote function call.

<!-- TODO: feature table with comparison with alternatives. -->

## Features

- **WebSocket-based RPC**: Fast, bidirectional communication
- **Lazy Evaluation**: Everything returns proxies by default
- **Explicit Materialization**: User controls when to fetch data from server
- **Token Authentication**: Secure connection with random tokens
- **msgpack Serialization**: Efficient binary serialization with numpy support
- **Flexible API**: Module patching for import-style usage, or namespace access for explicit remote calls
- **Advanced Features**: Remote code execution (`eval`, `execute`), function teleportation

## Installation

```bash
pip install simplerpc
```

## Quick Start

### 1. Start the Server

```bash
python -m simplerpc.server
```

The server will print a token. Set it as environment variable:
```bash
export SIMPLERPC_TOKEN='<TOKEN_FROM_SERVER>'
```

### 2. Use the Client

SimpleRPC provides two API styles - choose what fits your use case:

#### Style 1: Module Patching (Import-like)

```python
import simplerpc
from simplerpc import materialize

# Connect to server
conn = simplerpc.connect("localhost", 8000)

# Patch modules to use remote versions
simplerpc.patch_module(conn, "os")
simplerpc.patch_module(conn, "numpy")

# Import and use as if they were local
import os
import numpy as np

cwd = materialize(os.getcwd())
arr = materialize(np.array([1, 2, 3]))

conn.disconnect()
```

#### Style 2: Explicit Remote Access

```python
from simplerpc import connect, materialize

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

## Core Concepts

### Proxies vs Materialization

**Problem**: When should RPC return a proxy vs actual value?

**Solution**: Everything returns `RPCProxy` by default (lazy evaluation). User explicitly calls `materialize(obj)` when actual value is needed.

```python
# Everything is proxy by default
env = simpler_env.make('...')  # RPCProxy
result = env.step(action)       # RPCProxy

# Explicit materialization when needed
obs, reward, done, truncated, info = materialize(result)  # actual values
instruction = materialize(env.get_language_instruction())  # str

# Partial materialization also possible
obs = materialize(result[0])    # only observation
reward = materialize(result[1]) # only reward
```

**Key principle**: User decides when to fetch data from server, not the library.

## API Reference

### Connection

```python
from simplerpc import connect

conn = connect(host="localhost", port=8000, token=None)
# Token auto-detected from SIMPLERPC_TOKEN env var if not provided
```

### Basic API

**Module Patching:**
```python
import simplerpc

simplerpc.patch_module(conn, "os")      # Patch sys.modules
import os                                # Now uses remote version
```

**Namespace Access:**
```python
remote_os = conn.modules.os             # Access remote module
remote_len = conn.builtins.len          # Access remote builtin
```

**Utility Functions:**
```python
from simplerpc import materialize, is_proxy

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
python -m simplerpc.server [--host HOST] [--port PORT]
```

The server will print a token. Set it as environment variable:
```bash
export SIMPLERPC_TOKEN='<TOKEN_FROM_SERVER>'
```

## Examples

See `example_client.py` for comprehensive examples.

## Design Notes

SimpleRPC draws inspiration from [RPyC](https://github.com/tomerfiliba-org/rpyc)'s elegant design patterns while focusing on WebSocket transport and numpy compatibility. We adopt proven patterns from established RPC libraries and adapt them for modern use cases.

## Architecture

```
simplerpc/
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
