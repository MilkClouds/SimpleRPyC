# SimpleRPC

Simple Remote Procedure Call over WebSocket with lazy evaluation and explicit materialization.

## Features

- **WebSocket-based RPC**: Fast, bidirectional communication
- **Lazy Evaluation**: Everything returns proxies by default
- **Explicit Materialization**: User controls when to fetch data from server
- **Token Authentication**: Secure connection with random tokens
- **msgpack Serialization**: Efficient binary serialization with numpy support
- **Module Patching**: Use remote modules as if they were local

## Installation

```bash
uv sync
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

```python
import simplerpc
from simplerpc import materialize

# Connect to server (token auto-detected from SIMPLERPC_TOKEN env var)
# Or pass explicitly: simplerpc.connect("localhost", 8000, token="...")
simplerpc.connect("localhost", 8000)

# Patch a module (client doesn't need it installed)
simplerpc.patch_module("os")

# Import and use as normal
import os as remote_os

# Everything returns proxies by default
cwd_proxy = remote_os.getcwd()
print(simplerpc.is_proxy(cwd_proxy))  # True

# Explicitly materialize when you need the actual value
cwd = materialize(cwd_proxy)
print(cwd)  # Actual string value

# Disconnect
simplerpc.disconnect()
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

### Client Functions

- `connect(host, port, token)` - Connect to RPC server
- `disconnect()` - Disconnect from server
- `patch_module(module_name)` - Patch a module with RPC proxy
- `materialize(obj)` - Convert proxy to actual value
- `is_proxy(obj)` - Check if object is a proxy

### Environment Variables

- `SIMPLERPC_TOKEN` - Authentication token (auto-detected by `connect()` if not provided)

### Server

```bash
python -m simplerpc.server [--host HOST] [--port PORT]
```

## Examples

See `example_client.py` for comprehensive examples.

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

## License

MIT
