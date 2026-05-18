"""TC-023-01..05 — Institution loader: HOLDS MERGE counts and DuckDB read-only."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

_inst_mod = pytest.importorskip(
    "engine.kg.institution_loader",
    reason="engine.kg.institution_loader not yet implemented (pending req_impl)",
)

HoldsRow = _inst_mod.HoldsRow
run_institution_load = _inst_mod.run_institution_load
load_from_duckdb = _inst_mod.load_from_duckdb
_MERGE_INSTITUTION = _inst_mod._MERGE_INSTITUTION
_MERGE_HOLDS = _inst_mod._MERGE_HOLDS


def _row(holder_name: str, code: str, holder_type: str = "公募基金") -> HoldsRow:
    return HoldsRow(
        holder_name=holder_name,
        holder_type=holder_type,
        code=code,
        hold_ratio=3.5,
        report_date=date(2026, 3, 31),
    )


# ── TC-023-01 ──────────────────────────────────────────────────────────────────


class TestRunInstitutionLoadCallCount:
    """TC-023-01: 2 institutions, 3 holdings → 5 session.run calls total."""

    _ROWS = [_row("机构A", "300308"), _row("机构A", "300502"), _row("机构B", "300308")]

    def test_total_call_count(self):
        session = MagicMock()
        run_institution_load(session, self._ROWS)
        assert session.run.call_count == 5

    def test_institution_merge_count(self):
        session = MagicMock()
        run_institution_load(session, self._ROWS)
        inst_calls = [c for c in session.run.call_args_list if c.args[0] == _MERGE_INSTITUTION]
        assert len(inst_calls) == 2

    def test_holds_merge_count(self):
        session = MagicMock()
        run_institution_load(session, self._ROWS)
        holds_calls = [c for c in session.run.call_args_list if c.args[0] == _MERGE_HOLDS]
        assert len(holds_calls) == 3


# ── TC-023-02 ──────────────────────────────────────────────────────────────────


class TestCypherIdempotency:
    """TC-023-02: MERGE present, no bare CREATE in institution Cypher strings."""

    @pytest.mark.parametrize("stmt", [_MERGE_INSTITUTION, _MERGE_HOLDS])
    def test_contains_merge(self, stmt: str):
        assert "MERGE" in stmt

    @pytest.mark.parametrize("stmt", [_MERGE_INSTITUTION, _MERGE_HOLDS])
    def test_no_bare_create(self, stmt: str):
        cleaned = stmt.replace("ON CREATE SET", "").replace("ON MATCH SET", "")
        assert "CREATE" not in cleaned, f"Bare CREATE found: {stmt!r}"


# ── TC-023-03 ──────────────────────────────────────────────────────────────────


class TestLoadFromDuckdbReadOnly:
    """TC-023-03: load_from_duckdb opens DuckDB with read_only=True."""

    def _make_mock_con(self):
        mock_con = MagicMock()
        mock_con.execute.return_value.fetchall.return_value = []
        return mock_con

    def test_connect_read_only(self):
        mock_con = self._make_mock_con()
        with patch("duckdb.connect", return_value=mock_con) as mock_connect:
            load_from_duckdb("data/db/aidc.duckdb")
            mock_connect.assert_called_once_with("data/db/aidc.duckdb", read_only=True)

    def test_returns_list(self):
        mock_con = self._make_mock_con()
        with patch("duckdb.connect", return_value=mock_con):
            result = load_from_duckdb("data/db/aidc.duckdb")
            assert isinstance(result, list)

    def test_close_called(self):
        mock_con = self._make_mock_con()
        with patch("duckdb.connect", return_value=mock_con):
            load_from_duckdb("data/db/aidc.duckdb")
            mock_con.close.assert_called_once()


# ── TC-023-04 ──────────────────────────────────────────────────────────────────


class TestLoadFromDuckdbDateParsing:
    """TC-023-04: string report_date from DuckDB is parsed to datetime.date."""

    def test_string_date_parsed(self):
        mock_con = MagicMock()
        mock_con.execute.return_value.fetchall.return_value = [
            ("机构A", "公募基金", "300308", 3.5, "2026-03-31"),
        ]
        with patch("duckdb.connect", return_value=mock_con):
            rows = load_from_duckdb("mock.duckdb")
        assert len(rows) == 1
        assert rows[0].report_date == date(2026, 3, 31)
        assert rows[0].hold_ratio == 3.5


# ── TC-023-05 ──────────────────────────────────────────────────────────────────


class TestRunInstitutionLoadEmpty:
    """TC-023-05: empty rows → session.run never called."""

    def test_no_calls_on_empty_input(self):
        session = MagicMock()
        run_institution_load(session, [])
        session.run.assert_not_called()
