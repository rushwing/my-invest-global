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

# Canonical source of stock codes: the YAML pool used by the rest of the agent pipeline.
_STOCKS_YAML = (
    _ROOT / "data" / "agent_input" / "cn" / "stocks.yaml"
    if _ROOT else None
)

# Minimal hardcoded fallback used only when the YAML cannot be loaded
# (e.g. fresh clone before running data setup).
_FALLBACK_CODES = ["688041", "002415", "300308"]


def _load_codes() -> list[str]:
    """
    Load active A-share codes from data/agent_input/cn/stocks.yaml.
    Extracts all ``code:`` entries (must be 6-digit strings).
    Falls back to _FALLBACK_CODES if the file is missing or unreadable.
    """
    if _STOCKS_YAML and _STOCKS_YAML.exists():
        try:
            import re
            text = _STOCKS_YAML.read_text(encoding="utf-8")
            # Match lines like:    code: "300308"  or  code: '300308'
            codes = re.findall(r'^\s+code:\s*["\'](\d{6})["\']', text, re.MULTILINE)
            if codes:
                return list(dict.fromkeys(codes))  # deduplicate, preserve order
        except Exception:
            pass
    return list(_FALLBACK_CODES)


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
        help=(
            "Comma-separated FieldGroup names to fetch "
            "(quote,kline,kline_min,fundamental,segment,fund_flow,shareholder,"
            "announcement,index). Default: all due groups per schedule."
        ),
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

    # Parse --groups into FieldGroup instances; None means "let scheduler decide"
    forced_groups = None
    if args.groups:
        from engine.data_agent.fields import FieldGroup
        valid_values = {g.value for g in FieldGroup}
        parsed = []
        for name in args.groups.split(","):
            name = name.strip()
            if name not in valid_values:
                log.error(
                    "Unknown group %r — valid groups: %s",
                    name, ", ".join(sorted(valid_values)),
                )
                sys.exit(1)
            parsed.append(FieldGroup(name))
        forced_groups = parsed
        log.info("Group override: %s", [g.value for g in forced_groups])

    log.info("Starting data agent: %d codes, poll=%ds, once=%s", len(codes), args.poll, args.once)

    from engine.data_agent.orchestrator import StockDataOrchestrator
    from engine.data_agent.rate_limiter import RateLimiter

    # One shared RateLimiter so all sources and agents share circuit-breaker
    # and backoff state globally (split instances cause domain-level state divergence).
    shared_rl = RateLimiter()

    extra_sources: dict = {}

    # Wire optional sources based on environment
    try:
        from engine.data_agent.sources.akshare import AKShareSource
        extra_sources["akshare"] = AKShareSource(shared_rl)
        log.info("AKShare source enabled")
    except Exception as exc:
        log.warning("AKShare source unavailable: %s", exc)

    try:
        from engine.data_agent.sources.sina import SinaSource
        extra_sources["sina"] = SinaSource(shared_rl)
        log.info("Sina source enabled")
    except Exception as exc:
        log.warning("Sina source unavailable: %s", exc)

    try:
        from engine.data_agent.sources.tushare import TushareSource
        extra_sources["tushare"] = TushareSource(shared_rl)
        log.info("Tushare source enabled")
    except Exception as exc:
        log.warning("Tushare source unavailable: %s", exc)

    try:
        from engine.data_agent.sources.cninfo import CNINFOSource
        extra_sources["cninfo"] = CNINFOSource(shared_rl)
        log.info("CNINFO source enabled")
    except Exception as exc:
        log.warning("CNINFO source unavailable: %s", exc)

    with StockDataOrchestrator.from_defaults(
        codes=codes,
        poll_s=args.poll,
        extra_sources=extra_sources or None,
        rate_limiter=shared_rl,
    ) as orch:
        if args.once:
            summary = orch.run_once(groups=forced_groups)
            log.info("One-shot complete: %s", summary)
            total = sum(summary.values())
            print(f"Fetched {total} rows across {len(summary)} field groups.")
            for group, count in sorted(summary.items()):
                print(f"  {group}: {count} rows")
        else:
            try:
                orch.run_loop(groups=forced_groups)
            except KeyboardInterrupt:
                log.info("Interrupted — shutting down.")


if __name__ == "__main__":
    main()
