# OpenRTC

OpenRTC is a Python framework for running multiple LiveKit voice agents in a
single worker process with shared prewarmed models.

## Decorator-based discovery with shared defaults

Use `@agent_config(...)` on a standard LiveKit `Agent` subclass to attach
optional discovery metadata. Then set shared providers once on `AgentPool` and
only override the values that differ per agent.

```python
from pathlib import Path

from openrtc import AgentPool, agent_config
from livekit.agents import Agent


@agent_config(name="restaurant")
class RestaurantAgent(Agent):
    ...


pool = AgentPool(
    default_stt="deepgram/nova-3:multi",
    default_llm="openai/gpt-4.1-mini",
    default_tts="cartesia/sonic-3",
)
pool.discover(Path("./agents"))
pool.run()
```

The CLI also accepts shared defaults for discovered agents:

```bash
openrtc list \
  --agents-dir ./examples/agents \
  --default-stt deepgram/nova-3:multi \
  --default-llm openai/gpt-4.1-mini \
  --default-tts cartesia/sonic-3
```

For backward compatibility, discovery still supports legacy module-level
`AGENT_*` variables, but the decorator is the preferred pattern.


## Registering agents with explicit `AgentSession` options

`AgentPool.add()` continues to support the mapping-based `session_kwargs=` API,
and it now also accepts direct `AgentSession` keyword arguments for the Milestone
3 calling style. Direct keyword arguments override entries from
`session_kwargs=`, while the named `stt=`, `llm=`, and `tts=` parameters remain
the highest-precedence public API for those providers.

```python
from openrtc import AgentPool
from livekit.agents import Agent


class SupportAgent(Agent):
    ...


pool = AgentPool(default_stt="deepgram/nova-3:multi")
pool.add(
    "support",
    SupportAgent,
    llm="openai/gpt-4.1-mini",
    session_kwargs={"allow_interruptions": False},
    allow_interruptions=True,
)
```

