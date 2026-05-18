"""IndicatorGroup enum, IndicatorConfig dataclass, and INDICATOR_CONFIGS registry.

Covers ADR-007 Groups I–O (all macro indicator categories).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum

from engine.macro_agent.update_class import UpdateClass

_NY = "America/New_York"
_SH = "Asia/Shanghai"
_TW = "Asia/Taipei"
_KR = "Asia/Seoul"
_UTC = "UTC"

_NYSE_HOURS  = (dt.time(9, 30),  dt.time(16, 0))
_TWSE_HOURS  = (dt.time(9, 0),   dt.time(13, 30))
_KRX_HOURS   = (dt.time(9, 0),   dt.time(15, 30))
_SH_HOURS    = (dt.time(9, 30),  dt.time(15, 0))


class IndicatorGroup(StrEnum):
    MACRO_ECON   = "I"
    COMMODITIES  = "J"
    US_INDICES   = "K"
    CLOUD_CAPEX  = "L"
    APAC_SEMI    = "M"
    CHINA_MARKET = "N"
    GEOPOLITICAL = "O"


@dataclass
class IndicatorConfig:
    indicator_id:   str
    group:          IndicatorGroup
    update_class:   UpdateClass
    primary_source: str
    backups:        list[str]
    market_tz:      str
    session_hours:  tuple[dt.time, dt.time] | None
    poll_interval_s: int
    timeout_s:      int = 20
    cooldown_s:     int = 600

    @property
    def group_code(self) -> str:
        return self.group.value


def _cfg(
    iid: str,
    group: IndicatorGroup,
    uc: UpdateClass,
    primary: str,
    backups: list[str] | None = None,
    tz: str = _NY,
    hours: tuple[dt.time, dt.time] | None = _NYSE_HOURS,
    poll: int = 900,
    **kwargs: int,
) -> IndicatorConfig:
    return IndicatorConfig(
        indicator_id=iid,
        group=group,
        update_class=uc,
        primary_source=primary,
        backups=list(backups) if backups else [],
        market_tz=tz,
        session_hours=hours,
        poll_interval_s=poll,
        **kwargs,
    )


_I = IndicatorGroup.MACRO_ECON
_J = IndicatorGroup.COMMODITIES
_K = IndicatorGroup.US_INDICES
_L = IndicatorGroup.CLOUD_CAPEX
_M = IndicatorGroup.APAC_SEMI
_N = IndicatorGroup.CHINA_MARKET
_O = IndicatorGroup.GEOPOLITICAL

INDICATOR_CONFIGS: dict[str, IndicatorConfig] = {
    # ── Group I — Macro Economy ───────────────────────────────────────────────
    "CPIAUCSL": _cfg("CPIAUCSL", _I, UpdateClass.MONTHLY_FIXED, "fred",
                     backups=["akshare_macro"], hours=None, poll=86400),
    "PPIACO":   _cfg("PPIACO",   _I, UpdateClass.MONTHLY_FIXED, "fred",
                     backups=["akshare_macro"], hours=None, poll=86400),
    "CPI_CHINA": _cfg("CPI_CHINA", _I, UpdateClass.MONTHLY_FIXED, "akshare_macro",
                      backups=["tushare_macro"], tz=_SH, hours=None, poll=86400),
    "PPI_CHINA": _cfg("PPI_CHINA", _I, UpdateClass.MONTHLY_FIXED, "akshare_macro",
                      backups=["tushare_macro"], tz=_SH, hours=None, poll=86400),
    "DFEDTARL": _cfg("DFEDTARL", _I, UpdateClass.EVENT_DRIVEN, "fred",
                     hours=None, poll=86400),
    "DFEDTARU": _cfg("DFEDTARU", _I, UpdateClass.EVENT_DRIVEN, "fred",
                     hours=None, poll=86400),

    # ── Group J — Commodities ─────────────────────────────────────────────────
    "BZ=F": _cfg("BZ=F", _J, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                 hours=None, poll=900),
    "CL=F": _cfg("CL=F", _J, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                 hours=None, poll=900),
    "XLU":  _cfg("XLU",  _J, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                 hours=_NYSE_HOURS, poll=900),

    # ── Group K — US Key Indices / Equities ───────────────────────────────────
    "^SOX":     _cfg("^SOX",     _K, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                     hours=_NYSE_HOURS, poll=900),
    "^IXIC":    _cfg("^IXIC",    _K, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                     hours=_NYSE_HOURS, poll=900),
    "^NDX":     _cfg("^NDX",     _K, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                     hours=_NYSE_HOURS, poll=900),
    "^GSPC":    _cfg("^GSPC",    _K, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                     hours=_NYSE_HOURS, poll=900),
    "DX-Y.NYB": _cfg("DX-Y.NYB", _K, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                     hours=None, poll=900),
    "DGS10":    _cfg("DGS10",    _K, UpdateClass.DAILY, "fred",
                     hours=None, poll=86400),
    "DGS2":     _cfg("DGS2",     _K, UpdateClass.DAILY, "fred",
                     hours=None, poll=86400),
    "NVDA":     _cfg("NVDA",     _K, UpdateClass.INTRADAY_FAST, "yahoo_global",
                     hours=_NYSE_HOURS, poll=60),
    "MSFT":     _cfg("MSFT",     _K, UpdateClass.INTRADAY_FAST, "yahoo_global",
                     hours=_NYSE_HOURS, poll=60),
    "AVGO":     _cfg("AVGO",     _K, UpdateClass.INTRADAY_FAST, "yahoo_global",
                     hours=_NYSE_HOURS, poll=60),
    "ANET":     _cfg("ANET",     _K, UpdateClass.INTRADAY_FAST, "yahoo_global",
                     hours=_NYSE_HOURS, poll=60),
    "VRT":      _cfg("VRT",      _K, UpdateClass.INTRADAY_FAST, "yahoo_global",
                     hours=_NYSE_HOURS, poll=60),

    # ── Group L — Cloud Giant Quarterly CapEx ─────────────────────────────────
    "MSFT_CAPEX":  _cfg("MSFT_CAPEX",  _L, UpdateClass.QUARTERLY, "sec_edgar",
                        backups=["yahoo_global"], hours=None, poll=86400 * 75),
    "AMZN_CAPEX":  _cfg("AMZN_CAPEX",  _L, UpdateClass.QUARTERLY, "sec_edgar",
                        backups=["yahoo_global"], hours=None, poll=86400 * 75),
    "GOOGL_CAPEX": _cfg("GOOGL_CAPEX", _L, UpdateClass.QUARTERLY, "sec_edgar",
                        backups=["yahoo_global"], hours=None, poll=86400 * 75),
    "META_CAPEX":  _cfg("META_CAPEX",  _L, UpdateClass.QUARTERLY, "sec_edgar",
                        backups=["yahoo_global"], hours=None, poll=86400 * 75),

    # ── Group M — APAC Semiconductors ─────────────────────────────────────────
    "SOXX":     _cfg("SOXX",      _M, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                     hours=_NYSE_HOURS, poll=900),
    "^TWII":    _cfg("^TWII",     _M, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                     tz=_TW, hours=_TWSE_HOURS, poll=900),
    "TSM":      _cfg("TSM",       _M, UpdateClass.INTRADAY_SLOW, "yahoo_global",
                     tz=_TW, hours=_TWSE_HOURS, poll=900),
    "005930.KS":_cfg("005930.KS", _M, UpdateClass.DAILY, "yahoo_global",
                     tz=_KR, hours=_KRX_HOURS, poll=86400),
    "KRX_SEMI": _cfg("KRX_SEMI",  _M, UpdateClass.DAILY, "yahoo_global",
                     tz=_KR, hours=_KRX_HOURS, poll=86400),

    # ── Group N — China Market ────────────────────────────────────────────────
    "SGX_A50":         _cfg("SGX_A50",         _N, UpdateClass.INTRADAY_FAST, "akshare_macro",
                            tz=_SH, hours=_SH_HOURS, poll=60),
    "000688.SH":       _cfg("000688.SH",       _N, UpdateClass.INTRADAY_FAST, "akshare_macro",
                            tz=_SH, hours=_SH_HOURS, poll=60),
    "USDCNH":          _cfg("USDCNH",          _N, UpdateClass.INTRADAY_SLOW, "akshare_macro",
                            backups=["tushare_macro"], tz=_SH, hours=None, poll=900),
    "USDCNY":          _cfg("USDCNY",          _N, UpdateClass.INTRADAY_SLOW, "akshare_macro",
                            backups=["tushare_macro"], tz=_SH, hours=None, poll=900),
    "GREEN_ENERGY":    _cfg("GREEN_ENERGY",    _N, UpdateClass.DAILY, "akshare_macro",
                            tz=_SH, hours=_SH_HOURS, poll=86400),
    "A_SHARE_TURNOVER":_cfg("A_SHARE_TURNOVER",_N, UpdateClass.INTRADAY_SLOW, "akshare_macro",
                            tz=_SH, hours=_SH_HOURS, poll=900),

    # ── Group O — Geopolitical / News Sentiment ───────────────────────────────
    "CLS_NEWS":    _cfg("CLS_NEWS",    _O, UpdateClass.INTRADAY_SLOW, "akshare_macro",
                        tz=_SH, hours=None, poll=1800),
    "AV_SENTIMENT":_cfg("AV_SENTIMENT",_O, UpdateClass.INTRADAY_SLOW, "alpha_vantage",
                        tz=_UTC, hours=None, poll=1800),
}
