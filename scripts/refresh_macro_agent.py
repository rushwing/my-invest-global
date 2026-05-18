"""CLI entry point for the macro data agent.

Usage:
    uv run refresh-macro-agent                      # continuous loop, 60s poll
    uv run refresh-macro-agent --once               # single pass, then exit
    uv run refresh-macro-agent --once --groups I,K  # restrict to groups
    uv run refresh-macro-agent --poll 120           # custom poll interval
"""

from __future__ import annotations

import argparse
import logging
import sys

from engine.macro_agent.orchestrator import MacroOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Macro data agent refresh")
    p.add_argument("--once", action="store_true", help="Run once and exit")
    p.add_argument(
        "--groups",
        default=None,
        help="Comma-separated group codes to collect, e.g. I,J,K",
    )
    p.add_argument(
        "--poll",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Poll interval in seconds for continuous loop (default: 60)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    groups = [g.strip() for g in args.groups.split(",")] if args.groups else None

    orch = MacroOrchestrator.from_defaults()

    if args.once:
        log.info("Running macro agent once (groups=%s)", groups)
        orch.run_once(groups=groups)
        log.info("Done.")
    else:
        log.info("Starting macro agent loop (poll=%ds, groups=%s)", args.poll, groups)
        orch.run_loop(poll_s=args.poll)


if __name__ == "__main__":
    main()
