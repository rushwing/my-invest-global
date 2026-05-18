"""TC-021-01..04 — KGConnection ping/close and run_schema_init idempotency."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

_conn_mod = pytest.importorskip(
    "engine.kg.connection",
    reason="engine.kg.connection not yet implemented (pending req_impl)",
)
_schema_mod = pytest.importorskip(
    "engine.kg.schema",
    reason="engine.kg.schema not yet implemented (pending req_impl)",
)

KGSettings = _conn_mod.KGSettings
KGConnection = _conn_mod.KGConnection
CONSTRAINTS = _schema_mod.CONSTRAINTS
INDEXES = _schema_mod.INDEXES
run_schema_init = _schema_mod.run_schema_init

_SETTINGS = KGSettings(neo4j_uri="bolt://test:7687", neo4j_user="neo4j", neo4j_password="pw")


def _conn_with_mock_driver(verify_side_effect=None):
    mock_driver = MagicMock()
    if verify_side_effect is not None:
        mock_driver.verify_connectivity.side_effect = verify_side_effect
    conn = KGConnection(_SETTINGS)
    conn._driver = mock_driver
    return conn, mock_driver


# ── TC-021-01 ──────────────────────────────────────────────────────────────────


class TestPingTrue:
    """TC-021-01: ping() returns True when verify_connectivity succeeds."""

    def test_returns_true(self):
        conn, mock_driver = _conn_with_mock_driver()
        assert conn.ping() is True

    def test_verify_called_once(self):
        conn, mock_driver = _conn_with_mock_driver()
        conn.ping()
        mock_driver.verify_connectivity.assert_called_once()


# ── TC-021-02 ──────────────────────────────────────────────────────────────────


class TestPingFalse:
    """TC-021-02: ping() swallows connectivity exceptions and returns False."""

    def test_returns_false_on_runtime_error(self):
        conn, _ = _conn_with_mock_driver(verify_side_effect=RuntimeError("down"))
        assert conn.ping() is False

    def test_no_exception_propagated(self):
        conn, _ = _conn_with_mock_driver(verify_side_effect=Exception("refused"))
        try:
            result = conn.ping()
        except Exception:
            pytest.fail("ping() raised an exception instead of returning False")
        assert result is False


# ── TC-021-03 ──────────────────────────────────────────────────────────────────


class TestRunSchemaInit:
    """TC-021-03: run_schema_init calls session.run for every CONSTRAINT + INDEX with IF NOT EXISTS."""

    def _make_conn_with_session(self):
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)
        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_cm
        conn = KGConnection(_SETTINGS)
        conn._driver = mock_driver
        return conn, mock_session

    def test_call_count_equals_constraints_plus_indexes(self):
        conn, mock_session = self._make_conn_with_session()
        run_schema_init(conn)
        expected = len(CONSTRAINTS) + len(INDEXES)
        assert mock_session.run.call_count == expected

    def test_all_statements_contain_if_not_exists(self):
        conn, mock_session = self._make_conn_with_session()
        run_schema_init(conn)
        for call_args in mock_session.run.call_args_list:
            stmt = call_args.args[0]
            assert "IF NOT EXISTS" in stmt, f"Missing IF NOT EXISTS: {stmt!r}"


# ── TC-021-04 ──────────────────────────────────────────────────────────────────


class TestContextManager:
    """TC-021-04: __exit__ calls driver.close() and resets _driver to None."""

    def test_driver_closed_on_exit(self):
        conn, mock_driver = _conn_with_mock_driver()
        with conn:
            assert conn._driver is mock_driver
        mock_driver.close.assert_called_once()

    def test_driver_none_after_exit(self):
        conn, _ = _conn_with_mock_driver()
        with conn:
            pass
        assert conn._driver is None
