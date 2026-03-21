# OpenRTC API reference

Read this when you need the exact signature for `pool.add()`, `pool.discover()`,
session kwargs, or other `AgentPool` methods.

## Imports

```python
from openrtc import AgentPool, AgentConfig, AgentDiscoveryConfig, agent_config
```

## `AgentPool(...)`

```python
AgentPool(
    *,
    default_stt: str | Any = None,
    default_llm: str | Any = None,
    default_tts: str | Any = None,
    default_greeting: str | None = None,
)
```

## `pool.add(...)`

```python
pool.add(
    name: str,                                  # unique routing name
    agent_cls: type[Agent],                     # Agent subclass (module scope)
    *,
    stt: str | Any = None,                      # overrides pool default
    llm: str | Any = None,                      # overrides pool default
    tts: str | Any = None,                      # overrides pool default
    greeting: str | None = None,                # spoken after connect
    session_kwargs: Mapping[str, Any] = None,   # extra AgentSession kwargs
    **session_options: Any,                      # direct AgentSession kwargs (win over session_kwargs)
) -> AgentConfig
```

Raises `ValueError` on duplicate/empty name. Raises `TypeError` if
`agent_cls` is not an `Agent` subclass.

## `pool.discover(...)`

```python
pool.discover(agents_dir: str | Path) -> list[AgentConfig]
```

Scans for `*.py` files (skips `__init__.py` and `_`-prefixed). Each file must
define exactly one local `Agent` subclass. Reads `@agent_config(...)` metadata
if present. Internally calls `pool.add()` for each discovered agent.

## Other methods

```python
pool.list_agents() -> list[str]             # names in registration order
pool.get(name: str) -> AgentConfig          # raises KeyError
pool.remove(name: str) -> AgentConfig       # raises KeyError
pool.run() -> None                          # starts LiveKit worker
pool.server -> AgentServer                  # underlying server instance
```

## `@agent_config(...)`

```python
@agent_config(
    *,
    name: str | None = None,       # defaults to filename stem
    stt: str | Any = None,
    llm: str | Any = None,
    tts: str | Any = None,
    greeting: str | None = None,
)
```

All fields optional. Omitted fields inherit pool defaults.

## Session kwargs

Common kwargs forwarded to `AgentSession(...)` via `session_kwargs` or direct
keyword arguments to `add()`:

| Key | Type | Purpose |
|---|---|---|
| `max_tool_steps` | `int` | Max tool-call rounds per turn |
| `preemptive_generation` | `bool` | Start LLM before user finishes |
| `turn_handling` | `dict \| object` | Turn detection / interruption config |
