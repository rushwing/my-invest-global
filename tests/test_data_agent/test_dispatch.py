"""
Tests for the orchestrator dispatch fix (P1) and Eastmoney field scaling (P3).

Verifies that:
- Each FieldGroup routes to the correct source method, not always fetch_quotes()
- SlowAgent calls fetch_kline_day / fetch_business_segments / fetch_fund_flow for the
  appropriate groups
- Eastmoney push2 fields that are scaled × 100 are divided back to real values
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from engine.data_agent.fields import (
    GROUP_DISPATCH,
    GROUP_PER_CODE,
    FAST_SOURCES,
    FieldGroup,
)
from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sub_agents.slow_agent import SlowAgent


# ── GROUP_DISPATCH completeness ───────────────────────────────────────────────

class TestGroupDispatch:
    def test_all_groups_have_dispatch(self):
        for group in FieldGroup:
            assert group in GROUP_DISPATCH, f"{group} missing from GROUP_DISPATCH"

    def test_quote_dispatches_to_fetch_quotes(self):
        assert GROUP_DISPATCH[FieldGroup.QUOTE] == "fetch_quotes"

    def test_kline_dispatches_to_fetch_kline_day(self):
        assert GROUP_DISPATCH[FieldGroup.KLINE] == "fetch_kline_day"

    def test_segment_dispatches_to_fetch_business_segments(self):
        assert GROUP_DISPATCH[FieldGroup.SEGMENT] == "fetch_business_segments"

    def test_fund_flow_dispatches_to_fetch_fund_flow(self):
        assert GROUP_DISPATCH[FieldGroup.FUND_FLOW] == "fetch_fund_flow"

    def test_per_code_groups_correct(self):
        # QUOTE, INDEX, and FUNDAMENTAL are batch-call groups (not per-code).
        # FUNDAMENTAL is excluded because TushareSource.fetch_fundamentals()
        # accepts codes: list[str] — calling it per-code would iterate characters.
        batch_groups = {FieldGroup.QUOTE, FieldGroup.INDEX, FieldGroup.FUNDAMENTAL}
        for group in FieldGroup:
            if group in batch_groups:
                assert group not in GROUP_PER_CODE
            else:
                assert group in GROUP_PER_CODE


# ── SlowAgent dispatch ────────────────────────────────────────────────────────

def _make_rl():
    rl = RateLimiter()
    return rl


def _mock_source(name="eastmoney", domain="push2.eastmoney.com"):
    src = MagicMock()
    src.name = name
    src.domain = domain
    return src


class TestSlowAgentDispatch:
    def setup_method(self):
        self.rl = _make_rl()
        self.agent = SlowAgent(self.rl)

    def test_kline_calls_fetch_kline_day_not_fetch_quotes(self):
        src = _mock_source()
        src.fetch_kline_day.return_value = [
            {"code": "600000", "trade_date": "2026-05-15", "close": 11.5}
        ]
        results = self.agent.fetch(FieldGroup.KLINE, ["600000"], src)
        src.fetch_kline_day.assert_called_once_with("600000")
        src.fetch_quotes.assert_not_called()
        assert len(results) == 1

    def test_segment_calls_fetch_business_segments(self):
        src = _mock_source()
        src.fetch_business_segments.return_value = [
            {"code": "600000", "segment_name": "光模块", "revenue": 1e9}
        ]
        results = self.agent.fetch(FieldGroup.SEGMENT, ["600000"], src)
        src.fetch_business_segments.assert_called_once_with("600000")
        assert len(results) == 1

    def test_fund_flow_calls_fetch_fund_flow(self):
        src = _mock_source()
        src.fetch_fund_flow.return_value = [
            {"code": "600000", "main_net_inflow": 1e8}
        ]
        results = self.agent.fetch(FieldGroup.FUND_FLOW, ["600000"], src)
        src.fetch_fund_flow.assert_called_once_with("600000")
        assert results[0]["main_net_inflow"] == 1e8

    def test_quote_calls_fetch_quotes_batch(self):
        src = _mock_source()
        src.fetch_quotes.return_value = [
            {"code": "600000", "price": 11.5},
            {"code": "000001", "price": 15.2},
        ]
        results = self.agent.fetch(FieldGroup.QUOTE, ["600000", "000001"], src)
        # Batch call: fetch_quotes called once with all codes
        src.fetch_quotes.assert_called_once_with(["600000", "000001"])
        assert len(results) == 2

    def test_missing_method_raises_source_error(self):
        from engine.data_agent.sources.base import SourceError
        src = _mock_source()
        # Remove fetch_fund_flow from mock
        del src.fetch_fund_flow
        with pytest.raises(SourceError, match="does not implement"):
            self.agent.fetch(FieldGroup.FUND_FLOW, ["600000"], src)

    def test_per_code_iterates_all_codes(self):
        src = _mock_source()
        src.fetch_kline_day.return_value = [{"code": "x", "trade_date": "2026-05-15"}]
        codes = ["600000", "000001", "688041"]
        self.agent.fetch(FieldGroup.KLINE, codes, src)
        assert src.fetch_kline_day.call_count == 3

    def test_per_code_normalises_dict_return(self):
        """Per-code method returning a dict (not list) should be wrapped in list."""
        src = _mock_source()
        src.fetch_fund_flow.return_value = {"code": "600000", "main_net_inflow": 1e8}
        results = self.agent.fetch(FieldGroup.FUND_FLOW, ["600000"], src)
        assert results == [{"code": "600000", "main_net_inflow": 1e8}]

    def test_per_code_circuit_open_stops_early(self):
        src = _mock_source()
        src.fetch_kline_day.return_value = [{"code": "x"}]
        # Open the circuit after first call
        call_count = 0
        original_is_circuit_open = self.rl.is_circuit_open

        def is_open_after_one(domain):
            nonlocal call_count
            call_count += 1
            return call_count > 2  # open after first code

        with patch.object(self.rl, "is_circuit_open", side_effect=is_open_after_one):
            self.agent.fetch(FieldGroup.KLINE, ["600000", "000001", "688041"], src)

        # Should have stopped early
        assert src.fetch_kline_day.call_count < 3


# ── Eastmoney field scaling ───────────────────────────────────────────────────

class TestEastmoneyFieldScaling:
    """Verify that push2 fields scaled × 100 are correctly divided."""

    def _make_source(self):
        from engine.data_agent.sources.eastmoney import EastmoneySource
        rl = RateLimiter()
        src = EastmoneySource.__new__(EastmoneySource)
        src._rl = rl
        src._session = MagicMock()
        src.domain = "push2.eastmoney.com"
        return src

    def _mock_payload(self, **fields) -> dict:
        return {"data": fields}

    def test_price_divided_by_100(self):
        src = self._make_source()
        src._get = MagicMock(return_value=self._mock_payload(f43=1234))
        result = src._fetch_single_quote("600000")
        assert result["price"] == pytest.approx(12.34)

    def test_pct_change_divided_by_100(self):
        src = self._make_source()
        src._get = MagicMock(return_value=self._mock_payload(f170=156))
        result = src._fetch_single_quote("600000")
        assert result["pct_change"] == pytest.approx(1.56)

    def test_dynamic_pe_divided_by_100(self):
        src = self._make_source()
        src._get = MagicMock(return_value=self._mock_payload(f162=1567))
        result = src._fetch_single_quote("600000")
        assert result["dynamic_pe"] == pytest.approx(15.67)

    def test_pb_divided_by_100(self):
        src = self._make_source()
        src._get = MagicMock(return_value=self._mock_payload(f167=123))
        result = src._fetch_single_quote("600000")
        assert result["pb"] == pytest.approx(1.23)

    def test_turnover_rate_divided_by_100(self):
        src = self._make_source()
        src._get = MagicMock(return_value=self._mock_payload(f168=56))
        result = src._fetch_single_quote("600000")
        assert result["turnover_rate"] == pytest.approx(0.56)

    def test_volume_not_scaled(self):
        src = self._make_source()
        src._get = MagicMock(return_value=self._mock_payload(f47=9200000))
        result = src._fetch_single_quote("600000")
        assert result["volume"] == pytest.approx(9200000)

    def test_market_cap_not_scaled(self):
        src = self._make_source()
        src._get = MagicMock(return_value=self._mock_payload(f116=100000000000))
        result = src._fetch_single_quote("600000")
        assert result["market_cap"] == pytest.approx(100000000000)


# ── Eastmoney MAINOP_TYPE fix ─────────────────────────────────────────────────

class TestEastmoneySegmentFallback:
    """Verify that latest report date is determined before applying type preference."""

    def _make_source(self):
        from engine.data_agent.sources.eastmoney import EastmoneySource
        rl = RateLimiter()
        src = EastmoneySource.__new__(EastmoneySource)
        src._rl = rl
        return src

    def _row(self, report_date, mainop_type, item_name, income=1e8):
        return {
            "REPORT_DATE": report_date,
            "MAINOP_TYPE": str(mainop_type),
            "ITEM_NAME": item_name,
            "MAIN_BUSINESS_INCOME": str(income),
            "MAIN_BUSINESS_RPOFIT": str(income * 0.2),
            "MBI_RATIO": "0.5",
            "MBR_RATIO": "0.2",
        }

    def test_uses_latest_date_not_global_type_2(self):
        """If latest period only has type-1 rows but older periods have type-2,
        should return latest period's type-1 rows (not older type-2)."""
        src = self._make_source()
        payload = {
            "zygcfx": [
                # Older period: has type-2 (product) rows
                self._row("2023-12-31", 2, "光模块"),
                # Latest period: only has type-1 (industry) rows
                self._row("2024-12-31", 1, "光通信"),
            ]
        }
        rows = src._parse_segments("600000", payload)
        assert len(rows) == 1
        assert rows[0]["report_date"] == "2024-12-31"
        assert rows[0]["segment_name"] == "光通信"

    def test_latest_period_type_2_preferred(self):
        src = self._make_source()
        payload = {
            "zygcfx": [
                self._row("2024-12-31", 1, "光通信"),
                self._row("2024-12-31", 2, "光模块"),
            ]
        }
        rows = src._parse_segments("600000", payload)
        # Type-2 should be preferred
        assert all(r["segment_name"] == "光模块" for r in rows)

    def test_empty_payload_returns_empty(self):
        src = self._make_source()
        assert src._parse_segments("600000", {}) == []
        assert src._parse_segments("600000", {"zygcfx": []}) == []


# ── P1 INDEX fix: separate index codes and fetch_index_quotes ─────────────────

class TestIndexGroupDispatch:
    def test_index_dispatches_to_fetch_index_quotes(self):
        assert GROUP_DISPATCH[FieldGroup.INDEX] == "fetch_index_quotes"

    def test_index_not_in_fast_sources_dispatch_uses_batch(self):
        # INDEX is not per-code; agents should call method(symbols_list)
        assert FieldGroup.INDEX not in GROUP_PER_CODE

    def test_tencent_has_fetch_index_quotes(self):
        from engine.data_agent.sources.tencent import TencentSource
        assert hasattr(TencentSource, "fetch_index_quotes")

    def test_sina_has_fetch_index_quotes(self):
        from engine.data_agent.sources.sina import SinaSource
        assert hasattr(SinaSource, "fetch_index_quotes")

    def test_tencent_parse_index_response_uses_full_symbol_as_code(self):
        from engine.data_agent.sources.tencent import TencentSource
        rl = RateLimiter()
        src = TencentSource.__new__(TencentSource)
        src._rl = rl
        src._session = MagicMock()
        src.domain = "qt.gtimg.cn"

        # Minimal valid qt response (58+ tilde-separated fields)
        fields = ["1"] * 58
        fields[3] = "3456.78"    # price
        fields[30] = "20260516093000"  # quote_time
        fields[32] = "0.12"      # pct_change
        text = 'v_sh000001="' + "~".join(fields) + '"'

        rows = src._parse_index_response(text, {"sh000001"})
        assert len(rows) == 1
        assert rows[0]["code"] == "sh000001"
        assert rows[0]["price"] == pytest.approx(3456.78)

    def test_tencent_parse_index_response_ignores_unrequested_symbols(self):
        from engine.data_agent.sources.tencent import TencentSource
        rl = RateLimiter()
        src = TencentSource.__new__(TencentSource)
        src._rl = rl
        src._session = MagicMock()
        src.domain = "qt.gtimg.cn"

        fields = ["1"] * 58
        fields[30] = "20260516093000"
        text = 'v_sh000001="' + "~".join(fields) + '";v_sz399001="' + "~".join(fields) + '"'

        # Only request sh000001
        rows = src._parse_index_response(text, {"sh000001"})
        assert len(rows) == 1
        assert rows[0]["code"] == "sh000001"


# ── P1 FUND_FLOW fix: SourceError propagates (no silent swallow) ──────────────

class TestFundFlowSourceErrorPropagation:
    def _make_source(self):
        from engine.data_agent.sources.eastmoney import EastmoneySource
        rl = RateLimiter()
        src = EastmoneySource.__new__(EastmoneySource)
        src._rl = rl
        src._session = MagicMock()
        src.domain = "push2.eastmoney.com"
        return src

    def test_network_error_raises_source_error(self):
        from engine.data_agent.sources.base import SourceError
        src = self._make_source()
        src._get = MagicMock(side_effect=SourceError("connection failed"))
        with pytest.raises(SourceError, match="connection failed"):
            src.fetch_fund_flow("600000")

    def test_empty_data_returns_empty_list(self):
        src = self._make_source()
        src._get = MagicMock(return_value={"data": {}})
        assert src.fetch_fund_flow("600000") == []

    def test_none_data_returns_empty_list(self):
        src = self._make_source()
        src._get = MagicMock(return_value={"data": None})
        assert src.fetch_fund_flow("600000") == []


# ── P2 double-recording fix: base._get records failure once ──────────────────

class TestBaseGetFailureRecording:
    def test_single_failure_recorded_once_after_all_retries(self):
        """A connection error across 3 retries should call record_failure exactly once."""
        from engine.data_agent.sources.base import AbstractSource, SourceError

        class _Src(AbstractSource):
            name = "test"
            domain = "example.com"
            def fetch_quotes(self, codes):
                return []

        rl = RateLimiter()
        src = _Src(rl)
        src._session = MagicMock()
        src._session.get.side_effect = ConnectionError("timeout")

        record_calls = []
        original = rl.record_failure
        rl.record_failure = lambda domain, status: record_calls.append((domain, status))

        with pytest.raises(SourceError):
            src._get("https://example.com/api", retries=3)

        assert len(record_calls) == 1, (
            f"Expected 1 record_failure call, got {len(record_calls)}"
        )

    def test_rate_limit_response_records_failure_immediately(self):
        """A 429 response should record failure once without retrying."""
        from engine.data_agent.sources.base import AbstractSource, SourceError

        class _Src(AbstractSource):
            name = "test"
            domain = "example.com"
            def fetch_quotes(self, codes):
                return []

        rl = RateLimiter()
        src = _Src(rl)
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        src._session = MagicMock()
        src._session.get.return_value = mock_resp

        record_calls = []
        rl.record_failure = lambda domain, status: record_calls.append((domain, status))

        with pytest.raises(SourceError):
            src._get("https://example.com/api", retries=3)

        assert len(record_calls) == 1
        assert record_calls[0][1] == 429  # status code preserved


# ── P2 retrieval_log fix: log records actual source name ─────────────────────

class TestOrchestratorActualSource:
    def test_fetch_with_fallback_returns_actual_source_name(self):
        """_fetch_with_fallback must return (src_name, rows), not just rows."""
        from engine.data_agent.orchestrator import StockDataOrchestrator, AllSourcesFailedError
        from engine.data_agent.fields import FIELD_POLICIES
        from engine.data_agent.sources.base import SourceError

        rl = RateLimiter()
        storage = MagicMock()
        fast = MagicMock()
        slow = MagicMock()
        scheduler = MagicMock()

        primary_src = MagicMock()
        primary_src.domain = "qt.gtimg.cn"
        backup_src = MagicMock()
        backup_src.domain = "hq.sinajs.cn"

        fast.fetch.side_effect = [SourceError("primary down"), [{"code": "000001"}]]

        orch = StockDataOrchestrator(
            codes=["000001"],
            sources={"tencent": primary_src, "sina": backup_src},
            storage=storage,
            fast=fast,
            slow=slow,
            scheduler=scheduler,
            rate_limiter=rl,
        )
        policy = FIELD_POLICIES[FieldGroup.QUOTE]
        src_name, rows = orch._fetch_with_fallback(
            FieldGroup.QUOTE, ["000001"], policy
        )
        assert src_name == "sina"
        assert rows == [{"code": "000001"}]

    def test_all_sources_fail_raises(self):
        from engine.data_agent.orchestrator import StockDataOrchestrator, AllSourcesFailedError
        from engine.data_agent.fields import FIELD_POLICIES
        from engine.data_agent.sources.base import SourceError

        rl = RateLimiter()
        fast = MagicMock()
        fast.fetch.side_effect = SourceError("down")

        src = MagicMock()
        src.domain = "qt.gtimg.cn"

        orch = StockDataOrchestrator(
            codes=["000001"],
            sources={"tencent": src},
            storage=MagicMock(),
            fast=fast,
            slow=MagicMock(),
            scheduler=MagicMock(),
            rate_limiter=rl,
        )
        policy = FIELD_POLICIES[FieldGroup.QUOTE]
        with pytest.raises(AllSourcesFailedError):
            orch._fetch_with_fallback(FieldGroup.QUOTE, ["000001"], policy)
