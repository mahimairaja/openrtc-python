from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typer.testing import CliRunner

from openrtc.pool import AgentConfig, AgentPool
from openrtc.resources import (
    agent_disk_footprints,
    file_size_bytes,
    format_byte_size,
    process_resident_set_bytes,
)

logger = logging.getLogger("openrtc")

app = typer.Typer(
    name="openrtc",
    help="Discover and run multiple LiveKit agents in one worker.",
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()


def _pool_kwargs(
    default_stt: str | None,
    default_llm: str | None,
    default_tts: str | None,
    default_greeting: str | None,
) -> dict[str, Any]:
    return {
        "default_stt": default_stt,
        "default_llm": default_llm,
        "default_tts": default_tts,
        "default_greeting": default_greeting,
    }


def _discover_or_exit(agents_dir: Path, pool: AgentPool) -> list[AgentConfig]:
    discovered = pool.discover(agents_dir)
    if not discovered:
        logger.error("No agent modules were discovered in %s.", agents_dir)
        raise typer.Exit(code=1)
    return discovered


def _truncate_cell(text: str, max_len: int = 36) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


AgentsDirArg = Annotated[
    Path,
    typer.Option(
        "--agents-dir",
        help="Directory containing discoverable agent modules.",
        exists=False,
        resolve_path=True,
        path_type=Path,
    ),
]

DefaultSttArg = Annotated[
    str | None,
    typer.Option(
        "--default-stt",
        help=(
            "Default STT provider used when a discovered agent does not "
            "override STT via @agent_config(...)."
        ),
    ),
]

DefaultLlmArg = Annotated[
    str | None,
    typer.Option(
        "--default-llm",
        help=(
            "Default LLM provider used when a discovered agent does not "
            "override LLM via @agent_config(...)."
        ),
    ),
]

DefaultTtsArg = Annotated[
    str | None,
    typer.Option(
        "--default-tts",
        help=(
            "Default TTS provider used when a discovered agent does not "
            "override TTS via @agent_config(...)."
        ),
    ),
]

DefaultGreetingArg = Annotated[
    str | None,
    typer.Option(
        "--default-greeting",
        help=(
            "Default greeting used when a discovered agent does not "
            "override greeting via @agent_config(...)."
        ),
    ),
]


@app.command("list")
def list_command(
    agents_dir: AgentsDirArg,
    resources: Annotated[
        bool,
        typer.Option(
            "--resources",
            help=(
                "Show on-disk source sizes and approximate process memory (RSS) "
                "for this CLI process after discovery."
            ),
        ),
    ] = False,
    default_stt: DefaultSttArg = None,
    default_llm: DefaultLlmArg = None,
    default_tts: DefaultTtsArg = None,
    default_greeting: DefaultGreetingArg = None,
) -> None:
    """List discovered agents and optional resource estimates."""
    pool = AgentPool(
        **_pool_kwargs(default_stt, default_llm, default_tts, default_greeting)
    )
    discovered = _discover_or_exit(agents_dir, pool)

    table = Table(
        title="Discovered agents",
        show_header=True,
        header_style="bold",
        show_lines=False,
    )
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Class", style="green")
    table.add_column("STT")
    table.add_column("LLM")
    table.add_column("TTS")
    table.add_column("Greeting")
    if resources:
        table.add_column("Source file", style="dim")

    for config in discovered:
        greeting = "" if config.greeting is None else config.greeting
        row = [
            config.name,
            config.agent_cls.__name__,
            _truncate_cell(repr(config.stt)),
            _truncate_cell(repr(config.llm)),
            _truncate_cell(repr(config.tts)),
            _truncate_cell(greeting),
        ]
        if resources:
            if config.source_path is not None:
                sz = file_size_bytes(config.source_path)
                row.append(format_byte_size(sz))
            else:
                row.append("—")
        table.add_row(*row)

    console.print(table)

    if resources:
        _print_resource_summary(discovered)


@app.command("start")
def start_command(
    agents_dir: AgentsDirArg,
    default_stt: DefaultSttArg = None,
    default_llm: DefaultLlmArg = None,
    default_tts: DefaultTtsArg = None,
    default_greeting: DefaultGreetingArg = None,
) -> None:
    """Run the LiveKit worker (production-style entrypoint)."""
    pool = AgentPool(
        **_pool_kwargs(default_stt, default_llm, default_tts, default_greeting)
    )
    _discover_or_exit(agents_dir, pool)
    sys.argv = [sys.argv[0], "start"]
    pool.run()


@app.command("dev")
def dev_command(
    agents_dir: AgentsDirArg,
    default_stt: DefaultSttArg = None,
    default_llm: DefaultLlmArg = None,
    default_tts: DefaultTtsArg = None,
    default_greeting: DefaultGreetingArg = None,
) -> None:
    """Run the LiveKit worker in development mode."""
    pool = AgentPool(
        **_pool_kwargs(default_stt, default_llm, default_tts, default_greeting)
    )
    _discover_or_exit(agents_dir, pool)
    sys.argv = [sys.argv[0], "dev"]
    pool.run()


def _print_resource_summary(discovered: list[AgentConfig]) -> None:
    footprints = agent_disk_footprints(discovered)
    total_source = sum(f.size_bytes for f in footprints)

    lines: list[str] = [
        (
            f"Agents: {len(discovered)}; on-disk agent source total: "
            f"{format_byte_size(total_source)}"
        ),
    ]
    if len(footprints) < len(discovered):
        lines.append(
            "Per-agent source size is shown only when the module path is known "
            "(e.g. via discovery)."
        )

    rss = process_resident_set_bytes()
    if rss is not None:
        if sys.platform == "darwin":
            lines.append(
                f"Approximate resident memory (peak RSS on macOS): "
                f"{format_byte_size(rss)}"
            )
        else:
            lines.append(f"Approximate resident memory (RSS): {format_byte_size(rss)}")
    else:
        lines.append("Resident memory (RSS): not available on this platform.")

    lines.append("")
    lines.append(
        "OpenRTC runs every agent in one shared LiveKit worker process, so you ship "
        "one container image and one runtime instead of duplicating a large base "
        "image per agent. Actual memory at runtime depends on models, concurrent "
        "sessions, and providers; use host metrics in production."
    )

    console.print()
    console.print(
        Panel(
            "\n".join(lines),
            title="[bold]Resource summary[/bold]",
            subtitle="Local estimates for this [code]openrtc list[/code] process",
            border_style="blue",
        )
    )


def main(argv: list[str] | None = None) -> int:
    """Run the OpenRTC CLI (Typer + Rich)."""
    runner = CliRunner()
    cli_args = argv if argv is not None else sys.argv[1:]
    result = runner.invoke(app, cli_args, prog_name="openrtc")
    return result.exit_code
