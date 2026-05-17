"""TC-011-01..07 — MacroRegime gate computation and write_cache."""

from __future__ import annotations

import datetime as dt
import json
from unittest.mock import patch

import pytest

from engine.macro_agent.storage import MacroStorage

_regime_mod = pytest.importorskip(
    "engine.macro_agent.regime",
    reason="MacroRegime not yet implemented (pending req_impl)",
)
MacroRegime = _regime_mod.MacroRegime

_NOW_UTC = dt.datetime(2026, 5, 17, 14, 0, tzinfo=dt.UTC)
_TODAY = _NOW_UTC.date()
_AS_OF = dt.date(2026, 5, 15)


@pytest.fixture
def mem_store():
    s = MacroStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def regime(mem_store):
    return MacroRegime(storage=mem_store)


def _seed_capex(store, big4_qoq_pct: float) -> None:
    """Seed capex_quarterly so Big-4 avg QoQ == big4_qoq_pct."""
    companies = [("MSFT", "0000789019"), ("AMZN", "0001018724"),
                 ("GOOGL", "0001652044"), ("META", "0001326801")]
    base_q = dt.date(2026, 3, 31)  # current quarter
    prev_q = dt.date(2025, 12, 31)  # prior quarter
    prev_capex = 10.0  # arbitrary baseline
    cur_capex = prev_capex * (1 + big4_qoq_pct / 100)
    now_utc = dt.datetime.now(tz=dt.UTC)
    for company, cik in companies:
        for fq, period, capex in [("2025Q4", prev_q, prev_capex), ("2026Q1", base_q, cur_capex)]:
            store.upsert_capex([{
                "company": company, "cik": cik, "fiscal_quarter": fq,
                "period_end": period, "capex_usd": capex, "capex_yoy_pct": None,
                "filing_form": "10-Q", "source": "sec_edgar",
                "source_hash": f"{company}-{fq}", "fetched_at": now_utc,
            }])


def _seed_yield(store, dgs10: float, dgs2: float, days_old: int = 0) -> None:
    period = _AS_OF - dt.timedelta(days=days_old)
    utc_ts = _NOW_UTC - dt.timedelta(days=days_old)
    for iid, val in [("DGS10", dgs10), ("DGS2", dgs2)]:
        store.upsert_indicators([{
            "indicator_id": iid, "group_code": "K",
            "period_date": period, "market_tz": "America/New_York",
            "value": val, "value_unit": "percent", "value_raw": str(val),
            "source": "fred", "realtime_start": None, "vintage_as_of": period,
            "utc_ts": utc_ts, "fetched_at": utc_ts,
        }])


def _seed_sox_risk(store, above_ma: bool, sentiment: float) -> None:
    """Seed SOX prices so that the 20-day MA comparison is satisfied."""
    base_price = 5000.0
    ma_price = base_price * (0.95 if above_ma else 1.05)
    now_utc = dt.datetime.now(tz=dt.UTC)
    # 20 historical prices for SOX MA
    for i in range(20):
        d = _AS_OF - dt.timedelta(days=i + 1)
        store.upsert_indicators([{
            "indicator_id": "^SOX", "group_code": "K",
            "period_date": d, "market_tz": "America/New_York",
            "value": ma_price, "value_unit": "USD", "value_raw": str(ma_price),
            "source": "yahoo_global", "realtime_start": None,
            "vintage_as_of": d, "utc_ts": now_utc, "fetched_at": now_utc,
        }])
    # Current SOX price
    cur = base_price
    store.upsert_indicators([{
        "indicator_id": "^SOX", "group_code": "K",
        "period_date": _AS_OF, "market_tz": "America/New_York",
        "value": cur, "value_unit": "USD", "value_raw": str(cur),
        "source": "yahoo_global", "realtime_start": None,
        "vintage_as_of": _AS_OF, "utc_ts": now_utc, "fetched_at": now_utc,
    }])
    # AV sentiment
    store.upsert_indicators([{
        "indicator_id": "AV_SENTIMENT", "group_code": "O",
        "period_date": _AS_OF, "market_tz": "UTC",
        "value": sentiment, "value_unit": "score", "value_raw": str(sentiment),
        "source": "alpha_vantage", "realtime_start": None,
        "vintage_as_of": _AS_OF, "utc_ts": now_utc, "fetched_at": now_utc,
    }])


# ── TC-011-01 ─────────────────────────────────────────────────────────────────


class TestCompositeGreen:
    """TC-011-01: All three pillars positive → composite_state=green."""

    def test_composite_green_all_pillars_positive(self, regime, mem_store):
        _seed_capex(mem_store, big4_qoq_pct=+8.0)
        _seed_yield(mem_store, dgs10=4.8, dgs2=4.0)   # spread=0.8 → normal
        _seed_sox_risk(mem_store, above_ma=True, sentiment=0.3)

        result = regime.compute(as_of=_AS_OF)

        assert result["capex_state"] == "green"
        assert result["yield_curve_state"] == "normal"
        assert result["risk_state"] == "risk_on"
        assert result["composite_state"] == "green"


# ── TC-011-02 ─────────────────────────────────────────────────────────────────


class TestCapExRedDrivesCompositeRed:
    """TC-011-02: CapEx QoQ < -10% → capex_state=red, composite=red."""

    def test_capex_red_composite_red(self, regime, mem_store):
        _seed_capex(mem_store, big4_qoq_pct=-15.0)
        _seed_yield(mem_store, dgs10=4.8, dgs2=4.0)
        _seed_sox_risk(mem_store, above_ma=True, sentiment=0.3)

        result = regime.compute(as_of=_AS_OF)

        assert result["capex_state"] == "red"
        assert result["composite_state"] == "red"


# ── TC-011-03 ─────────────────────────────────────────────────────────────────


class TestStalePropagatesWhenYieldOld:
    """TC-011-03: DGS10/DGS2 data >3 trading days old → yield_curve_state=stale."""

    def test_stale_propagates_to_composite(self, regime, mem_store):
        _seed_capex(mem_store, big4_qoq_pct=+8.0)
        _seed_yield(mem_store, dgs10=4.8, dgs2=4.0, days_old=5)  # 5 days stale
        _seed_sox_risk(mem_store, above_ma=True, sentiment=0.3)

        result = regime.compute(as_of=_AS_OF)

        assert result["yield_curve_state"] == "stale"
        assert result["composite_state"] == "stale"


# ── TC-011-04 ─────────────────────────────────────────────────────────────────


class TestWriteCacheManualOverridePreserved:
    """TC-011-04: write_cache skips when macro_state.json lacks auto_computed."""

    def test_manual_state_file_not_overwritten(self, regime, tmp_path):
        manual_state = {"state": "manual-override", "note": "hand edited"}
        state_file = tmp_path / "macro_state.json"
        state_file.write_text(json.dumps(manual_state))

        new_state = {"composite_state": "green", "auto_computed": True,
                     "capex_as_of": "2026-Q1", "yield_as_of": None, "computed_at": None}

        with patch.object(regime, "_cache_path", state_file):
            regime.write_cache(new_state)

        content = json.loads(state_file.read_text())
        assert content["state"] == "manual-override", "manual override must not be replaced"


# ── TC-011-05 ─────────────────────────────────────────────────────────────────


class TestWriteCacheAutoPathWorks:
    """TC-011-05: write_cache writes/overwrites when auto_computed=true or file absent."""

    def test_writes_when_file_absent(self, regime, tmp_path):
        state_file = tmp_path / "macro_state.json"
        new_state = {"composite_state": "yellow", "auto_computed": True,
                     "capex_as_of": "2026-Q1", "yield_as_of": str(_AS_OF),
                     "computed_at": _NOW_UTC.isoformat()}

        with patch.object(regime, "_cache_path", state_file):
            regime.write_cache(new_state)

        content = json.loads(state_file.read_text())
        assert content.get("state") == "yellow"
        assert content.get("auto_computed") is True

    def test_overwrites_auto_computed_file(self, regime, tmp_path):
        state_file = tmp_path / "macro_state.json"
        state_file.write_text(json.dumps({"state": "green", "auto_computed": True}))

        new_state = {"composite_state": "red", "auto_computed": True,
                     "capex_as_of": "2026-Q1", "yield_as_of": str(_AS_OF),
                     "computed_at": _NOW_UTC.isoformat()}

        with patch.object(regime, "_cache_path", state_file):
            regime.write_cache(new_state)

        content = json.loads(state_file.read_text())
        assert content.get("state") == "red"


# ── TC-011-06 ─────────────────────────────────────────────────────────────────


class TestAVBudgetGateskipsSentiment:
    """TC-011-06: AV budget >= 22 → skip AlphaVantage, still collect CLS."""

    def test_av_not_called_when_budget_at_22(self, mem_store):
        _orch_mod = pytest.importorskip("engine.macro_agent.orchestrator")
        MacroOrchestrator = _orch_mod.MacroOrchestrator

        # Budget at 22
        today = dt.date.today()
        for _ in range(22):
            mem_store.increment_av_budget(today)

        cls_cfg = MagicMock()
        cls_cfg.indicator_id = "CLS_NEWS"
        cls_cfg.group_code = "O"
        cls_cfg.update_class = "intraday_slow"
        cls_cfg.primary_source = "akshare_macro"
        cls_cfg.backups = []
        cls_cfg.market_tz = "Asia/Shanghai"
        cls_cfg.session_hours = None
        cls_cfg.poll_interval_s = 1800

        av_cfg = MagicMock()
        av_cfg.indicator_id = "AV_SENTIMENT"
        av_cfg.group_code = "O"
        av_cfg.update_class = "intraday_slow"
        av_cfg.primary_source = "alpha_vantage"
        av_cfg.backups = []
        av_cfg.market_tz = "UTC"
        av_cfg.session_hours = None
        av_cfg.poll_interval_s = 1800

        from unittest.mock import MagicMock as MM  # noqa: PLC0415

        akshare_mock = MM()
        akshare_mock.name = "akshare_macro"
        akshare_mock.fetch_cls_news.return_value = [{
            "indicator_id": "CLS_NEWS", "group_code": "O",
            "period_date": today, "market_tz": "Asia/Shanghai",
            "value": None, "value_unit": "", "value_raw": "[]",
            "source": "akshare_macro", "realtime_start": None,
            "vintage_as_of": today, "utc_ts": _NOW_UTC, "fetched_at": _NOW_UTC,
        }]

        av_mock = MM()
        av_mock.name = "alpha_vantage"

        sched = MM()
        sched.get_due_indicators.return_value = [cls_cfg, av_cfg]

        orch = MacroOrchestrator(
            storage=mem_store,
            scheduler=sched,
            sources={"akshare_macro": akshare_mock, "alpha_vantage": av_mock},
            rate_limiter=MM(),
        )
        orch.run_once(groups=["O"])

        av_mock.fetch_news_sentiment.assert_not_called()
        akshare_mock.fetch_cls_news.assert_called_once()

    def test_cls_written_to_macro_indicators(self, mem_store):
        _orch_mod = pytest.importorskip("engine.macro_agent.orchestrator")
        MacroOrchestrator = _orch_mod.MacroOrchestrator
        from unittest.mock import MagicMock as MM  # noqa: PLC0415

        today = dt.date.today()
        for _ in range(22):
            mem_store.increment_av_budget(today)

        cls_cfg = MM()
        cls_cfg.indicator_id = "CLS_NEWS"
        cls_cfg.group_code = "O"
        cls_cfg.update_class = "intraday_slow"
        cls_cfg.primary_source = "akshare_macro"
        cls_cfg.backups = []
        cls_cfg.market_tz = "Asia/Shanghai"
        cls_cfg.session_hours = None
        cls_cfg.poll_interval_s = 1800

        akshare_mock = MM()
        akshare_mock.name = "akshare_macro"
        akshare_mock.fetch_cls_news.return_value = [{
            "indicator_id": "CLS_NEWS", "group_code": "O",
            "period_date": today, "market_tz": "Asia/Shanghai",
            "value": None, "value_unit": "", "value_raw": "[]",
            "source": "akshare_macro", "realtime_start": None,
            "vintage_as_of": today, "utc_ts": _NOW_UTC, "fetched_at": _NOW_UTC,
        }]

        sched = MM()
        sched.get_due_indicators.return_value = [cls_cfg]

        orch = MacroOrchestrator(
            storage=mem_store,
            scheduler=sched,
            sources={"akshare_macro": akshare_mock},
            rate_limiter=MM(),
        )
        orch.run_once(groups=["O"])

        row = mem_store.get_latest_indicator("CLS_NEWS", source="akshare_macro")
        assert row is not None


from unittest.mock import MagicMock  # noqa: E402

# ── TC-011-07 ─────────────────────────────────────────────────────────────────


class TestInvertedYieldDrivesCompositeRed:
    """TC-011-07: yield_curve=inverted independently drives composite_state=red."""

    def test_inverted_yield_composite_red(self, regime, mem_store):
        _seed_capex(mem_store, big4_qoq_pct=+8.0)           # capex=green
        _seed_yield(mem_store, dgs10=3.8, dgs2=4.1)          # spread=-0.3 → inverted
        _seed_sox_risk(mem_store, above_ma=True, sentiment=0.3)  # risk=risk_on

        result = regime.compute(as_of=_AS_OF)

        assert result["yield_curve_state"] == "inverted"
        assert result["composite_state"] == "red"
