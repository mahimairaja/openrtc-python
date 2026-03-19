from __future__ import annotations

import asyncio

import pytest
from livekit.agents import Agent, AgentSession, JobContext

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
        llm="openai/gpt-5-mini",
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


def test_run_without_agents_raises() -> None:
    pool = AgentPool()

    with pytest.raises(RuntimeError):
        pool.run()


def test_add_merges_session_kwargs_with_direct_agent_session_kwargs() -> None:
    pool = AgentPool()

    config = pool.add(
        "test",
        DemoAgent,
        session_kwargs={"max_tool_steps": 2, "allow_interruptions": False},
        allow_interruptions=True,
        max_nested_fnc_calls=3,
    )

    assert config.session_kwargs == {
        "max_tool_steps": 2,
        "allow_interruptions": True,
        "max_nested_fnc_calls": 3,
    }


def test_add_named_session_parameters_override_session_kwargs() -> None:
    pool = AgentPool(default_stt="default-stt", default_llm="default-llm")

    config = pool.add(
        "test",
        DemoAgent,
        stt="named-stt",
        llm="named-llm",
        session_kwargs={
            "stt": "mapping-stt",
            "llm": "mapping-llm",
            "tts": "mapping-tts",
        },
        tts="named-tts",
    )

    assert config.stt == "named-stt"
    assert config.llm == "named-llm"
    assert config.tts == "named-tts"
    assert config.session_kwargs == {
        "stt": "mapping-stt",
        "llm": "mapping-llm",
        "tts": "mapping-tts",
    }


def test_handle_session_uses_direct_agent_session_kwargs() -> None:
    pool = AgentPool(default_stt="default-stt", default_llm="default-llm")
    pool.add(
        "test",
        DemoAgent,
        stt="named-stt",
        session_kwargs={"allow_interruptions": False, "vad": "custom-vad"},
        allow_interruptions=True,
    )

    ctx = JobContext()
    ctx.proc.userdata["vad"] = "pool-vad"
    ctx.proc.userdata["turn_detection"] = "pool-turn"

    asyncio.run(pool._handle_session(ctx))

    assert AgentSession.last_instance is not None
    # The conftest stub stores the latest instance on the class for inspection.
    assert AgentSession.last_instance.kwargs == {
        "allow_interruptions": True,
        "vad": "custom-vad",
        "stt": "named-stt",
        "llm": "default-llm",
        "tts": None,
        "turn_detection": "pool-turn",
    }


def test_add_rejects_non_mapping_session_kwargs() -> None:
    pool = AgentPool()

    with pytest.raises(TypeError):
        pool.add("test", DemoAgent, session_kwargs=[("stt", "deepgram")])  # type: ignore[arg-type]
