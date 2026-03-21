"""Console script entrypoint for OpenRTC.

The Typer/Rich implementation lives in :mod:`openrtc.cli_app` and is installed
with the optional extra ``openrtc[cli]``.
"""

from __future__ import annotations

import importlib.util
import sys
from typing import Any

CLI_EXTRA_INSTALL_HINT = (
    "The OpenRTC CLI requires optional dependencies. "
    "Install with: pip install 'openrtc[cli]'"
)

_CLI_IMPORT_ERROR = (
    "Failed to import openrtc.cli_app even though Typer and Rich appear to be "
    "installed. This usually indicates a broken install or an internal error, "
    "not a missing optional extra."
)


def _optional_cli_dependencies_installed() -> bool:
    return (
        importlib.util.find_spec("typer") is not None
        and importlib.util.find_spec("rich") is not None
    )


def main(argv: list[str] | None = None) -> int:
    """Run the OpenRTC CLI when optional ``cli`` dependencies are installed."""
    if not _optional_cli_dependencies_installed():
        print(CLI_EXTRA_INSTALL_HINT, file=sys.stderr)
        return 1
    try:
        from openrtc.cli_app import main as run_cli
    except ImportError as exc:
        raise ImportError(_CLI_IMPORT_ERROR) from exc
    return run_cli(argv)


def __getattr__(name: str) -> Any:
    if name == "app":
        if not _optional_cli_dependencies_installed():
            raise ImportError(CLI_EXTRA_INSTALL_HINT)
        try:
            from openrtc.cli_app import app as typer_app
        except ImportError as exc:
            raise ImportError(_CLI_IMPORT_ERROR) from exc
        return typer_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
