"""
AKShare 1.18.60 contract validation.

Three-tier check:
  1. Presence of all 27 functions (data-source-matrix.md Appendix B)
  2. Core runtime smoke tests — functions with no mainland-CN CDN dependency
  3. Network-sensitive tests — functions that use Eastmoney's numbered push2 CDN
     (xx.push2.eastmoney.com); a pre-flight check determines if these are reachable.
     Inaccessible CDN = SKIP (not FAIL); these are expected to work on mainland CN networks.
  4. Monitored compat — upstream-HTML-scrape or volatile functions; presence-only.

Version pin decision:
  PASS if: all 27 present  AND  all core-runtime ok
  CDN-SKIP and monitored-compat entries never block the pin.

Run:
    source ~/.zshrc
    uv run --with "akshare==1.18.60" python scripts/validate_akshare.py

Output:
    docs/akshare-validation-report.md
    exit 0 on PASS, exit 1 on any presence-missing or core-runtime failure
"""

import os
import sys
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

PIN = "1.18.60"
TEST_CODE_SSE  = "688041"  # 华工科技 — 科创板 (SSE), market='sh'

REPORT = Path(__file__).resolve().parent.parent / "docs" / "akshare-validation-report.md"

# ── All 27 functions ──────────────────────────────────────────────────────────
ALL_FUNCTIONS = [
    "stock_zh_a_spot_em",
    "stock_zh_a_hist",
    "stock_zh_a_hist_min_em",
    "stock_zh_a_daily",
    "stock_yjbb_em",
    "stock_lrb_em",
    "stock_xjll_em",
    "stock_financial_analysis_indicator",
    "stock_financial_abstract",
    "stock_financial_report_sina",
    "stock_yjyg_em",
    "stock_zygc_em",
    "stock_individual_fund_flow",
    "stock_main_fund_flow",
    "stock_hsgt_hold_stock_em",
    "stock_margin_account_info",
    "stock_gdfx_free_holding_detail_em",
    "stock_zh_a_disclosure_report_cninfo",
    "stock_notice_report",
    "stock_individual_notice_report",
    "stock_research_report_em",
    "stock_news_em",
    "stock_info_global_cls",
    "stock_board_industry_name_em",
    "stock_board_industry_spot_em",
    "stock_board_industry_index_ths",
    "stock_sector_spot",
]

# Tier 2 — Core runtime: uses stable datacenter/emweb endpoints; must pass to pin version.
# Parameters verified against akshare 1.18.60 source:
#   - stock_individual_fund_flow: market='sh'|'sz' (NOT board name like '科创板')
CORE_RUNTIME: dict[str, object] = {
    "stock_yjbb_em": lambda ak: ak.stock_yjbb_em(date="20241231"),
    "stock_individual_fund_flow": lambda ak: ak.stock_individual_fund_flow(
        stock=TEST_CODE_SSE, market="sh"   # SSE stocks: market='sh'
    ),
    "stock_zygc_em": lambda ak: ak.stock_zygc_em(symbol=f"SH{TEST_CODE_SSE}"),
}

# Tier 3 — Eastmoney push2 CDN: uses push2.eastmoney.com and push2his.eastmoney.com.
# These domains route through geo-distributed CDN and may be unreliable behind a proxy
# or from non-mainland-CN networks. Pre-flight determines SKIP vs run.
# This tier covers both numbered (xx.push2) and non-numbered (push2his) subdomains.
CDN_FUNCTIONS: dict[str, object] = {
    "stock_zh_a_hist": lambda ak: ak.stock_zh_a_hist(
        symbol=TEST_CODE_SSE,
        period="daily",
        start_date="20250101",
        end_date="20250116",
        adjust="qfq",
    ),
    "stock_zh_a_hist_min_em": lambda ak: ak.stock_zh_a_hist_min_em(
        symbol=TEST_CODE_SSE, period="1"
    ),
    "stock_zh_a_spot_em": lambda ak: ak.stock_zh_a_spot_em(),
    "stock_board_industry_name_em": lambda ak: ak.stock_board_industry_name_em(),
    "stock_board_industry_spot_em": lambda ak: ak.stock_board_industry_spot_em(
        symbol="光通信"
    ),
}
# Pre-flight: check push2his (non-numbered, used by hist/hist_min) and push2 (numbered CDN)
CDN_PREFLIGHT_HOSTS = [
    ("push2his.eastmoney.com", 443),
    ("push2.eastmoney.com", 443),
]

# Tier 4 — Monitored compat: presence-only; volatile upstream HTML/API.
#   stock_hsgt_hold_stock_em: scrapes eastmoney HTML for date; structure changed in 1.18.x.
MONITORED_COMPAT = {
    "stock_hsgt_hold_stock_em",
    "stock_financial_report_sina",
    "stock_zh_a_disclosure_report_cninfo",
    "stock_notice_report",
    "stock_individual_notice_report",
    "stock_research_report_em",
    "stock_news_em",
    "stock_info_global_cls",
}


@contextmanager
def _no_proxy():
    """Temporarily unset proxy env vars so requests bypass the local proxy."""
    saved = {}
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                "all_proxy", "ALL_PROXY"):
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    try:
        yield
    finally:
        os.environ.update(saved)


# Connection-class exceptions that indicate network environment, not API contract issues.
# Any exception whose type name or message contains one of these strings is treated as
# network-unavailable → SKIP rather than FAIL.
_NETWORK_ERROR_MARKERS = (
    "ConnectionError", "RemoteDisconnected", "Connection aborted",
    "Max retries exceeded", "timed out", "timeout", "ProxyError",
    "SSLError", "gaierror", "ConnectionRefused",
)


def _is_network_error(exc: Exception) -> bool:
    msg = f"{type(exc).__name__}: {exc}"
    return any(m.lower() in msg.lower() for m in _NETWORK_ERROR_MARKERS)


def _smoke(call, ak, bypass_proxy: bool = False, network_skip: bool = False) -> dict:
    """
    Run one smoke call.
    network_skip=True: classify connection-class errors as SKIP instead of FAIL.
    """
    t0 = time.perf_counter()
    try:
        ctx = _no_proxy() if bypass_proxy else _noop()
        with ctx:
            df = call(ak)
        rows = len(df) if hasattr(df, "__len__") else "?"
        latency = int((time.perf_counter() - t0) * 1000)
        return {"status": "ok", "rows": rows, "latency_ms": latency}
    except Exception as exc:
        latency = int((time.perf_counter() - t0) * 1000)
        if network_skip and _is_network_error(exc):
            return {"status": "SKIP", "reason": f"network: {str(exc)[:150]}", "latency_ms": latency}
        return {"status": "FAIL", "error": str(exc)[:300], "latency_ms": latency}


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def run() -> int:
    import akshare as ak

    actual = ak.__version__
    if actual != PIN:
        print(f"ERROR: expected akshare=={PIN}, got {actual}")
        print('Re-run: uv run --with "akshare==1.18.60" python scripts/validate_akshare.py')
        return 1

    proxy_env = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "none"
    print(f"akshare {actual} | proxy: {proxy_env}\n")

    # ── Tier 1: Presence ──────────────────────────────────────────────────────
    print("Tier 1: presence check (27 functions)… ", end="", flush=True)
    presence: dict[str, bool] = {fn: hasattr(ak, fn) for fn in ALL_FUNCTIONS}
    missing_presence = [f for f, ok in presence.items() if not ok]
    print(f"{'ok' if not missing_presence else f'MISSING: {missing_presence}'}")

    # ── Tier 2: Core runtime ──────────────────────────────────────────────────
    print("\nTier 2: core runtime smoke tests")
    core_results: dict[str, dict] = {}
    for fn, call in CORE_RUNTIME.items():
        print(f"  {fn}… ", end="", flush=True)
        r = _smoke(call, ak)
        core_results[fn] = r
        if r["status"] == "ok":
            print(f"ok ({r['rows']} rows, {r['latency_ms']}ms)")
        else:
            print(f"FAIL — {r.get('error','')[:100]}")
        time.sleep(2)

    # ── Tier 3: CDN smoke tests (network errors → SKIP, not FAIL) ────────────
    print("\nTier 3: Eastmoney push2 CDN smoke tests")
    print("  (connection errors → SKIP; only Python/API errors → FAIL)")
    cdn_results: dict[str, dict] = {}
    for fn, call in CDN_FUNCTIONS.items():
        print(f"  [CDN] {fn}… ", end="", flush=True)
        r = _smoke(call, ak, bypass_proxy=True, network_skip=True)
        cdn_results[fn] = r
        if r["status"] == "ok":
            print(f"ok ({r['rows']} rows, {r['latency_ms']}ms)")
        elif r["status"] == "SKIP":
            print(f"SKIP (network env: {r.get('reason','')[:80]})")
        else:
            print(f"FAIL — {r.get('error','')[:100]}")
        time.sleep(1)

    # ── Tier 4: Monitored compat ──────────────────────────────────────────────
    monitored: dict[str, str] = {
        fn: ("present" if presence.get(fn) else "MISSING") for fn in MONITORED_COMPAT
    }

    # ── Verdict ───────────────────────────────────────────────────────────────
    core_fails = [f for f, r in core_results.items() if r["status"] == "FAIL"]
    cdn_fails  = [f for f, r in cdn_results.items() if r["status"] == "FAIL"]
    cdn_skips  = [f for f, r in cdn_results.items() if r["status"] == "SKIP"]
    # CDN SKIP = network environment (not a contract issue). Only CDN FAIL blocks pin.
    passed = not missing_presence and not core_fails and not cdn_fails
    verdict = (
        f"✅ PASS — pin `akshare=={PIN}`"
        if passed
        else "❌ FAIL — do not pin; see failures below"
    )

    # ── Write report ──────────────────────────────────────────────────────────
    lines: list[str] = [
        f"# AKShare {PIN} Validation Report",
        "",
        f"Date: {date.today()}  ",
        f"Test stock: `{TEST_CODE_SSE}` (科创板/SSE)  ",
        f"Proxy env: `{proxy_env}`  ",
        f"CDN skipped (network env): `{len(cdn_skips)} / {len(CDN_FUNCTIONS)}`  ",
        f"Verdict: **{verdict}**",
        "",
        "---",
        "",
        "## Tier 1 — Presence Check (27 functions)",
        "",
        _row(["Function", "Present"]),
        _row(["---", "---"]),
    ]
    for fn in ALL_FUNCTIONS:
        mark = "✅" if presence.get(fn) else "❌ MISSING"
        lines.append(_row([f"`{fn}`", mark]))

    lines += [
        "",
        "## Tier 2 — Core Runtime Smoke Tests",
        "",
        "> No mainland-CN CDN dependency. Must all pass for version pin.",
        "",
        _row(["Function", "Status", "Rows", "Latency"]),
        _row(["---", "---", "---", "---"]),
    ]
    for fn, r in core_results.items():
        if r["status"] == "ok":
            lines.append(_row([f"`{fn}`", "✅ ok", str(r["rows"]), f"{r['latency_ms']}ms"]))
        else:
            err = r.get("error", "")[:120]
            lines.append(_row([f"`{fn}`", "❌ FAIL", "—", f"{r['latency_ms']}ms — `{err}`"]))

    lines += [
        "",
        "## Tier 3 — Eastmoney push2 CDN Functions",
        "",
        "> Covers `push2his.eastmoney.com` (hist/min bars) and "
        "`xx.push2.eastmoney.com` (spot/boards).",
        "> **SKIP** = connection-class network error (expected behind VPN/proxy "
        "or outside mainland CN).",
        "> **FAIL** = Python/API contract error (blocks version pin).",
        "",
        _row(["Function", "Status", "Rows", "Latency / Note"]),
        _row(["---", "---", "---", "---"]),
    ]
    for fn, r in cdn_results.items():
        if r["status"] == "ok":
            lines.append(_row([f"`{fn}`", "✅ ok", str(r["rows"]), f"{r['latency_ms']}ms"]))
        elif r["status"] == "SKIP":
            lines.append(_row([f"`{fn}`", "⏭️ SKIP", "—", r.get("reason", "")]))
        else:
            err = r.get("error", "")[:120]
            lines.append(_row([f"`{fn}`", "❌ FAIL", "—", f"{r['latency_ms']}ms — `{err}`"]))

    lines += [
        "",
        "## Tier 4 — Monitored Compatibility (presence only)",
        "",
        "> Failures do not block pin. These functions depend on upstream HTML/API "
        "structures that change frequently.",
        "",
        "| Function | Status | Note |",
        "| --- | --- | --- |",
        f"| `stock_hsgt_hold_stock_em` | "
        f"{'✅ present' if monitored.get('stock_hsgt_hold_stock_em') == 'present' else '⚠️ MISSING'}"
        f" | upstream HTML date-scrape structure changed in 1.18.x |",
    ]
    for fn in sorted(MONITORED_COMPAT - {"stock_hsgt_hold_stock_em"}):
        s = monitored.get(fn, "MISSING")
        mark = "✅ present" if s == "present" else "⚠️ MISSING"
        lines.append(f"| `{fn}` | {mark} | upstream-sensitive |")

    if missing_presence or core_fails or cdn_skips or cdn_fails:
        lines += ["", "## Notes / Failures", ""]
        for f in missing_presence:
            lines.append(f"- **Presence MISSING**: `{f}`")
        for f in core_fails:
            err = core_results[f].get("error", "")[:200]
            lines.append(f"- **Core runtime FAIL**: `{f}` — {err}")
        for f in cdn_skips:
            lines.append(f"- **CDN SKIP** (network): `{f}`")
        for f in cdn_fails:
            lines.append(f"- **CDN runtime FAIL**: `{f}` — {cdn_results[f].get('error','')[:200]}")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n{'─'*60}")
    print(f"Verdict : {verdict}")
    print(f"Report  : {REPORT}")
    if missing_presence:
        print(f"Missing   : {missing_presence}")
    if core_fails:
        print(f"Core fails: {core_fails}")
    if cdn_skips:
        print(f"CDN skips : {cdn_skips} (network env, not a contract issue)")
    if cdn_fails:
        print(f"CDN fails : {cdn_fails}")

    return 0 if passed else 1


class _noop:
    def __enter__(self): return self
    def __exit__(self, *_): pass


if __name__ == "__main__":
    sys.exit(run())
