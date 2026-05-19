"""E2E smoke test for the Phase 9 analysis pipeline.

Usage:
    uv run python -m scripts.e2e_test             # dry-run: mock LLM, no API key needed
    uv run python -m scripts.e2e_test --live       # real Claude API, real DuckDB
    uv run python -m scripts.e2e_test --db PATH    # custom DuckDB path (default: /tmp)
"""
from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ── ANSI colours ──────────────────────────────────────────────────────────────
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"  {_GREEN}✓{_RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"  {_RED}✗{_RESET} {msg}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}⚠{_RESET} {msg}")


def _section(title: str) -> None:
    print(f"\n{_BOLD}{_CYAN}── {title} {'─' * (50 - len(title))}{_RESET}")


# ── Mock LLM ──────────────────────────────────────────────────────────────────

class _MockMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _MockLLM:
    """Returns a minimal valid StockSignal JSON array for each holding."""

    def invoke(self, messages: list[Any]) -> _MockMessage:
        import re
        user_text = messages[-1].content if messages else ""
        # Parse "--- code name (category) ---" lines from new prompt format
        codes = re.findall(r"---\s+(\d{6})\s+(.+?)\s+\((.+?)\)\s+---", user_text)
        if not codes:
            codes = [("000000", "Mock股票", "弹性股")]

        signals = [
            {
                "code": code,
                "name": name,
                "category": cat,
                "technical_score": 60.0,
                "fundamental_score": 65.0,
                "sentiment_score": 55.0,
                "composite_score": 60.0,
                "action": "持有观望（模拟信号）",
                "action_code": "hold",
                "reasoning": "dry-run mock — no real analysis performed",
                "signals": {},
            }
            for code, name, cat in codes
        ]
        return _MockMessage(json.dumps(signals, ensure_ascii=False))


# ── Test steps ────────────────────────────────────────────────────────────────

@dataclass
class _Result:
    passed: int = 0
    failed: int = 0

    def record(self, ok: bool, msg_ok: str, msg_fail: str) -> None:
        if ok:
            _ok(msg_ok)
            self.passed += 1
        else:
            _fail(msg_fail)
            self.failed += 1


def _step_holdings(res: _Result) -> Any:
    _section("Step 1 — holdings.yaml")
    from engine.portfolio import load_holdings
    holdings = load_holdings()
    res.record(len(holdings) > 0, f"Loaded {len(holdings)} holdings", "holdings.yaml missing or empty")
    if holdings:
        for h in holdings:
            _ok(f"  {h.code}  {h.name:<8}  {h.category}  ¥{h.market_value:>10,.0f}")
    return holdings


def _step_snapshot(holdings: list[Any], res: _Result) -> Any:
    _section("Step 2 — build_snapshot")
    from engine.agent.state import build_snapshot
    snap = build_snapshot()
    res.record(
        len(snap.holdings) == len(holdings),
        f"Snapshot built: session={snap.session_id[:8]}…  macro={snap.macro_state}",
        "build_snapshot failed or holding count mismatch",
    )
    total_mv = sum(snap.price_snapshot[c] * 0 + v
                   for c, v in snap.price_snapshot.items())
    _ok(f"  price_snapshot: {len(snap.price_snapshot)} codes")
    return snap


def _step_run_analysis(snap: Any, live: bool, res: _Result) -> Any:
    _section(f"Step 3 — run_analysis ({'live Claude API' if live else 'mock LLM'})")
    from engine.agent.runner import run_analysis
    llm = None if live else _MockLLM()  # type: ignore[arg-type]
    t0 = time.monotonic()
    state = run_analysis(snap, llm=llm)  # type: ignore[arg-type]
    elapsed = time.monotonic() - t0

    res.record(
        len(state["signals"]) > 0,
        f"Got {len(state['signals'])} signals in {elapsed:.1f}s",
        f"No signals returned  errors={state['errors']}",
    )
    if state["errors"]:
        for e in state["errors"]:
            _warn(f"  pipeline error: {e}")
    return state


def _step_print_signals(state: Any) -> None:
    _section("Step 4 — signal summary")
    signals = state["signals"]
    reasoning = state["reasoning"]
    if not signals:
        _warn("No signals to display")
        return
    header = f"  {'代码':6}  {'名称':8}  {'分类':4}  {'综合':>4}  {'建议':<16}"
    print(header)
    print("  " + "─" * (len(header) - 2))
    for sig in signals:
        r = reasoning.get(sig.code, "")
        line = (f"  {sig.code}  {sig.name:<8}  {sig.category:<4}  "
                f"{sig.composite_score:>4.0f}  {sig.action_code:<16}")
        print(line)
        if r and r != "dry-run mock — no real analysis performed":
            wrapped = textwrap.fill(r, width=72, initial_indent="         ", subsequent_indent="         ")
            print(f"{_CYAN}{wrapped}{_RESET}")


def _step_session_store(state: Any, db_path: str, res: _Result) -> None:
    _section("Step 5 — session_store save/load round-trip")
    from engine.agent.session_store import load_latest_session, save_session
    save_session(db_path, state)
    _ok(f"save_session → {db_path}")
    loaded = load_latest_session(db_path)
    res.record(
        loaded is not None and loaded["session_id"] == state["session_id"],
        f"load_latest_session round-trip OK  session={state['session_id'][:8]}…",
        "load_latest_session returned None or mismatched session_id",
    )
    if loaded:
        res.record(
            len(loaded["signals"]) == len(state["signals"]),
            f"Signal count preserved: {len(loaded['signals'])}",
            f"Signal count mismatch: saved={len(state['signals'])} loaded={len(loaded['signals'])}",
        )


def _print_summary(res: _Result, db_path: str) -> None:
    _section("Summary")
    total = res.passed + res.failed
    colour = _GREEN if res.failed == 0 else _RED
    print(f"  {colour}{_BOLD}{res.passed}/{total} checks passed{_RESET}")
    print(f"  DuckDB: {db_path}")
    if res.failed > 0:
        print(f"\n  {_RED}Some checks failed — see ✗ lines above.{_RESET}")
        sys.exit(1)
    else:
        print(f"\n  {_GREEN}All checks passed.{_RESET}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 9 E2E smoke test")
    parser.add_argument("--live", action="store_true", help="Use real Claude API")
    parser.add_argument("--db", default="", help="DuckDB path (default: temp file)")
    args = parser.parse_args()

    mode = "LIVE" if args.live else "DRY-RUN"
    print(f"\n{_BOLD}Phase 9 E2E Smoke Test  [{mode}]{_RESET}")
    print(f"Holdings: {Path('data/agent_input/cn/holdings.yaml').resolve()}")

    # Resolve DB path
    _tmp_dir = None
    if args.db:
        db_path = args.db
    else:
        _tmp_dir = tempfile.mkdtemp(prefix="e2e_phase9_")
        db_path = str(Path(_tmp_dir) / "test.duckdb")

    res = _Result()

    holdings = _step_holdings(res)
    if not holdings:
        _fail("Aborting — cannot proceed without holdings")
        sys.exit(1)

    snap = _step_snapshot(holdings, res)
    state = _step_run_analysis(snap, live=args.live, res=res)
    _step_print_signals(state)
    _step_session_store(state, db_path, res)
    _print_summary(res, db_path)


if __name__ == "__main__":
    main()
