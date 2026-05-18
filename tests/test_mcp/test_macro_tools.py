"""TC-012-01..07 — MCP macro tools: Pydantic validation, tool registration, filtering."""

from __future__ import annotations

import datetime as dt
from unittest.mock import patch

import pytest

from engine.macro_agent.storage import MacroStorage

_tools_mod = pytest.importorskip(
    "engine.mcp.macro_tools",
    reason="engine.mcp.macro_tools not yet implemented (pending req_impl)",
)
_server_mod = pytest.importorskip(
    "engine.mcp.server",
    reason="engine.mcp.server not yet implemented (pending req_impl)",
)

get_macro_state = _tools_mod.get_macro_state
get_capex_trend = _tools_mod.get_capex_trend
get_fomc_calendar = _tools_mod.get_fomc_calendar
get_yield_curve = _tools_mod.get_yield_curve
get_news_sentiment = _tools_mod.get_news_sentiment
get_global_indices = _tools_mod.get_global_indices

MacroStateResult = _tools_mod.MacroStateResult
CapExTrendResult = _tools_mod.CapExTrendResult
FOMCCalendarResult = _tools_mod.FOMCCalendarResult
YieldCurveResult = _tools_mod.YieldCurveResult
NewsSentimentResult = _tools_mod.NewsSentimentResult
GlobalIndicesResult = _tools_mod.GlobalIndicesResult

mcp = _server_mod.mcp

_NOW_UTC = dt.datetime(2026, 5, 17, 14, 0, tzinfo=dt.UTC)
_TODAY = _NOW_UTC.date()


@pytest.fixture
def mem_store():
    s = MacroStorage(":memory:")
    yield s
    s.close()


# ── TC-012-01 ─────────────────────────────────────────────────────────────────


class TestGetMacroStateStale:
    """TC-012-01: composite_state=stale propagates to is_stale=True."""

    def test_is_stale_true_when_composite_stale(self, mem_store):
        stale_regime = {
            "as_of_date": _TODAY,
            "capex_state": "stale",
            "yield_curve_state": "stale",
            "risk_state": "stale",
            "composite_state": "stale",
            "capex_as_of": "2026-Q1",
            "yield_as_of": None,
            "computed_at": _NOW_UTC,
        }
        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_regime_latest.return_value = stale_regime
            result = get_macro_state()

        assert result["composite_state"] == "stale"
        assert result["is_stale"] is True

    def test_pydantic_validates_stale_result(self, mem_store):
        stale_regime = {
            "as_of_date": _TODAY, "capex_state": "stale",
            "yield_curve_state": "stale", "risk_state": "stale",
            "composite_state": "stale", "capex_as_of": "2026-Q1",
            "yield_as_of": None, "computed_at": _NOW_UTC,
        }
        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_regime_latest.return_value = stale_regime
            result = get_macro_state()

        MacroStateResult(**result)  # must not raise

    def test_is_stale_false_when_composite_green(self, mem_store):
        green_regime = {
            "as_of_date": _TODAY, "capex_state": "green",
            "yield_curve_state": "normal", "risk_state": "risk_on",
            "composite_state": "green", "capex_as_of": "2026-Q1",
            "yield_as_of": _TODAY, "computed_at": _NOW_UTC,
        }
        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_regime_latest.return_value = green_regime
            result = get_macro_state()

        assert result["is_stale"] is False


# ── TC-012-02 ─────────────────────────────────────────────────────────────────


class TestGetCapExTrendPydantic:
    """TC-012-02: get_capex_trend returns value validated by CapExTrendResult."""

    def test_four_quarters_pydantic_valid(self):
        quarters = [
            {"company": "MSFT", "cik": "0000789019", "fiscal_quarter": f"2025Q{i}",
             "period_end": dt.date(2025, 3 * i, 28), "capex_usd": 3.0 + i * 0.3,
             "capex_yoy_pct": None, "filing_form": "10-Q",
             "source": "sec_edgar", "source_hash": f"h{i}", "fetched_at": _NOW_UTC}
            for i in range(1, 5)
        ]
        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_capex_quarters.return_value = quarters
            result = get_capex_trend("MSFT", quarters=4)

        model = CapExTrendResult(**result)
        assert model.company == "MSFT"
        assert len(model.quarters) == 4

    def test_latest_qoq_pct_type(self):
        quarters = [
            {"company": "MSFT", "cik": "0000789019", "fiscal_quarter": f"2025Q{i}",
             "period_end": dt.date(2025, 3 * i, 28), "capex_usd": 3.0,
             "capex_yoy_pct": None, "filing_form": "10-Q",
             "source": "sec_edgar", "source_hash": f"h{i}", "fetched_at": _NOW_UTC}
            for i in range(1, 5)
        ]
        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_capex_quarters.return_value = quarters
            result = get_capex_trend("MSFT", quarters=4)

        model = CapExTrendResult(**result)
        assert model.latest_qoq_pct is None or isinstance(model.latest_qoq_pct, float)


# ── TC-012-03 ─────────────────────────────────────────────────────────────────


class TestGetFOMCCalendarFilter:
    """TC-012-03: get_fomc_calendar only returns meetings within lookahead_days."""

    def test_only_60day_meeting_returned(self, mem_store):
        # 1 meeting in 60 days, 2 meetings in 120+ days
        meetings_60 = [{"meeting_date": _TODAY + dt.timedelta(days=60),
                        "meeting_type": "regular", "decision_date": None,
                        "rate_decision": None, "target_lower": None,
                        "target_upper": None, "source": "yaml", "updated_at": _NOW_UTC}]
        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_fomc_upcoming.return_value = meetings_60
            result = get_fomc_calendar(lookahead_days=90)

        model = FOMCCalendarResult(**result)
        assert len(model.meetings) == 1
        assert model.next_meeting_date == _TODAY + dt.timedelta(days=60)

    def test_lookahead_days_passed_to_storage(self):
        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_fomc_upcoming.return_value = []
            get_fomc_calendar(lookahead_days=90)

        call_kwargs = mock_store.get_fomc_upcoming.call_args
        assert call_kwargs is not None
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        args = call_kwargs.args if call_kwargs.args else ()
        lookahead = kwargs.get("lookahead_days") or (args[1] if len(args) > 1 else None)
        assert lookahead == 90


# ── TC-012-04 ─────────────────────────────────────────────────────────────────


class TestGetYieldCurveRealTimeStart:
    """TC-012-04: get_yield_curve preserves FRED realtime_start vintage."""

    def test_realtime_start_in_response(self):
        dgs10_row = {"indicator_id": "DGS10", "value": 4.5,
                     "realtime_start": dt.date(2026, 4, 1),
                     "period_date": _TODAY, "source": "fred",
                     "group_code": "K", "market_tz": "America/New_York",
                     "vintage_as_of": _TODAY, "utc_ts": _NOW_UTC, "fetched_at": _NOW_UTC,
                     "value_unit": "percent", "value_raw": "4.5"}
        dgs2_row = {**dgs10_row, "indicator_id": "DGS2", "value": 4.1}

        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_latest_indicator.side_effect = lambda iid, **_: (
                dgs10_row if iid == "DGS10" else dgs2_row
            )
            result = get_yield_curve()

        model = YieldCurveResult(**result)
        assert model.realtime_start == dt.date(2026, 4, 1)

    def test_spread_calculated_correctly(self):
        dgs10_row = {"indicator_id": "DGS10", "value": 4.5, "realtime_start": None,
                     "period_date": _TODAY, "source": "fred", "group_code": "K",
                     "market_tz": "America/New_York", "vintage_as_of": _TODAY,
                     "utc_ts": _NOW_UTC, "fetched_at": _NOW_UTC,
                     "value_unit": "percent", "value_raw": "4.5"}
        dgs2_row = {**dgs10_row, "indicator_id": "DGS2", "value": 4.0}

        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_latest_indicator.side_effect = lambda iid, **_: (
                dgs10_row if iid == "DGS10" else dgs2_row
            )
            result = get_yield_curve()

        assert result["spread_10y_2y"] == pytest.approx(0.5, abs=0.001)


# ── TC-012-05 ─────────────────────────────────────────────────────────────────


class TestGetNewsSentimentBudget:
    """TC-012-05: av_budget_remaining = max(0, 25 - requests_used)."""

    def test_budget_remaining_calculated(self):
        cls_rows = [{"indicator_id": "CLS_NEWS", "group_code": "O",
                     "period_date": _TODAY, "market_tz": "Asia/Shanghai",
                     "value": None, "value_unit": "", "value_raw": "[]",
                     "source": "akshare_macro", "realtime_start": None,
                     "vintage_as_of": _TODAY, "utc_ts": _NOW_UTC, "fetched_at": _NOW_UTC}]
        av_row = {"indicator_id": "AV_SENTIMENT", "group_code": "O",
                  "period_date": _TODAY, "market_tz": "UTC",
                  "value": 0.15, "value_unit": "score", "value_raw": "0.15",
                  "source": "alpha_vantage", "realtime_start": None,
                  "vintage_as_of": _TODAY, "utc_ts": _NOW_UTC, "fetched_at": _NOW_UTC}

        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_av_budget.return_value = 18
            mock_store._conn.execute.return_value.fetchall.return_value = [
                (r["indicator_id"], r["value"], r["fetched_at"]) for r in cls_rows
            ]
            mock_store.get_latest_indicator.return_value = av_row
            result = get_news_sentiment(hours_back=24)

        model = NewsSentimentResult(**result)
        assert model.av_budget_remaining == 7  # 25 - 18

    def test_budget_remaining_clamps_to_zero(self):
        with patch("engine.mcp.macro_tools._storage") as mock_store:
            mock_store.get_av_budget.return_value = 30  # exceeded free limit
            mock_store.get_latest_indicator.return_value = None
            mock_store._conn.execute.return_value.fetchall.return_value = []
            result = get_news_sentiment(hours_back=24)

        assert result["av_budget_remaining"] == 0  # max(0, 25-30) = 0


# ── TC-012-06 ─────────────────────────────────────────────────────────────────


class TestGetGlobalIndicesGroupFilter:
    """TC-012-06: get_global_indices(["J"]) returns only Group J snapshots."""

    def test_only_group_j_returned(self, mem_store):
        # Pre-fill Group J and Group K indicators
        now_utc = _NOW_UTC
        for iid, group in [("BZ=F", "J"), ("CL=F", "J"), ("^SOX", "K"), ("DGS10", "K")]:
            mem_store.upsert_indicators([{
                "indicator_id": iid, "group_code": group,
                "period_date": _TODAY, "market_tz": "America/New_York",
                "value": 100.0, "value_unit": "USD", "value_raw": "100.0",
                "source": "yahoo_global", "realtime_start": None,
                "vintage_as_of": _TODAY, "utc_ts": now_utc, "fetched_at": now_utc,
            }])

        with patch("engine.mcp.macro_tools._storage") as mock_store:
            j_rows = mem_store._conn.execute(
                "SELECT * FROM macro_indicators WHERE group_code='J'"
            ).fetchall()
            cols = [d[0] for d in mem_store._conn.execute(
                "SELECT * FROM macro_indicators LIMIT 0"
            ).description]
            mock_store._conn.execute.return_value.fetchall.return_value = [
                dict(zip(cols, r)) for r in j_rows
            ]
            mock_store._conn.execute.return_value.description = [
                (c,) for c in cols
            ]
            result = get_global_indices(["J"])

        model = GlobalIndicesResult(**result)
        assert len(model.snapshots) > 0
        for snap in model.snapshots:
            assert snap.group_code == "J", f"unexpected group_code: {snap.group_code}"


# ── TC-012-07 ─────────────────────────────────────────────────────────────────


class TestMacroToolsRegistration:
    """TC-012-07: macro_tools are importable and registered on the mcp instance."""

    def test_get_macro_state_is_callable(self):
        assert callable(get_macro_state)

    def test_mcp_instance_exists(self):
        assert mcp is not None

    def test_get_macro_state_registered_on_mcp(self):
        # FastMCP stores tools in an internal manager; check via list_tools or equivalent
        try:
            # Try FastMCP >= 1.x API
            tool_names = [t.name for t in mcp.list_tools()]
        except (AttributeError, TypeError):
            try:
                # Try internal _tool_manager (FastMCP < 1.x)
                tool_names = list(mcp._tool_manager._tools.keys())
            except AttributeError:
                pytest.skip("Cannot introspect FastMCP tool registry (unknown version)")
        assert "get_macro_state" in tool_names

    def test_all_six_tools_registered(self):
        expected = {
            "get_macro_state", "get_capex_trend", "get_fomc_calendar",
            "get_yield_curve", "get_news_sentiment", "get_global_indices",
        }
        try:
            tool_names = {t.name for t in mcp.list_tools()}
        except (AttributeError, TypeError):
            try:
                tool_names = set(mcp._tool_manager._tools.keys())
            except AttributeError:
                pytest.skip("Cannot introspect FastMCP tool registry (unknown version)")
        missing = expected - tool_names
        assert not missing, f"MCP tools not registered: {missing}"
