"""
Field group definitions, source priority policies, and retry configuration.

Every data field the agent can fetch belongs to a FieldGroup. Each group has a
SourcePolicy that declares which source to try first and which to fall back to.
"""

from dataclasses import dataclass, field
from enum import Enum


class FieldGroup(str, Enum):
    QUOTE        = "quote"        # real-time price, volume, PE, market cap
    KLINE        = "kline"        # daily/weekly/monthly OHLCV + adj_factor
    KLINE_MIN    = "kline_min"    # 1-min intraday OHLCV
    FUNDAMENTAL  = "fundamental"  # quarterly/annual income, balance, cashflow
    SEGMENT      = "segment"      # 主营构成 by product line
    FUND_FLOW    = "fund_flow"    # 主力净流入, northbound, margin
    SHAREHOLDER  = "shareholder"  # top-10 holders, institutional %, lockup schedule
    ANNOUNCEMENT = "announcement" # 公告, 研报, news summaries
    INDEX        = "index"        # 上证综指, 深成指, 申万行业


@dataclass
class SourcePolicy:
    """Retrieval policy for one FieldGroup: source priority + retry/backoff config."""

    primary: str
    backups: list[str] = field(default_factory=list)
    timeout_s: int = 20
    retries: int = 3
    backoff_base_s: float = 1.0   # first retry delay; doubles each attempt
    circuit_break_after: int = 3  # consecutive failures before circuit opens
    cooldown_s: int = 600         # circuit-open cooldown (10 min default)


# Primary source selection rationale (from docs/data-source-matrix.md):
#   QUOTE       — Tencent qt.gtimg.cn: free, fast, batch-40; EM push2 as backup
#   KLINE       — Tencent ifzq (existing code); akshare/tushare as backups
#   KLINE_MIN   — EM push2his; akshare wraps same; tencent as last resort
#   FUNDAMENTAL — Tushare: stable, structured; EM datacenter; akshare wrappers
#   SEGMENT     — EM F10 (existing code); akshare stock_zygc_em; tushare fina_mainbz
#   FUND_FLOW   — EM datacenter zjlx; akshare wrappers; tushare moneyflow_dc
#   SHAREHOLDER — Tushare top10_floatholders; EM gdfx; akshare wrappers
#   ANNOUNCEMENT— CNINFO (法定披露); akshare cninfo wrappers; EM public notices
#   INDEX       — Tencent (same as QUOTE path); sina hq.sinajs.cn; EM push2
FIELD_POLICIES: dict[FieldGroup, SourcePolicy] = {
    FieldGroup.QUOTE: SourcePolicy(
        primary="tencent",
        backups=["eastmoney", "sina"],
    ),
    FieldGroup.KLINE: SourcePolicy(
        primary="tencent",
        backups=["akshare", "tushare"],
    ),
    FieldGroup.KLINE_MIN: SourcePolicy(
        primary="eastmoney",
        backups=["akshare", "tencent"],
        cooldown_s=300,  # shorter cooldown; intraday data has limited retry window
    ),
    FieldGroup.FUNDAMENTAL: SourcePolicy(
        primary="tushare",
        backups=["eastmoney", "akshare"],
        timeout_s=30,
        cooldown_s=1800,  # fundamentals are non-urgent; longer cooldown is fine
    ),
    FieldGroup.SEGMENT: SourcePolicy(
        primary="eastmoney",
        backups=["akshare", "tushare"],
        cooldown_s=1800,
    ),
    FieldGroup.FUND_FLOW: SourcePolicy(
        primary="eastmoney",
        backups=["akshare", "tushare"],
    ),
    FieldGroup.SHAREHOLDER: SourcePolicy(
        primary="tushare",
        backups=["eastmoney", "akshare"],
        cooldown_s=3600,
    ),
    FieldGroup.ANNOUNCEMENT: SourcePolicy(
        primary="cninfo",
        backups=["akshare", "eastmoney"],
        timeout_s=30,
        cooldown_s=1800,
    ),
    FieldGroup.INDEX: SourcePolicy(
        primary="tencent",
        backups=["sina", "eastmoney"],
    ),
}

# Sources that use async parallel fetching (fast_agent).
# Everything else goes through slow_agent (serial + anti-blacklist delays).
FAST_SOURCES: frozenset[str] = frozenset({"tencent", "sina", "yahoo"})

# Maps each FieldGroup to the source method name the agents should call.
GROUP_DISPATCH: dict[FieldGroup, str] = {
    FieldGroup.QUOTE:        "fetch_quotes",
    FieldGroup.KLINE:        "fetch_kline_day",
    FieldGroup.KLINE_MIN:    "fetch_kline_min",
    FieldGroup.FUNDAMENTAL:  "fetch_fundamentals",
    FieldGroup.SEGMENT:      "fetch_business_segments",
    FieldGroup.FUND_FLOW:    "fetch_fund_flow",
    FieldGroup.SHAREHOLDER:  "fetch_shareholders",
    FieldGroup.ANNOUNCEMENT: "fetch_announcements",
    FieldGroup.INDEX:        "fetch_quotes",
}

# FieldGroups whose dispatch method is called once per code (code: str) rather
# than once for the whole batch (codes: list[str]).
GROUP_PER_CODE: frozenset[FieldGroup] = frozenset({
    FieldGroup.KLINE,
    FieldGroup.KLINE_MIN,
    FieldGroup.FUNDAMENTAL,
    FieldGroup.SEGMENT,
    FieldGroup.FUND_FLOW,
    FieldGroup.SHAREHOLDER,
    FieldGroup.ANNOUNCEMENT,
})
