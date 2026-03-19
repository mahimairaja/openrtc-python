from __future__ import annotations

import pytest
from livekit.agents import Agent

from openrtc import AgentPool


class DemoAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="Test agent")


def test_add_registers_agent() -> None:
    pool = AgentPool()

    config = pool.add(
        "test",
        DemoAgent,
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3",
    )

    assert config.name == "test"
    assert pool.list_agents() == ["test"]


def test_add_uses_pool_defaults_when_agent_values_are_omitted() -> None:
    pool = AgentPool(
        default_stt="deepgram/nova-3:multi",
        default_llm="openai/gpt-4.1-mini",
        default_tts="cartesia/sonic-3",
        default_greeting="Hello from OpenRTC.",
    )

    config = pool.add("test", DemoAgent)

    assert config.stt == "deepgram/nova-3:multi"
    assert config.llm == "openai/gpt-4.1-mini"
    assert config.tts == "cartesia/sonic-3"
    assert config.greeting == "Hello from OpenRTC."


def test_add_stores_session_kwargs_copy() -> None:
    pool = AgentPool()
    session_kwargs = {
        "preemptive_generation": True,
        "min_endpointing_delay": 0.5,
    }

    config = pool.add("test", DemoAgent, session_kwargs=session_kwargs)
    session_kwargs["preemptive_generation"] = False

    assert config.session_kwargs == {
        "preemptive_generation": True,
        "min_endpointing_delay": 0.5,
    }


def test_add_duplicate_name_raises() -> None:
    pool = AgentPool()
    pool.add("test", DemoAgent)

    with pytest.raises(ValueError):
        pool.add("test", DemoAgent)


@pytest.mark.parametrize("agent_cls", [str, object])
def test_add_non_agent_raises(agent_cls: type[object]) -> None:
    pool = AgentPool()

    with pytest.raises(TypeError):
        pool.add("test", agent_cls)  # type: ignore[arg-type]


def test_list_agents_returns_registration_order() -> None:
    pool = AgentPool()
    pool.add("restaurant", DemoAgent)
    pool.add("dental", DemoAgent)

    assert pool.list_agents() == ["restaurant", "dental"]


def test_get_returns_registered_agent() -> None:
    pool = AgentPool()
    config = pool.add("restaurant", DemoAgent)

    assert pool.get("restaurant") is config


def test_get_unknown_agent_raises_key_error() -> None:
    pool = AgentPool()

    with pytest.raises(KeyError, match="Unknown agent 'missing'"):
        pool.get("missing")


def test_remove_returns_removed_agent() -> None:
    pool = AgentPool()
    config = pool.add("restaurant", DemoAgent)

    removed = pool.remove("restaurant")

    assert removed is config
    assert pool.list_agents() == []


def test_remove_unknown_agent_raises_key_error() -> None:
    pool = AgentPool()

    with pytest.raises(KeyError, match="Unknown agent 'missing'"):
        pool.remove("missing")


def test_run_without_agents_raises() -> None:
    pool = AgentPool()

    with pytest.raises(RuntimeError):
        pool.run()
