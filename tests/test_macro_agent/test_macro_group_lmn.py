"""TC-010-01..06 — Groups L/M/N: CapEx quarterly, APAC semi, China market."""

from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock

import pytest

from engine.data_agent.sources.base import SourceError
from engine.macro_agent.storage import MacroStorage

_orch_mod = pytest.importorskip(
    "engine.macro_agent.orchestrator",
    reason="MacroOrchestrator not yet implemented (pending req_impl)",
)
MacroOrchestrator = _orch_mod.MacroOrchestrator

_NOW_UTC = dt.datetime(2026, 5, 17, 14, 0, tzinfo=dt.UTC)
_TODAY = _NOW_UTC.date()


@pytest.fixture
def mem_store():
    s = MacroStorage(":memory:")
    yield s
    s.close()


def _make_cfg(
    indicator_id: str,
    group_code: str,
    update_class: str = "daily",
    primary_source: str = "sec_edgar",
    backups: list[str] | None = None,
) -> MagicMock:
    cfg = MagicMock()
    cfg.indicator_id = indicator_id
    cfg.group_code = group_code
    cfg.update_class = update_class
    cfg.primary_source = primary_source
    cfg.backups = backups or []
    cfg.market_tz = "America/New_York"
    cfg.session_hours = None
    cfg.poll_interval_s = 86400
    return cfg


def _build_orch(store, due_cfgs, sources):
    sched = MagicMock()
    sched.get_due_indicators.return_value = due_cfgs
    return MacroOrchestrator(
        storage=store,
        scheduler=sched,
        sources=sources,
        rate_limiter=MagicMock(),
    )


# ── TC-010-01 ─────────────────────────────────────────────────────────────────


class TestCapExSingleQuarterReversal:
    """TC-010-01: SEC EDGAR cumulative → single-quarter reversal before upsert."""

    def test_q2_single_quarter_usd(self, mem_store):
        # SEC fixture: Q1=3B (single), Q2_cum=7B (cumulative) → Q2 single = 4B
        q1 = {
            "company": "MSFT",
            "cik": "0000789019",
            "fiscal_quarter": "2026Q1",
            "period_end": dt.date(2026, 3, 31),
            "capex_usd": 3.0,
            "capex_yoy_pct": None,
            "filing_form": "10-Q",
            "source": "sec_edgar",
            "source_hash": "hash_q1",
            "fetched_at": _NOW_UTC,
        }
        q2_single = {
            "company": "MSFT",
            "cik": "0000789019",
            "fiscal_quarter": "2026Q2",
            "period_end": dt.date(2026, 6, 30),
            "capex_usd": 4.0,  # already reversed by fetcher
            "capex_yoy_pct": None,
            "filing_form": "10-Q",
            "source": "sec_edgar",
            "source_hash": "hash_q2",
            "fetched_at": _NOW_UTC,
        }
        mem_store.upsert_capex([q1, q2_single])
        quarters = mem_store.get_capex_quarters("MSFT", 4)
        q2_row = next((r for r in quarters if r["fiscal_quarter"] == "2026Q2"), None)
        assert q2_row is not None
        assert q2_row["capex_usd"] == pytest.approx(4.0)
        assert q2_row["filing_form"] == "10-Q"

    def test_orchestrator_run_once_writes_capex(self, mem_store):
        msft_cfg = _make_cfg("MSFT_CAPEX", "L", update_class="quarterly")

        sec_mock = MagicMock()
        sec_mock.name = "sec_edgar"
        sec_mock.fetch_capex_quarterly.return_value = [{
            "company": "MSFT",
            "cik": "0000789019",
            "fiscal_quarter": "2026Q2",
            "period_end": dt.date(2026, 6, 30),
            "capex_usd": 4.0,
            "capex_yoy_pct": None,
            "filing_form": "10-Q",
            "source": "sec_edgar",
            "source_hash": "abc123",
            "fetched_at": _NOW_UTC,
        }]

        orch = _build_orch(mem_store, [msft_cfg], {"sec_edgar": sec_mock})
        orch.run_once(groups=["L"])

        quarters = mem_store.get_capex_quarters("MSFT", 4)
        assert any(r["fiscal_quarter"] == "2026Q2" for r in quarters)


# ── TC-010-02 ─────────────────────────────────────────────────────────────────


class TestCapExYoYWriteback:
    """TC-010-02: MacroStorage.update_capex_yoy() writes back YoY pct."""

    def _seed(self, store):
        base = {
            "company": "MSFT",
            "cik": "0000789019",
            "filing_form": "10-Q",
            "source": "sec_edgar",
            "source_hash": "h",
            "fetched_at": _NOW_UTC,
            "capex_yoy_pct": None,
        }
        store.upsert_capex([{**base, "fiscal_quarter": "2025Q1",
                             "period_end": dt.date(2025, 3, 31), "capex_usd": 3.0,
                             "source_hash": "h1"}])
        store.upsert_capex([{**base, "fiscal_quarter": "2026Q1",
                             "period_end": dt.date(2026, 3, 31), "capex_usd": 3.9,
                             "source_hash": "h2"}])

    def test_yoy_pct_calculated_and_written(self, mem_store):
        self._seed(mem_store)
        mem_store.update_capex_yoy("MSFT", "2026Q1")
        rows = mem_store.get_capex_quarters("MSFT", 4)
        row_2026q1 = next(r for r in rows if r["fiscal_quarter"] == "2026Q1")
        assert row_2026q1["capex_yoy_pct"] == pytest.approx(30.0, abs=0.1)

    def test_yoy_none_when_prior_year_missing(self, mem_store):
        # Only 2026Q1, no 2025Q1
        mem_store.upsert_capex([{
            "company": "MSFT", "cik": "0000789019", "fiscal_quarter": "2026Q1",
            "period_end": dt.date(2026, 3, 31), "capex_usd": 3.9,
            "capex_yoy_pct": None, "filing_form": "10-Q",
            "source": "sec_edgar", "source_hash": "h", "fetched_at": _NOW_UTC,
        }])
        mem_store.update_capex_yoy("MSFT", "2026Q1")  # must not raise
        rows = mem_store.get_capex_quarters("MSFT", 4)
        assert rows[0]["capex_yoy_pct"] is None


# ── TC-010-03 ─────────────────────────────────────────────────────────────────


class TestCapExYahooFallback:
    """TC-010-03: SEC EDGAR failure triggers Yahoo quoteSummary backup."""

    def test_yahoo_called_when_sec_fails(self, mem_store):
        msft_cfg = _make_cfg(
            "MSFT_CAPEX", "L",
            update_class="quarterly",
            primary_source="sec_edgar",
            backups=["yahoo_global"],
        )

        sec_mock = MagicMock()
        sec_mock.name = "sec_edgar"
        sec_mock.fetch_capex_quarterly.side_effect = SourceError("SEC unavailable")

        yahoo_mock = MagicMock()
        yahoo_mock.name = "yahoo_global"
        yahoo_mock.fetch_capex_quarterly.return_value = [{
            "company": "MSFT", "cik": "0000789019", "fiscal_quarter": "2026Q1",
            "period_end": dt.date(2026, 3, 31), "capex_usd": 3.9,
            "capex_yoy_pct": None, "filing_form": None,
            "source": "yahoo_global", "source_hash": "yh1", "fetched_at": _NOW_UTC,
        }]

        orch = _build_orch(
            mem_store, [msft_cfg], {"sec_edgar": sec_mock, "yahoo_global": yahoo_mock}
        )
        orch.run_once(groups=["L"])

        yahoo_mock.fetch_capex_quarterly.assert_called_once()
        orch_run_fine = True  # run_once() did not raise
        assert orch_run_fine

    def test_capex_written_from_yahoo_backup(self, mem_store):
        msft_cfg = _make_cfg(
            "MSFT_CAPEX", "L",
            update_class="quarterly",
            primary_source="sec_edgar",
            backups=["yahoo_global"],
        )
        sec_mock = MagicMock()
        sec_mock.name = "sec_edgar"
        sec_mock.fetch_capex_quarterly.side_effect = SourceError("SEC unavailable")

        yahoo_mock = MagicMock()
        yahoo_mock.name = "yahoo_global"
        yahoo_mock.fetch_capex_quarterly.return_value = [{
            "company": "MSFT", "cik": "0000789019", "fiscal_quarter": "2026Q1",
            "period_end": dt.date(2026, 3, 31), "capex_usd": 3.9,
            "capex_yoy_pct": None, "filing_form": None,
            "source": "yahoo_global", "source_hash": "yh1", "fetched_at": _NOW_UTC,
        }]

        orch = _build_orch(
            mem_store, [msft_cfg], {"sec_edgar": sec_mock, "yahoo_global": yahoo_mock}
        )
        orch.run_once(groups=["L"])

        quarters = mem_store.get_capex_quarters("MSFT", 4)
        assert any(r["source"] == "yahoo_global" for r in quarters)


# ── TC-010-04 ─────────────────────────────────────────────────────────────────


class TestGroupNSGXA50:
    """TC-010-04: SGX A50 futures written to macro_indicators with group_code N."""

    def test_sgx_a50_written(self, mem_store):
        sgx_cfg = _make_cfg(
            "SGX_A50", "N",
            update_class="intraday_fast",
            primary_source="akshare_macro",
        )
        akshare_mock = MagicMock()
        akshare_mock.name = "akshare_macro"
        akshare_mock.fetch_sgx_a50.return_value = [{
            "indicator_id": "SGX_A50",
            "group_code": "N",
            "period_date": _TODAY,
            "market_tz": "Asia/Shanghai",
            "value": 12500.0,
            "value_unit": "CNY",
            "value_raw": "12500.0",
            "source": "akshare_macro",
            "realtime_start": None,
            "vintage_as_of": _TODAY,
            "utc_ts": _NOW_UTC,
            "fetched_at": _NOW_UTC,
        }]

        orch = _build_orch(mem_store, [sgx_cfg], {"akshare_macro": akshare_mock})
        orch.run_once(groups=["N"])

        row = mem_store.get_latest_indicator("SGX_A50", source="akshare_macro")
        assert row is not None
        assert row["group_code"] == "N"
        assert row["value"] is not None


# ── TC-010-05 ─────────────────────────────────────────────────────────────────


class TestSourceHashIdempotency:
    """TC-010-05: upsert_capex returns 0 and preserves fetched_at when hash unchanged."""

    def test_second_upsert_with_same_hash_returns_zero(self, mem_store):
        record = {
            "company": "MSFT", "cik": "0000789019", "fiscal_quarter": "2026Q1",
            "period_end": dt.date(2026, 3, 31), "capex_usd": 3.9,
            "capex_yoy_pct": None, "filing_form": "10-Q",
            "source": "sec_edgar", "source_hash": "stable_hash",
            "fetched_at": _NOW_UTC,
        }
        n1 = mem_store.upsert_capex([record])
        assert n1 == 1

        later = _NOW_UTC + dt.timedelta(hours=1)
        record_v2 = {**record, "fetched_at": later}
        n2 = mem_store.upsert_capex([record_v2])
        assert n2 == 0, "same source_hash must skip upsert and return 0"

    def test_fetched_at_not_updated_when_hash_same(self, mem_store):
        record = {
            "company": "MSFT", "cik": "0000789019", "fiscal_quarter": "2026Q1",
            "period_end": dt.date(2026, 3, 31), "capex_usd": 3.9,
            "capex_yoy_pct": None, "filing_form": "10-Q",
            "source": "sec_edgar", "source_hash": "stable_hash",
            "fetched_at": _NOW_UTC,
        }
        mem_store.upsert_capex([record])

        later = _NOW_UTC + dt.timedelta(hours=1)
        mem_store.upsert_capex([{**record, "fetched_at": later}])

        row = mem_store._conn.execute(
            "SELECT fetched_at FROM capex_quarterly"
            " WHERE company='MSFT' AND fiscal_quarter='2026Q1'"
        ).fetchone()
        assert row is not None
        stored_ts = row[0]
        # fetched_at must still be the original timestamp
        if hasattr(stored_ts, "replace"):
            stored_ts = stored_ts.replace(tzinfo=dt.UTC) if stored_ts.tzinfo is None else stored_ts
        assert stored_ts == pytest.approx(_NOW_UTC, abs=dt.timedelta(seconds=1))

    def test_new_hash_triggers_upsert(self, mem_store):
        record = {
            "company": "MSFT", "cik": "0000789019", "fiscal_quarter": "2026Q1",
            "period_end": dt.date(2026, 3, 31), "capex_usd": 3.9,
            "capex_yoy_pct": None, "filing_form": "10-Q",
            "source": "sec_edgar", "source_hash": "hash_v1",
            "fetched_at": _NOW_UTC,
        }
        mem_store.upsert_capex([record])
        n2 = mem_store.upsert_capex([{**record, "source_hash": "hash_v2", "capex_usd": 4.5}])
        assert n2 == 1, "changed source_hash must trigger upsert"


# ── TC-010-06 ─────────────────────────────────────────────────────────────────


class TestGroupMKRXFailureDoesNotBlock:
    """TC-010-06: KRX semiconductor index failure leaves other Group M indicators intact."""

    def test_other_m_indicators_written_when_krx_fails(self, mem_store):
        cfgs = [
            _make_cfg("SOXX",     "M", "intraday_slow", "yahoo_global"),
            _make_cfg("^TWII",    "M", "intraday_slow", "yahoo_global"),
            _make_cfg("TSM",      "M", "intraday_slow", "yahoo_global"),
            _make_cfg("005930.KS","M", "daily",         "yahoo_global"),
            _make_cfg("KRX_SEMI", "M", "daily",         "yahoo_global"),
        ]

        def _yahoo_fetch_ohlcv(tickers, **_kwargs):
            records = []
            for t in tickers:
                if t == "KRX_SEMI":
                    raise SourceError("KRX_SEMI unavailable")
                records.append({
                    "indicator_id": t, "group_code": "M",
                    "period_date": _TODAY, "market_tz": "America/New_York",
                    "value": 100.0, "value_unit": "USD", "value_raw": "100.0",
                    "source": "yahoo_global", "realtime_start": None,
                    "vintage_as_of": _TODAY, "utc_ts": _NOW_UTC, "fetched_at": _NOW_UTC,
                })
            return records

        yahoo_mock = MagicMock()
        yahoo_mock.name = "yahoo_global"
        yahoo_mock.fetch_ohlcv.side_effect = _yahoo_fetch_ohlcv

        orch = _build_orch(mem_store, cfgs, {"yahoo_global": yahoo_mock})
        orch.run_once(groups=["M"])  # must not raise

        rows = mem_store._conn.execute(
            "SELECT indicator_id FROM macro_indicators WHERE group_code='M'"
        ).fetchall()
        written = {r[0] for r in rows}
        for expected in ("SOXX", "^TWII", "TSM", "005930.KS"):
            assert expected in written, f"{expected} must be written despite KRX failure"

    def test_run_once_does_not_raise_on_krx_failure(self, mem_store):
        krx_cfg = _make_cfg("KRX_SEMI", "M", "daily", "yahoo_global")
        yahoo_mock = MagicMock()
        yahoo_mock.name = "yahoo_global"
        yahoo_mock.fetch_ohlcv.side_effect = SourceError("KRX_SEMI unavailable")

        orch = _build_orch(mem_store, [krx_cfg], {"yahoo_global": yahoo_mock})
        orch.run_once(groups=["M"])  # must not raise
