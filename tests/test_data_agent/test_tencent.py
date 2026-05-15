"""Tests for engine.data_agent.sources.tencent — mock HTTP, batch splitting, field normalization."""

import datetime as dt
from unittest.mock import MagicMock, patch

import pytest

from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.tencent import TencentSource, _market_prefix


class TestMarketPrefix:
    def test_sh_prefix_for_600(self):
        assert _market_prefix("600000") == "sh"

    def test_sh_prefix_for_9(self):
        assert _market_prefix("900001") == "sh"

    def test_sz_prefix_for_000(self):
        assert _market_prefix("000001") == "sz"

    def test_sz_prefix_for_300(self):
        assert _market_prefix("300001") == "sz"

    def test_sh_prefix_for_688(self):
        # 688xxx = STAR Market, listed on SSE (Shanghai)
        assert _market_prefix("688041") == "sh"


# Minimal valid Tencent qt response for sh600000.
# Fields are tilde-delimited; index 30 = datetime as %Y%m%d%H%M%S;
# index 32 = pct_change; index 3 = price; need >= 58 fields.
def _make_qt_line(code: str = "600000", prefix: str = "sh") -> str:
    # Build 60 fields; place significant values at correct indices
    fields = ["0"] * 60
    fields[0]  = "1"
    fields[1]  = "浦发银行"
    fields[2]  = code
    fields[3]  = "11.50"   # price
    fields[30] = "20260515143000"  # quote_time
    fields[32] = "1.77"   # pct_change
    fields[36] = "9200000"  # volume
    fields[37] = "4600000000"  # amount fallback
    fields[39] = "12.0"   # dynamic_pe
    fields[45] = "100000000000"  # market_cap
    fields[57] = "4600000000"  # amount primary
    return f'v_{prefix}{code}="{"~".join(fields)}";'


_SAMPLE_QT_LINE = _make_qt_line()


def _make_source():
    rl = RateLimiter()
    src = TencentSource.__new__(TencentSource)
    src._rl = rl
    src._session = MagicMock()
    return src


class TestParseQtResponse:
    def test_parses_price(self):
        src = _make_source()
        results = src._parse_qt_response(_SAMPLE_QT_LINE, ["600000"])
        assert len(results) == 1
        assert results[0]["code"] == "600000"
        assert results[0]["price"] == pytest.approx(11.50)

    def test_ignores_unrequested_codes(self):
        src = _make_source()
        results = src._parse_qt_response(_SAMPLE_QT_LINE, ["000001"])
        assert results == []

    def test_pct_change_parsed(self):
        src = _make_source()
        results = src._parse_qt_response(_SAMPLE_QT_LINE, ["600000"])
        assert results[0]["pct_change"] == pytest.approx(1.77)

    def test_source_is_tencent(self):
        src = _make_source()
        results = src._parse_qt_response(_SAMPLE_QT_LINE, ["600000"])
        assert results[0]["source"] == "tencent"

    def test_quote_time_parsed(self):
        src = _make_source()
        results = src._parse_qt_response(_SAMPLE_QT_LINE, ["600000"])
        qt = results[0]["quote_time"]
        assert isinstance(qt, dt.datetime)
        assert qt.hour == 14
        assert qt.minute == 30


class TestFetchQuotesBatching:
    def test_batch_split_at_40(self):
        src = _make_source()
        called_urls = []

        def mock_get(url, **kwargs):
            called_urls.append(url)
            resp = MagicMock()
            resp.text = ""
            resp.raise_for_status = MagicMock()
            return resp

        src._session.get = mock_get
        # 45 codes → should produce 2 batches (40 + 5)
        codes = [f"{600000 + i:06d}" for i in range(45)]
        src.fetch_quotes(codes)
        assert len(called_urls) == 2

    def test_empty_codes_returns_empty(self):
        src = _make_source()
        result = src.fetch_quotes([])
        assert result == []
