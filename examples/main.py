from __future__ import annotations

from pathlib import Path

from openrtc import AgentPool


def main() -> None:
    pool = AgentPool()
    pool.discover(Path(__file__).with_name("agents"))
    pool.run()


if __name__ == "__main__":
    main()
