<div align="center">
  <a href="https://github.com/mahimailabs/openrtc">
    <img src="assets/banner.png" alt="OpenRTC Banner" width="100%" />
  </a>
</div>

<br />

<div align="center">
  <strong>A Python framework for running multiple LiveKit voice agents in a single worker process with shared prewarmed models.</strong>
</div>
<br />

<div align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://pypi.org/project/openrtc/"><img src="https://img.shields.io/pypi/v/openrtc.svg" alt="PyPI version"></a>
  <a href="https://codecov.io/gh/mahimairaja/openrtc-python"><img src="https://codecov.io/gh/mahimairaja/openrtc-python/graph/badge.svg?token=W7VQ5FGSA9" alt="codecov"></a>
</div>

<br />

OpenRTC is designed for the common case where you want to run several different
voice agents on a small VPS without paying the memory cost of one full
LiveKit worker per agent.

<br />

<details>
  <summary><b>Table of Contents</b></summary>
  <ol>
    <li><a href="#why-openrtc-exists">Why OpenRTC exists</a></li>
    <li><a href="#what-openrtc-wraps">What OpenRTC wraps</a></li>
    <li><a href="#memory-comparison">Memory comparison</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#quick-start-register-agents-directly-with-add">Quick start: register agents directly</a></li>
    <li><a href="#quick-start-discover-agent-files-with-agent_config">Quick start: discover agent files</a></li>
    <li><a href="#routing-behavior">Routing behavior</a></li>
    <li><a href="#greetings-and-session-options">Greetings and session options</a></li>
    <li><a href="#provider-model-strings">Provider model strings</a></li>
    <li><a href="#cli-usage">CLI usage</a></li>
    <li><a href="#public-api-at-a-glance">Public API at a glance</a></li>
    <li><a href="#project-structure">Project structure</a></li>
    <li><a href="#contributing">Contributing</a></li>
  </ol>
</details>

<br />

## Why OpenRTC exists

A standard `livekit-agents` worker process loads shared runtime assets such as
Python, Silero VAD, and turn-detection models. If you run ten agents as ten
separate workers, you pay that base memory cost ten times.

OpenRTC keeps your agent classes completely standard and only centralizes the
worker boilerplate:

- shared prewarm for VAD and turn detection
- metadata-based dispatch to the correct agent
- per-agent `AgentSession` construction inside one worker

Your agent code still subclasses `livekit.agents.Agent` directly. If you stop
using OpenRTC later, your agent classes still work as normal LiveKit agents.

## What OpenRTC wraps

OpenRTC intentionally wraps only the worker orchestration layer:

1. `AgentServer()` setup and prewarm
2. a universal `@server.rtc_session()` entrypoint
3. per-call `AgentSession()` creation with the right providers

OpenRTC does **not** replace:

- `livekit.agents.Agent`
- `@function_tool`
- `RunContext`
- `on_enter`, `on_exit`, `llm_node`, `stt_node`, `tts_node`
- standard LiveKit deployment patterns

## Memory comparison

| Deployment model | Shared runtime loads | Approximate memory shape |
| --- | --- | --- |
| 10 separate LiveKit workers | 10x | ~500 MB × 10 |
| 1 OpenRTC pool with 10 agents | 1x shared + per-call session cost | ~500 MB shared + active-call overhead |

The exact numbers depend on your providers, concurrency, and environment, but
OpenRTC is built to reduce duplicate worker overhead.

## Installation

Install OpenRTC from PyPI:

```bash
pip install openrtc
```

The base package pulls in `livekit-agents[openai,silero,turn-detector]`, so the
runtime plugins required by shared prewarm are installed without extra flags.

Install the Typer/Rich CLI (`openrtc list`, `openrtc start`, `openrtc dev`, …)
with:

```bash
pip install 'openrtc[cli]'
```

Install the optional **Textual sidecar TUI** (`openrtc tui --watch`) with:

```bash
pip install 'openrtc[cli,tui]'
```

If you are developing locally, the repository uses `uv` for environment and
command management.

### Required environment variables

OpenRTC uses the same environment variables as a standard LiveKit worker:

```bash
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

For provider-native OpenAI plugin objects, set:

```bash
OPENAI_API_KEY=...
```

## Quick start: register agents directly with `add()`

Use `AgentPool.add(...)` when you want the most explicit setup.

```python
from livekit.agents import Agent
from livekit.plugins import openai
from openrtc import AgentPool


class RestaurantAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You help callers make restaurant bookings.")


class DentalAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You help callers manage dental appointments.")


pool = AgentPool()
pool.add(
    "restaurant",
    RestaurantAgent,
    stt=openai.STT(model="gpt-4o-mini-transcribe"),
    llm=openai.responses.LLM(model="gpt-4.1-mini"),
    tts=openai.TTS(model="gpt-4o-mini-tts"),
    greeting="Welcome to reservations.",
)
pool.add(
    "dental",
    DentalAgent,
    stt=openai.STT(model="gpt-4o-mini-transcribe"),
    llm=openai.responses.LLM(model="gpt-4.1-mini"),
    tts=openai.TTS(model="gpt-4o-mini-tts"),
)
pool.run()
```

## Quick start: discover agent files with `@agent_config(...)`

Use discovery when you want one agent module per file. OpenRTC will import each
module, find a local `Agent` subclass, and optionally read overrides from the
`@agent_config(...)` decorator.

Discovered agents are safe to run under `livekit dev`, including spawn-based
worker runtimes such as macOS. For direct `add()` registration, define agent
classes at module scope so worker processes can reload them.

```python
from pathlib import Path

from livekit.plugins import openai
from openrtc import AgentPool

pool = AgentPool(
    default_stt=openai.STT(model="gpt-4o-mini-transcribe"),
    default_llm=openai.responses.LLM(model="gpt-4.1-mini"),
    default_tts=openai.TTS(model="gpt-4o-mini-tts"),
)
pool.discover(Path("./agents"))
pool.run()
```

Example agent file:

```python
from livekit.agents import Agent
from openrtc import agent_config


@agent_config(name="restaurant", greeting="Welcome to reservations.")
class RestaurantAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You help callers make restaurant bookings.")
```

### Discovery defaults

A discovered module does not need to provide any OpenRTC metadata. If the agent
class has no `@agent_config(...)` decorator:

- the agent name defaults to the Python filename stem
- STT/LLM/TTS/greeting fall back to `AgentPool(...)` defaults

That keeps discovery straightforward while still allowing per-agent overrides
when needed.

## Routing behavior

For each incoming room, `AgentPool` resolves the agent in this order:

1. `ctx.job.metadata["agent"]`
2. `ctx.job.metadata["demo"]`
3. `ctx.room.metadata["agent"]`
4. `ctx.room.metadata["demo"]`
5. room name prefix match, such as `restaurant-call-123`
6. the first registered agent

This lets one worker process host several agents while staying compatible with
standard LiveKit job and room metadata.

If metadata references an unknown registered name, OpenRTC raises a `ValueError`
instead of silently falling back.

## Greetings and session options

OpenRTC can play a greeting after `ctx.connect()` and pass extra options into
`AgentSession(...)`.

```python
pool.add(
    "restaurant",
    RestaurantAgent,
    greeting="Welcome to reservations.",
    session_kwargs={"turn_handling": {"interruption": {"enabled": False}}},
    max_tool_steps=4,
    preemptive_generation=True,
)
```

Direct keyword arguments take precedence over the same keys inside
`session_kwargs`.

By default, OpenRTC builds explicit `turn_handling` for each session using the
multilingual turn detector with VAD-based interruption. That keeps the shared
turn detector available without implicitly enabling LiveKit adaptive
interruption. To opt into adaptive interruption explicitly, pass
`session_kwargs={"turn_handling": {"interruption": {"mode": "adaptive"}}}`.

## Provider configuration

OpenRTC now passes `stt`, `llm`, and `tts` through to `livekit-agents`
unchanged.

For self-hosted and provider-native setups, pass instantiated provider objects:

- `openai.STT(model="gpt-4o-mini-transcribe")`
- `openai.responses.LLM(model="gpt-4.1-mini")`
- `openai.TTS(model="gpt-4o-mini-tts")`

If you pass raw strings such as `openai/gpt-4.1-mini`, OpenRTC leaves them
unchanged and `livekit-agents` will interpret them according to the current
LiveKit runtime, which may mean inference-backed behavior on compatible cloud
deployments.

## CLI usage

OpenRTC includes a CLI for discovery-based workflows. Subcommands mirror the
LiveKit Agents CLI (`dev`, `start`, `console`, `connect`, `download-files`, as
in `python agent.py <command>`), plus `list` and `tui`.

**Typical path:** set `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`,
then run the worker with only `--agents-dir` (plus any `--default-*` strings
your agents need).

```bash
export LIVEKIT_URL=ws://localhost:7880
export LIVEKIT_API_KEY=devkey
export LIVEKIT_API_SECRET=secret

openrtc dev --agents-dir ./agents
# or
openrtc start --agents-dir ./agents
```

Defaults are conservative (no dashboard, 1s refresh where applicable). Tuning
flags are grouped under **Advanced** in each command’s `--help`.

### List discovered agents

```bash
openrtc list \
  --agents-dir ./agents \
  --default-stt openai/gpt-4o-mini-transcribe \
  --default-llm openai/gpt-4.1-mini \
  --default-tts openai/gpt-4o-mini-tts
```

These CLI defaults are raw passthrough strings for `livekit-agents`, not
provider-object construction.

Stable output for scripts and CI:

- `--plain` — line-oriented text without ANSI or table borders (similar to the
  legacy `print` format). Use `--resources` for source-size and RSS lines.
- `--json` — machine-readable JSON with a `schema_version` field; combine with
  `--resources` for `resource_summary` (footprint + resident-set metadata).
  The `resident_set` object includes a `description`: on **Linux** it reflects
  current **VmRSS**; on **macOS** it is **peak** `ru_maxrss` (bytes), not
  instantaneous live RSS—compare runs only on the same OS.

### Run workers (production and development)

```bash
openrtc start --agents-dir ./agents
openrtc dev --agents-dir ./agents
```

Optional runtime visibility:

- **`--dashboard`** — Rich summary (worker RSS, sessions, routing, savings
  estimate). Off by default.
- **`--metrics-json-file ./runtime.json`** — Overwrites a JSON file each tick with
  the latest snapshot (automation / CI). See **Advanced** in `--help`.
- **`--metrics-jsonl ./openrtc-metrics.jsonl`** — Append **JSON Lines** (truncates
  when the worker starts): versioned `snapshot` rows plus optional `event`
  rows for session lifecycle. Use with a second terminal:

  ```bash
  pip install 'openrtc[cli,tui]'
  openrtc tui --watch ./openrtc-metrics.jsonl
  ```

Other worker subcommands match LiveKit: `openrtc console`, `openrtc connect
--room …`, and `openrtc download-files` (minimal options: agents dir + connection
only). See [docs/cli.md](docs/cli.md) for full detail.

Worker commands discover agents first, then delegate to the LiveKit CLI;
OpenRTC-only flags are not forwarded to LiveKit’s parser.

## Public API at a glance

OpenRTC currently exposes:

- `AgentPool`
- `AgentConfig`
- `AgentDiscoveryConfig`
- `agent_config(...)`

On `AgentPool`, the primary public methods and properties are:

- `add(...)`
- `discover(...)`
- `list_agents()`
- `get(name)`
- `remove(name)`
- `run()`
- `runtime_snapshot()`
- `drain_metrics_stream_events()` — drain queued session lifecycle events for JSONL
  export (used by the CLI; rarely needed in application code)
- `server`

## Project structure

```text
src/openrtc/
├── __init__.py
├── cli.py
├── cli_app.py
├── metrics_stream.py
├── tui_app.py
└── pool.py
```

- `pool.py` contains the core `AgentPool` implementation and discovery helpers
- `cli.py` / `cli_app.py` provide the Typer/Rich CLI (`openrtc[cli]`)
- `metrics_stream.py` defines the JSONL metrics stream format
- `tui_app.py` implements the optional Textual sidecar (`openrtc[tui]`)
- `__init__.py` exposes the public package API

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md)
before opening a pull request.

## License

MIT. See [LICENSE](LICENSE).
