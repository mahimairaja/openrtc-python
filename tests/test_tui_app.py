"""Tests for the Textual sidecar ``openrtc tui --watch`` (requires Textual)."""

from __future__ import annotations

import json

import pytest

from openrtc.metrics_stream import snapshot_envelope
from openrtc.resources import PoolRuntimeSnapshot

pytest.importorskip("textual")


@pytest.mark.asyncio
async def test_metrics_tui_displays_event_line(tmp_path) -> None:
    from openrtc.metrics_stream import event_envelope
    from openrtc.tui_app import MetricsTuiApp

    path = tmp_path / "ev.jsonl"
    ev = json.dumps(
        event_envelope(seq=2, payload={"event": "session_started", "agent": "a"}),
        sort_keys=True,
    )
    path.write_text(ev + "\n", encoding="utf-8")

    app = MetricsTuiApp(path, from_start=True)
    async with app.run_test() as pilot:
        app._poll_file()
        await pilot.pause()
        event_w = app.query_one("#event")
        text = str(event_w.renderable)
        assert "session_started" in text
        assert "agent" in text
        assert "a" in text


@pytest.mark.asyncio
async def test_metrics_tui_skips_malformed_line_then_parses_valid(
    tmp_path,
    minimal_pool_runtime_snapshot: PoolRuntimeSnapshot,
) -> None:
    from openrtc.tui_app import MetricsTuiApp

    path = tmp_path / "mix.jsonl"
    snap = minimal_pool_runtime_snapshot
    good = json.dumps(snapshot_envelope(seq=1, snapshot=snap), sort_keys=True)
    path.write_text("not-valid-json\n" + good + "\n", encoding="utf-8")

    app = MetricsTuiApp(path, from_start=True)
    async with app.run_test() as pilot:
        app._poll_file()
        await pilot.pause()
        status = app.query_one("#status")
        assert "seq=1" in str(status.renderable)


@pytest.mark.asyncio
async def test_metrics_tui_displays_snapshot_line(
    tmp_path,
    minimal_pool_runtime_snapshot: PoolRuntimeSnapshot,
) -> None:
    from openrtc.tui_app import MetricsTuiApp

    path = tmp_path / "stream.jsonl"
    snap = minimal_pool_runtime_snapshot
    line = json.dumps(snapshot_envelope(seq=1, snapshot=snap), sort_keys=True)
    path.write_text(line + "\n", encoding="utf-8")

    app = MetricsTuiApp(path, from_start=True)
    async with app.run_test() as pilot:
        app._poll_file()
        await pilot.pause()
        status = app.query_one("#status")
        text = str(status.renderable)
        assert "seq=1" in text
        assert "registered=1" in text
