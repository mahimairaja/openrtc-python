from __future__ import annotations

import logging
import resource
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from openrtc.pool import AgentConfig

logger = logging.getLogger("openrtc")


@dataclass(frozen=True, slots=True)
class AgentDiskFootprint:
    """On-disk size for a single agent module file."""

    name: str
    path: Path
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ProcessResidentSetInfo:
    """Best-effort resident-memory-related metric for this process (platform-specific)."""

    bytes_value: int | None
    """Numeric value when available, else ``None``."""

    metric: str
    """Stable identifier: ``linux_vm_rss``, ``darwin_ru_max_rss``, or ``unavailable``."""

    description: str
    """Plain-language meaning of ``bytes_value`` on this platform."""


def format_byte_size(num_bytes: int) -> str:
    """Return a short human-readable size string using binary units."""
    if num_bytes < 0:
        num_bytes = 0
    value = float(num_bytes)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for i, unit in enumerate(units):
        if value < 1024.0 or i == len(units) - 1:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{int(num_bytes)} B"


def file_size_bytes(path: Path) -> int:
    """Return the size of a file in bytes, or ``0`` if it cannot be read."""
    try:
        return path.stat().st_size
    except OSError as exc:
        logger.debug("Could not stat %s: %s", path, exc)
        return 0


def agent_disk_footprints(configs: Sequence[AgentConfig]) -> list[AgentDiskFootprint]:
    """Collect per-agent source file sizes when a path was recorded at registration."""
    footprints: list[AgentDiskFootprint] = []
    for config in configs:
        if config.source_path is None:
            continue
        path = config.source_path
        footprints.append(
            AgentDiskFootprint(
                name=config.name,
                path=path,
                size_bytes=file_size_bytes(path),
            )
        )
    return footprints


def get_process_resident_set_info() -> ProcessResidentSetInfo:
    """Return platform-specific RSS-related metrics for this process.

    The returned :attr:`ProcessResidentSetInfo.bytes_value` is **not** always
    comparable across operating systems:

    - **Linux**: current resident set size (VmRSS from ``/proc/self/status``).
    - **macOS**: maximum resident set size from :func:`resource.getrusage`
      (``ru_maxrss`` in bytes), which tracks peak usage—not necessarily the
      current instantaneous RSS.
    - **Other** (e.g. Windows): unavailable here (``None``).
    """
    if sys.platform.startswith("linux"):
        value = _linux_rss_bytes()
        return ProcessResidentSetInfo(
            bytes_value=value,
            metric="linux_vm_rss",
            description=(
                "Current resident set size (VmRSS from /proc/self/status), in bytes."
            ),
        )
    if sys.platform == "darwin":
        value = _macos_rss_bytes()
        return ProcessResidentSetInfo(
            bytes_value=value,
            metric="darwin_ru_max_rss",
            description=(
                "Maximum resident set size from getrusage (ru_maxrss), in bytes; "
                "not the same as instantaneous current RSS."
            ),
        )
    return ProcessResidentSetInfo(
        bytes_value=None,
        metric="unavailable",
        description="RSS not available on this platform (e.g. Windows).",
    )


def process_resident_set_bytes() -> int | None:
    """Return RSS-related bytes for this process, or ``None`` if unknown.

    Prefer :func:`get_process_resident_set_info` when you need platform context.
    This function returns only the numeric value (same rules as
    :func:`get_process_resident_set_info`).
    """
    return get_process_resident_set_info().bytes_value


def _linux_rss_bytes() -> int | None:
    try:
        text = Path("/proc/self/status").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2:
                # Value is in kB on Linux.
                return int(parts[1]) * 1024
    return None


def _macos_rss_bytes() -> int | None:
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
    except OSError:
        return None
    # On macOS, ru_maxrss is bytes (per CPython docs).
    value = int(usage.ru_maxrss)
    return value if value > 0 else None
