I want to implement simple RPC client/server with websocket.

## desired design

### Authentication
- server generates a random token on startup and prints it to console
- client must provide this token during initial connection handshake
- server rejects connections with invalid/missing tokens
- token is passed as query parameter: `ws://localhost:8000?token=<TOKEN>`

### Core Design

- server and client communicate via websocket.
- server is stateful. manages session per client. Creates dedicated process per client when client connects.
- for serde before/after client/server communication, use `msgpack`. install both `msgpack` and `msgpack-numpy` to ensure numpy serde work.  you need following patch.
```py
import msgpack
import msgpack_numpy as m
m.patch()
```
- on client, for every time "patched remote module" must be called, request command to server. on server, execute commands from client directly with `exec`. manages `globals()` per client.

server side:
`python -m simplerpyc.server`

client side:
```diff
+ import simplerpyc, atexit
+ # token can be given as environmental variable or passed directly
+ simplerpyc.connect("localhost", 8000, token="<TOKEN_FROM_SERVER>")
+ # client does not have simpler_env installed, but it can access it via RPC
+ patcher = simplerpyc.patch_module("simpler_env")
+ # now simpler_env provides magic proxy
+ atexit.register(simplerpyc.disconnect)

  import simpler_env
  from simpler_env.utils.env.observation_utils import get_image_from_maniskill2_obs_dict
  
  env = simpler_env.make('google_robot_pick_coke_can')
  obs, reset_info = env.reset()
  instruction = env.get_language_instruction()
  print("Reset info", reset_info)
  print("Instruction", instruction)
  
  done, truncated = False, False
  while not (done or truncated):
     # action[:3]: delta xyz; action[3:6]: delta rotation in axis-angle representation;
     # action[6:7]: gripper (the meaning of open / close depends on robot URDF)
     image = get_image_from_maniskill2_obs_dict(env, obs)
     action = env.action_space.sample() # replace this with your policy inference
     obs, reward, done, truncated, info = env.step(action) # for long horizon tasks, you can call env.advance_to_next_subtask() to advance to the next subtask; the environment might also autoadvance if env._elapsed_steps is larger than a threshold
     new_instruction = env.get_language_instruction()
     if new_instruction != instruction:
        # for long horizon tasks, we get a new instruction when robot proceeds to the next subtask
        instruction = new_instruction
        print("New Instruction", instruction)
  
  episode_stats = info.get('episode_stats', {})
  print("Episode stats", episode_stats)
```

mock/patch design:
- follows unittest.mock and directly use them

### Proxy vs Materialization Problem

**Problem**: When should RPC return a proxy vs actual value?
- `simpler_env.make()` should return proxy (Environment object)
- `env.step(action)` should return tuple container
- eventually we need actual values (numpy arrays, strings, etc.)

**Solution**: Explicit materialization by user
- Everything returns `RPCProxy` by default (lazy evaluation)
- User explicitly calls `materialize(obj)` when actual value is needed
- Simple, predictable, and gives full control to user

```python
import simplerpyc
from simplerpyc import materialize

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

