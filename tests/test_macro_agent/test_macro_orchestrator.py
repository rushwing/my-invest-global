"""TC-009-01..06 — MacroOrchestrator Groups I/J/K collection and CLI entry."""

from __future__ import annotations

import datetime as dt
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from engine.data_agent.sources.base import SourceError
from engine.macro_agent.storage import MacroStorage

_orch_mod = pytest.importorskip(
    "engine.macro_agent.orchestrator",
    reason="MacroOrchestrator not yet implemented (pending req_impl)",
)
MacroOrchestrator = _orch_mod.MacroOrchestrator

# ── Helpers ───────────────────────────────────────────────────────────────────

_NOW_UTC = dt.datetime(2026, 5, 17, 14, 0, tzinfo=dt.UTC)
_TODAY = _NOW_UTC.date()


def _make_indicator(
    indicator_id: str,
    group_code: str,
    update_class: str = "intraday_slow",
    primary_source: str = "fred",
    backups: list[str] | None = None,
    market_tz: str = "America/New_York",
    session_hours: tuple | None = (dt.time(9, 30), dt.time(16, 0)),
    poll_interval_s: int = 900,
) -> MagicMock:
    """Return a MagicMock mimicking IndicatorConfig."""
    cfg = MagicMock()
    cfg.indicator_id = indicator_id
    cfg.group_code = group_code
    cfg.update_class = update_class
    cfg.primary_source = primary_source
    cfg.backups = backups or []
    cfg.market_tz = market_tz
    cfg.session_hours = session_hours
    cfg.poll_interval_s = poll_interval_s
    return cfg


def _make_indicator_record(
    indicator_id: str,
    group_code: str,
    value: float,
    period_date: dt.date | None = None,
    source: str = "fred",
) -> dict[str, Any]:
    """Return a dict matching macro_indicators DDL."""
    return {
        "indicator_id": indicator_id,
        "group_code": group_code,
        "period_date": period_date or _TODAY,
        "market_tz": "America/New_York",
        "value": value,
        "value_unit": "percent",
        "value_raw": str(value),
        "source": source,
        "realtime_start": None,
        "vintage_as_of": _TODAY,
        "utc_ts": _NOW_UTC,
        "fetched_at": _NOW_UTC,
    }


@pytest.fixture
def mem_store():
    s = MacroStorage(":memory:")
    yield s
    s.close()


def _build_orchestrator(
    storage: MacroStorage,
    scheduler_due: list,
    sources: dict,
) -> MacroOrchestrator:
    """Construct MacroOrchestrator with injected mocks (not from_defaults)."""
    mock_scheduler = MagicMock()
    mock_scheduler.get_due_indicators.return_value = scheduler_due
    mock_rl = MagicMock()
    return MacroOrchestrator(
        storage=storage,
        scheduler=mock_scheduler,
        sources=sources,
        rate_limiter=mock_rl,
    )


# ── TC-009-01 ─────────────────────────────────────────────────────────────────


class TestGroupIFREDFallback:
    """TC-009-01: primary FREDSource failure triggers AKShare backup."""

    def test_fallback_invokes_akshare(self, mem_store: MacroStorage) -> None:
        cpiaucsl_cfg = _make_indicator(
            "CPIAUCSL", "I",
            update_class="monthly_fixed",
            primary_source="fred",
            backups=["akshare_macro"],
        )

        fred_mock = MagicMock()
        fred_mock.name = "fred"
        fred_mock.fetch_series.side_effect = SourceError("FRED unavailable")

        akshare_mock = MagicMock()
        akshare_mock.name = "akshare_macro"
        akshare_mock.fetch_us_cpi.return_value = [
            _make_indicator_record("CPIAUCSL", "I", 3.2, source="akshare_macro")
        ]

        orch = _build_orchestrator(
            mem_store,
            scheduler_due=[cpiaucsl_cfg],
            sources={"fred": fred_mock, "akshare_macro": akshare_mock},
        )
        orch.run_once(groups=["I"])

        fred_mock.fetch_series.assert_called_once()
        akshare_mock.fetch_us_cpi.assert_called_once()

    def test_fallback_upserts_to_macro_indicators(self, mem_store: MacroStorage) -> None:
        cpiaucsl_cfg = _make_indicator(
            "CPIAUCSL", "I",
            update_class="monthly_fixed",
            primary_source="fred",
            backups=["akshare_macro"],
        )

        fred_mock = MagicMock()
        fred_mock.name = "fred"
        fred_mock.fetch_series.side_effect = SourceError("FRED unavailable")

        akshare_mock = MagicMock()
        akshare_mock.name = "akshare_macro"
        akshare_mock.fetch_us_cpi.return_value = [
            _make_indicator_record("CPIAUCSL", "I", 3.2, source="akshare_macro")
        ]

        orch = _build_orchestrator(
            mem_store,
            scheduler_due=[cpiaucsl_cfg],
            sources={"fred": fred_mock, "akshare_macro": akshare_mock},
        )
        orch.run_once(groups=["I"])

        row = mem_store.get_latest_indicator("CPIAUCSL", source="akshare_macro")
        assert row is not None
        assert row["source"] == "akshare_macro"


# ── TC-009-02 ─────────────────────────────────────────────────────────────────


class TestRetrievalLogCleanDB:
    """TC-009-02: retrieval_log initialises in a brand-new :memory: DB."""

    def _run(self, store: MacroStorage) -> None:
        success_cfg = _make_indicator("DGS10", "K", primary_source="fred")
        fail_cfg = _make_indicator(
            "CPIAUCSL", "I",
            primary_source="fred",
            backups=[],
        )

        fred_success = MagicMock()
        fred_success.name = "fred"
        fred_success.fetch_series.side_effect = [
            # First call (DGS10): success
            [_make_indicator_record("DGS10", "K", 4.5)],
            # Second call (CPIAUCSL): failure
            SourceError("unavailable"),
        ]

        orch = _build_orchestrator(
            store,
            scheduler_due=[success_cfg, fail_cfg],
            sources={"fred": fred_success},
        )
        orch.run_once()

    def test_run_once_does_not_raise(self, mem_store: MacroStorage) -> None:
        self._run(mem_store)  # must not raise

    def test_retrieval_log_table_exists(self, mem_store: MacroStorage) -> None:
        self._run(mem_store)
        rows = mem_store._conn.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_name = 'retrieval_log'"
        ).fetchall()
        assert rows, "retrieval_log table must exist after run_once()"

    def test_retrieval_log_has_ok_row(self, mem_store: MacroStorage) -> None:
        self._run(mem_store)
        row = mem_store._conn.execute(
            "SELECT * FROM retrieval_log WHERE status = 'ok' LIMIT 1"
        ).fetchone()
        assert row is not None, "expected at least one ok row in retrieval_log"

    def test_retrieval_log_has_failed_row(self, mem_store: MacroStorage) -> None:
        self._run(mem_store)
        row = mem_store._conn.execute(
            "SELECT * FROM retrieval_log WHERE status = 'failed' LIMIT 1"
        ).fetchone()
        assert row is not None, "expected at least one failed row in retrieval_log"

    def test_ok_row_has_source_and_latency(self, mem_store: MacroStorage) -> None:
        self._run(mem_store)
        row = mem_store._conn.execute(
            "SELECT source, latency_ms FROM retrieval_log WHERE status = 'ok' LIMIT 1"
        ).fetchone()
        assert row is not None
        source, latency_ms = row
        assert source is not None and source != ""
        assert latency_ms is not None and latency_ms >= 0

    def test_macro_fields_in_retrieval_log(self, mem_store: MacroStorage) -> None:
        self._run(mem_store)
        row = mem_store._conn.execute(
            "SELECT field_group, code FROM retrieval_log WHERE status = 'ok' LIMIT 1"
        ).fetchone()
        assert row is not None
        field_group, code = row
        # group_code written to field_group; indicator_id written to code
        assert field_group in ("I", "J", "K", "L", "M", "N", "O")
        assert code is not None


# ── TC-009-03 ─────────────────────────────────────────────────────────────────


class TestGroupKIntradayFastSkipAfterHours:
    """TC-009-03: INTRADAY_FAST NVDA is skipped outside NYSE hours (01:00 ET)."""

    def test_nvda_not_fetched_at_0100_et(self, mem_store: MacroStorage) -> None:
        # Scheduler returns no due indicators at 01:00 ET for INTRADAY_FAST
        # (the real scheduler filters; here we simulate its output)
        mock_scheduler = MagicMock()
        mock_scheduler.get_due_indicators.return_value = []  # nothing due at 01:00 ET

        yahoo_mock = MagicMock()
        yahoo_mock.name = "yahoo_global"

        orch = MacroOrchestrator(
            storage=mem_store,
            scheduler=mock_scheduler,
            sources={"yahoo_global": yahoo_mock},
            rate_limiter=MagicMock(),
        )

        # Simulate 01:00 ET — pass now to confirm scheduler receives the time
        t_0100_et = dt.datetime(2026, 5, 17, 1, 0,
                                tzinfo=dt.timezone(dt.timedelta(hours=-4)))
        orch.run_once(groups=["K"], now=t_0100_et)

        # Scheduler must have been called with now
        mock_scheduler.get_due_indicators.assert_called_once()
        call_kwargs = mock_scheduler.get_due_indicators.call_args
        assert call_kwargs is not None

        # Yahoo source should not have fetched NVDA
        yahoo_mock.fetch_ohlcv.assert_not_called()

    def test_scheduler_groups_filter_passed_for_k(self, mem_store: MacroStorage) -> None:
        mock_scheduler = MagicMock()
        mock_scheduler.get_due_indicators.return_value = []

        orch = MacroOrchestrator(
            storage=mem_store,
            scheduler=mock_scheduler,
            sources={},
            rate_limiter=MagicMock(),
        )
        orch.run_once(groups=["K"])

        call_kwargs = mock_scheduler.get_due_indicators.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        args = call_kwargs.args if call_kwargs.args else ()
        groups_passed = kwargs.get("groups_filter") or (args[1] if len(args) > 1 else None)
        assert groups_passed == ["K"]


# ── TC-009-04 ─────────────────────────────────────────────────────────────────


class TestCLIOnceExitCode:
    """TC-009-04: refresh-macro-agent --once exits 0 even with partial failures."""

    def test_pyproject_registers_refresh_macro_agent(self) -> None:
        import tomllib
        from pathlib import Path
        pyproject = Path(__file__).parents[2] / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        scripts = data.get("project", {}).get("scripts", {})
        assert "refresh-macro-agent" in scripts, (
            "refresh-macro-agent must be registered in [project.scripts]"
        )
        assert scripts["refresh-macro-agent"] == "scripts.refresh_macro_agent:main"

    def test_main_once_exits_zero_all_success(self, mem_store: MacroStorage) -> None:
        from scripts.refresh_macro_agent import main  # noqa: PLC0415

        with (
            patch("scripts.refresh_macro_agent.MacroOrchestrator") as MockOrch,
            patch.object(sys, "argv", ["refresh-macro-agent", "--once"]),
        ):
            mock_orch = MagicMock()
            MockOrch.from_defaults.return_value = mock_orch
            main()
            mock_orch.run_once.assert_called_once()

    def test_main_once_exits_zero_partial_failure(self, mem_store: MacroStorage) -> None:
        from scripts.refresh_macro_agent import main  # noqa: PLC0415

        with (
            patch("scripts.refresh_macro_agent.MacroOrchestrator") as MockOrch,
            patch.object(sys, "argv", ["refresh-macro-agent", "--once", "--groups", "I,K"]),
        ):
            mock_orch = MagicMock()
            # run_once does NOT raise even with internal failures
            mock_orch.run_once.return_value = None
            MockOrch.from_defaults.return_value = mock_orch
            main()  # must not raise SystemExit with non-zero code


# ── TC-009-05 ─────────────────────────────────────────────────────────────────


class TestT10Y2YSpreadCalculation:
    """TC-009-05: DGS10=4.5 + DGS2=4.1 → T10Y2Y row with value=0.4."""

    def test_spread_written_to_macro_indicators(self, mem_store: MacroStorage) -> None:
        dgs10_cfg = _make_indicator("DGS10", "K", update_class="daily", primary_source="fred")
        dgs2_cfg = _make_indicator("DGS2", "K", update_class="daily", primary_source="fred")

        fred_mock = MagicMock()
        fred_mock.name = "fred"
        fred_mock.fetch_series.side_effect = [
            [_make_indicator_record("DGS10", "K", 4.5)],
            [_make_indicator_record("DGS2", "K", 4.1)],
        ]

        orch = _build_orchestrator(
            mem_store,
            scheduler_due=[dgs10_cfg, dgs2_cfg],
            sources={"fred": fred_mock},
        )
        orch.run_once(groups=["K"])

        spread_row = mem_store.get_latest_indicator("T10Y2Y")
        assert spread_row is not None, "T10Y2Y spread row must be written"
        assert spread_row["value"] == pytest.approx(0.4, abs=1e-4)

    def test_spread_period_date_matches_inputs(self, mem_store: MacroStorage) -> None:
        target_date = dt.date(2026, 5, 16)
        dgs10_cfg = _make_indicator("DGS10", "K", update_class="daily", primary_source="fred")
        dgs2_cfg = _make_indicator("DGS2", "K", update_class="daily", primary_source="fred")

        fred_mock = MagicMock()
        fred_mock.name = "fred"
        fred_mock.fetch_series.side_effect = [
            [_make_indicator_record("DGS10", "K", 4.5, period_date=target_date)],
            [_make_indicator_record("DGS2", "K", 4.1, period_date=target_date)],
        ]

        orch = _build_orchestrator(
            mem_store,
            scheduler_due=[dgs10_cfg, dgs2_cfg],
            sources={"fred": fred_mock},
        )
        orch.run_once(groups=["K"])

        spread_row = mem_store.get_latest_indicator("T10Y2Y")
        assert spread_row is not None
        assert spread_row["period_date"] == target_date


# ── TC-009-06 ─────────────────────────────────────────────────────────────────


class TestGroupsFilterIsolation:
    """TC-009-06: run_once(groups=["I"]) must not invoke Group J or K sources."""

    def test_only_group_i_sources_called(self, mem_store: MacroStorage) -> None:
        # Scheduler returns only Group I due indicators (groups_filter applied internally)
        cfg_i = _make_indicator("CPIAUCSL", "I", primary_source="fred")

        mock_scheduler = MagicMock()
        mock_scheduler.get_due_indicators.return_value = [cfg_i]
        # (scheduler has already applied groups_filter=["I"])

        fred_mock = MagicMock()
        fred_mock.name = "fred"
        fred_mock.fetch_series.return_value = [
            _make_indicator_record("CPIAUCSL", "I", 3.2)
        ]

        yahoo_mock = MagicMock()
        yahoo_mock.name = "yahoo_global"

        orch = MacroOrchestrator(
            storage=mem_store,
            scheduler=mock_scheduler,
            sources={"fred": fred_mock, "yahoo_global": yahoo_mock},
            rate_limiter=MagicMock(),
        )
        orch.run_once(groups=["I"])

        # Group J/K yahoo source must not be called
        yahoo_mock.fetch_ohlcv.assert_not_called()

    def test_groups_filter_forwarded_to_scheduler(self, mem_store: MacroStorage) -> None:
        mock_scheduler = MagicMock()
        mock_scheduler.get_due_indicators.return_value = []

        orch = MacroOrchestrator(
            storage=mem_store,
            scheduler=mock_scheduler,
            sources={},
            rate_limiter=MagicMock(),
        )
        orch.run_once(groups=["I"])

        call_args = mock_scheduler.get_due_indicators.call_args
        # groups_filter=["I"] must be passed to scheduler
        kwargs = call_args.kwargs if call_args.kwargs else {}
        args = call_args.args if call_args.args else ()
        groups_filter = kwargs.get("groups_filter") or (
            args[1] if len(args) > 1 else None
        )
        assert groups_filter == ["I"]

    def test_only_group_i_written_to_storage(self, mem_store: MacroStorage) -> None:
        cfg_i = _make_indicator("CPIAUCSL", "I", primary_source="fred")

        mock_scheduler = MagicMock()
        mock_scheduler.get_due_indicators.return_value = [cfg_i]

        fred_mock = MagicMock()
        fred_mock.name = "fred"
        fred_mock.fetch_series.return_value = [
            _make_indicator_record("CPIAUCSL", "I", 3.2)
        ]

        orch = MacroOrchestrator(
            storage=mem_store,
            scheduler=mock_scheduler,
            sources={"fred": fred_mock},
            rate_limiter=MagicMock(),
        )
        orch.run_once(groups=["I"])

        rows = mem_store._conn.execute(
            "SELECT DISTINCT group_code FROM macro_indicators"
        ).fetchall()
        group_codes = {r[0] for r in rows}
        assert group_codes == {"I"}, (
            f"only Group I should be written, found: {group_codes}"
        )
