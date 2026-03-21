"""Console script entrypoint for OpenRTC.

The Typer/Rich implementation lives in :mod:`openrtc.cli_app` and is installed
with the optional extra ``openrtc[cli]``.
"""

from __future__ import annotations

import sys
from typing import Any

CLI_EXTRA_INSTALL_HINT = (
    "The OpenRTC CLI requires optional dependencies. "
    "Install with: pip install 'openrtc[cli]'"
)


def main(argv: list[str] | None = None) -> int:
    """Run the OpenRTC CLI when optional ``cli`` dependencies are installed."""
    try:
        from openrtc.cli_app import main as run_cli
    except ImportError:
        print(CLI_EXTRA_INSTALL_HINT, file=sys.stderr)
        return 1
    return run_cli(argv)


def __getattr__(name: str) -> Any:
    if name == "app":
        try:
            from openrtc.cli_app import app as typer_app
        except ImportError as exc:
            raise ImportError(CLI_EXTRA_INSTALL_HINT) from exc
        return typer_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
