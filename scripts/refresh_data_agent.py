"""
CLI entry point for the stock data refresh agent.

Usage:
    uv run refresh-data-agent                    # loop forever with all defaults
    uv run refresh-data-agent --once             # one cycle, then exit
    uv run refresh-data-agent --groups quote,kline --codes 688041,002415
    uv run refresh-data-agent --poll 60          # poll every 60 seconds

Environment:
    TUSHARE_TOKEN  — required when tushare source is active (fundamental/shareholder)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when called directly
_ROOT = next(
    (p for p in Path(__file__).resolve().parents if (p / ".git").exists()),
    None,
)
if _ROOT and str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Default A-share AIDC pool (matches codes tracked in aidc_report.html)
DEFAULT_CODES = [
    # Core AIDC semiconductor & equipment
    "688041",  # 华工科技
    "688041",  # placeholder — replace with full pool from stock_codes.py
]


def _load_codes() -> list[str]:
    """Load codes from project stock list, falling back to DEFAULT_CODES."""
    try:
        from app.stock_codes import STOCK_CODES  # type: ignore[import]
        return [c for c in STOCK_CODES if c.isdigit() and len(c) == 6]
    except ImportError:
        return DEFAULT_CODES


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Stock data refresh agent — multi-source, rate-limited"
    )
    p.add_argument(
        "--codes",
        metavar="CODE,...",
        help="Comma-separated 6-digit stock codes (default: full AIDC pool)",
    )
    p.add_argument(
        "--groups",
        metavar="GROUP,...",
        help="Comma-separated FieldGroup names to fetch "
             "(quote,kline,kline_min,fundamental,segment,fund_flow,shareholder,announcement,index). "
             "Default: all due groups per schedule.",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run one cycle and exit (default: loop forever)",
    )
    p.add_argument(
        "--poll",
        metavar="SECONDS",
        type=int,
        default=30,
        help="Polling interval in seconds for loop mode (default: 30)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    log = logging.getLogger("refresh_data_agent")

    codes = [c.strip() for c in args.codes.split(",")] if args.codes else _load_codes()
    codes = list(dict.fromkeys(c for c in codes if c))  # deduplicate, preserve order

    if not codes:
        log.error("No stock codes provided and default pool is empty.")
        sys.exit(1)

    log.info("Starting data agent: %d codes, poll=%ds, once=%s", len(codes), args.poll, args.once)

    from engine.data_agent.orchestrator import StockDataOrchestrator

    extra_sources: dict = {}

    # Wire optional sources based on environment
    try:
        from engine.data_agent.sources.akshare import AKShareSource
        from engine.data_agent.rate_limiter import RateLimiter
        _rl = RateLimiter()
        extra_sources["akshare"] = AKShareSource(_rl)
        log.info("AKShare source enabled")
    except Exception as exc:
        log.warning("AKShare source unavailable: %s", exc)

    try:
        from engine.data_agent.sources.sina import SinaSource
        from engine.data_agent.rate_limiter import RateLimiter as _RL
        _rl2 = _RL()
        extra_sources["sina"] = SinaSource(_rl2)
        log.info("Sina source enabled")
    except Exception as exc:
        log.warning("Sina source unavailable: %s", exc)

    try:
        from engine.data_agent.sources.tushare import TushareSource
        from engine.data_agent.rate_limiter import RateLimiter as _RL3
        _rl3 = _RL3()
        extra_sources["tushare"] = TushareSource(_rl3)
        log.info("Tushare source enabled")
    except Exception as exc:
        log.warning("Tushare source unavailable: %s", exc)

    try:
        from engine.data_agent.sources.cninfo import CNINFOSource
        from engine.data_agent.rate_limiter import RateLimiter as _RL4
        _rl4 = _RL4()
        extra_sources["cninfo"] = CNINFOSource(_rl4)
        log.info("CNINFO source enabled")
    except Exception as exc:
        log.warning("CNINFO source unavailable: %s", exc)

    with StockDataOrchestrator.from_defaults(
        codes=codes,
        poll_s=args.poll,
        extra_sources=extra_sources or None,
    ) as orch:
        if args.once:
            summary = orch.run_once()
            log.info("One-shot complete: %s", summary)
            total = sum(summary.values())
            print(f"Fetched {total} rows across {len(summary)} field groups.")
            for group, count in sorted(summary.items()):
                print(f"  {group}: {count} rows")
        else:
            try:
                orch.run_loop()
            except KeyboardInterrupt:
                log.info("Interrupted — shutting down.")


if __name__ == "__main__":
    main()
