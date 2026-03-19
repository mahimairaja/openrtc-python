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

## Session routing and greetings

`AgentPool` resolves sessions in this order:

1. `ctx.job.metadata["agent"]` or `ctx.job.metadata["demo"]`
2. `ctx.room.metadata["agent"]` or `ctx.room.metadata["demo"]`
3. room name prefix matching such as `restaurant-call-123`
4. the first registered agent

Registered greetings are generated after `ctx.connect()`, and advanced
`AgentSession` options can be passed either with `session_kwargs` or directly as
keyword arguments to `add()`. Direct keyword arguments take precedence when the
same option is provided both ways.

```python
pool.add(
    "restaurant",
    RestaurantAgent,
    greeting="Welcome to reservations.",
    session_kwargs={"allow_interruptions": False},
    max_tool_steps=4,
    preemptive_generation=True,
)
```

