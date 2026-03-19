# Examples

The repository includes a small multi-agent example setup.

## Main example

`examples/main.py` registers two agents in a single `AgentPool`:

- `restaurant`
- `dental`

Both share the same worker process while using distinct instructions and tool
methods.

## Restaurant agent

The restaurant example shows an agent that can:

- check reservation availability
- create a reservation request
- summarize menu highlights

## Dental agent

The dental example shows an agent that can:

- schedule a cleaning
- explain pre-visit instructions
- share office hours

## Why these examples matter

These examples demonstrate the package's current design goal:
multiple specialized LiveKit agents can run in one worker process while sharing
prewarmed runtime resources.
