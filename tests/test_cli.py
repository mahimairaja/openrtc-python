from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from openrtc.cli import main


@dataclass
class StubConfig:
    name: str
    agent_cls: type[Any]
    stt: Any = None
    llm: Any = None
    tts: Any = None
    greeting: str | None = None


class StubAgent:
    __name__ = "StubAgent"


class StubPool:
    def __init__(self, discovered: list[StubConfig]) -> None:
        self._discovered = discovered
        self.discover_calls: list[Path] = []
        self.run_called = False

    def discover(self, agents_dir: Path) -> list[StubConfig]:
        self.discover_calls.append(agents_dir)
        return self._discovered

    def run(self) -> None:
        self.run_called = True


@pytest.fixture
def original_argv() -> list[str]:
    return sys.argv.copy()


def test_list_command_prints_discovered_agents(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stub_pool = StubPool(
        [
            StubConfig(
                name="restaurant",
                agent_cls=StubAgent,
                stt="deepgram/nova-3",
                llm="openai/gpt-4.1-mini",
                tts="cartesia/sonic-3",
                greeting="hello",
            )
        ]
    )
    monkeypatch.setattr("openrtc.cli.AgentPool", lambda: stub_pool)

    exit_code = main(["list", "--agents-dir", "./agents"])

    assert exit_code == 0
    assert stub_pool.discover_calls == [Path("./agents")]
    assert "restaurant: class=StubAgent" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["start", "dev"])
def test_run_commands_inject_livekit_mode_and_run_pool(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    original_argv: list[str],
) -> None:
    stub_pool = StubPool([StubConfig(name="restaurant", agent_cls=StubAgent)])
    monkeypatch.setattr("openrtc.cli.AgentPool", lambda: stub_pool)
    monkeypatch.setattr(sys, "argv", original_argv.copy())

    exit_code = main([command, "--agents-dir", "./agents"])

    assert exit_code == 0
    assert stub_pool.run_called is True
    assert sys.argv == [original_argv[0], command]


def test_cli_returns_non_zero_when_no_agents_are_discovered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_pool = StubPool([])
    monkeypatch.setattr("openrtc.cli.AgentPool", lambda: stub_pool)

    exit_code = main(["list", "--agents-dir", "./agents"])

    assert exit_code == 1
