"""CLI entry point for Phase 9 analysis pipeline.

Usage:
    uv run python -m scripts.run_analysis --once --db data/db/aidc.duckdb
    uv run python -m scripts.run_analysis --daemon --db data/db/aidc.duckdb
"""
from __future__ import annotations

import argparse
import logging

log = logging.getLogger(__name__)


def _run_once(db_path: str) -> None:
    from engine.agent.runner import run_analysis
    from engine.agent.session_store import save_session
    from engine.agent.state import build_snapshot

    log.info("Building market snapshot ...")
    snap = build_snapshot(db_path)
    log.info("Running analysis (session %s) ...", snap.session_id)
    state = run_analysis(snap)
    save_session(db_path, state)
    log.info("Done: %d signals, %d errors", len(state["signals"]), len(state["errors"]))


def _run_daemon(db_path: str) -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BlockingScheduler(timezone="Asia/Hong_Kong")
    scheduler.add_job(
        _run_once,
        CronTrigger(hour=8, minute=0),
        args=[db_path],
        id="daily_analysis",
        replace_existing=True,
    )
    log.info("Scheduler started. Next run at 08:00 HKT daily.")
    scheduler.start()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Phase 9 analysis runner")
    parser.add_argument("--db", default="data/db/aidc.duckdb")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once", action="store_true")
    group.add_argument("--daemon", action="store_true")
    args = parser.parse_args()

    if args.once:
        _run_once(args.db)
    else:
        _run_daemon(args.db)


if __name__ == "__main__":
    main()
