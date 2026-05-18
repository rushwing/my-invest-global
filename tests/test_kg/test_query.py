"""TC-024-01..05 — KGQuerier: read-only guard and injection-based unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

_query_mod = pytest.importorskip(
    "engine.kg.query",
    reason="engine.kg.query not yet implemented (pending req_impl)",
)
_conn_mod = pytest.importorskip(
    "engine.kg.connection",
    reason="engine.kg.connection not yet implemented (pending req_impl)",
)

KGQuerier = _query_mod.KGQuerier
KGQueryResult = _query_mod.KGQueryResult
_is_write_cypher = _query_mod._is_write_cypher
KGSettings = _conn_mod.KGSettings
KGConnection = _conn_mod.KGConnection

_SETTINGS = KGSettings(neo4j_uri="bolt://test:7687", neo4j_user="neo4j", neo4j_password="pw")
_READ_CYPHER = (
    "MATCH (s:Stock)-[:BELONGS_TO]->(sub:SubSector {name: '光通信'}) RETURN s.code"
)
_WRITE_CYPHER = "MERGE (s:Stock {code: '300308'}) RETURN s"
_ANSWER = "中际旭创属于光通信"
_SCHEMA = "(:Stock {code})-[:BELONGS_TO]->(:SubSector {name})"


def _make_querier() -> KGQuerier:
    conn = KGConnection(_SETTINGS)
    conn._driver = MagicMock()
    return KGQuerier(conn)


def _mock_llm(*contents: str) -> MagicMock:
    """Mock LLM called as a callable by LangChain's RunnableLambda wrapper."""
    mock_llm = MagicMock()
    mock_llm.side_effect = [MagicMock(content=c) for c in contents]
    return mock_llm


# ── TC-024-01 ──────────────────────────────────────────────────────────────────


class TestQueryReadCypher:
    """TC-024-01: read Cypher → KGQueryResult with MATCH, correct answer, no error."""

    def _call(self):
        querier = _make_querier()
        runner = MagicMock(return_value=[{"s.code": "300308"}])
        result = querier.query(
            "光通信的股票",
            llm=_mock_llm(_READ_CYPHER, _ANSWER),
            schema=_SCHEMA,
            session_runner=runner,
        )
        return result, runner

    def test_cypher_contains_match(self):
        result, _ = self._call()
        assert "MATCH" in result.cypher_used

    def test_answer_correct(self):
        result, _ = self._call()
        assert result.answer == _ANSWER

    def test_error_is_none(self):
        result, _ = self._call()
        assert result.error is None

    def test_session_runner_called_once(self):
        _, runner = self._call()
        runner.assert_called_once()


# ── TC-024-02 ──────────────────────────────────────────────────────────────────


class TestQueryLlmException:
    """TC-024-02: LLM raises ValueError → result.error set, no propagation."""

    def _call(self):
        querier = _make_querier()
        mock_llm = MagicMock()
        mock_llm.side_effect = ValueError("timeout")
        runner = MagicMock()
        result = querier.query("问题", llm=mock_llm, schema=_SCHEMA, session_runner=runner)
        return result, runner

    def test_error_message(self):
        result, _ = self._call()
        assert result.error == "timeout"

    def test_answer_empty(self):
        result, _ = self._call()
        assert result.answer == ""

    def test_raw_results_empty(self):
        result, _ = self._call()
        assert result.raw_results == []

    def test_runner_not_called(self):
        _, runner = self._call()
        runner.assert_not_called()

    def test_no_exception_propagated(self):
        querier = _make_querier()
        mock_llm = MagicMock()
        mock_llm.side_effect = ValueError("timeout")
        try:
            querier.query("问题", llm=mock_llm, schema=_SCHEMA, session_runner=MagicMock())
        except Exception:
            pytest.fail("query() propagated an exception")


# ── TC-024-03 ──────────────────────────────────────────────────────────────────


class TestQueryWriteCypherBlocked:
    """TC-024-03: write Cypher → read_only_violation, session_runner never called."""

    def _call(self):
        querier = _make_querier()
        runner = MagicMock()
        result = querier.query(
            "创建股票",
            llm=_mock_llm(_WRITE_CYPHER),
            schema=_SCHEMA,
            session_runner=runner,
        )
        return result, runner

    def test_error_read_only_violation(self):
        result, _ = self._call()
        assert result.error == "read_only_violation"

    def test_cypher_used_contains_merge(self):
        result, _ = self._call()
        assert "MERGE" in result.cypher_used

    def test_answer_empty(self):
        result, _ = self._call()
        assert result.answer == ""

    def test_runner_never_called(self):
        _, runner = self._call()
        runner.assert_not_called()


# ── TC-024-04 ──────────────────────────────────────────────────────────────────


class TestIsWriteCypher:
    """TC-024-04: _is_write_cypher correctly classifies read vs write Cypher."""

    def test_match_return_is_read(self):
        assert _is_write_cypher("MATCH (n) RETURN n") is False

    def test_delete_is_write(self):
        assert _is_write_cypher("MATCH (n) DELETE n") is True

    def test_set_is_write(self):
        assert _is_write_cypher("MATCH (n) SET n.x=1") is True

    def test_merge_is_write(self):
        assert _is_write_cypher("MERGE (s:Stock {code: '300308'})") is True

    def test_case_insensitive(self):
        assert _is_write_cypher("match (n) delete n") is True


# ── TC-024-05 ──────────────────────────────────────────────────────────────────


class TestQueryInjectionIsolation:
    """TC-024-05: injected llm/schema/session_runner avoids real Neo4j calls."""

    def test_neo4j_graph_not_instantiated(self):
        querier = _make_querier()
        runner = MagicMock(return_value=[])
        with patch("engine.kg.query.Neo4jGraph") as mock_graph:
            querier.query(
                "问题",
                llm=_mock_llm("MATCH (n) RETURN n", "answer"),
                schema=_SCHEMA,
                session_runner=runner,
            )
        mock_graph.assert_not_called()

    def test_run_cypher_not_called(self):
        querier = _make_querier()
        runner = MagicMock(return_value=[])
        with patch.object(querier, "_run_cypher") as spy:
            querier.query(
                "问题",
                llm=_mock_llm("MATCH (n) RETURN n", "answer"),
                schema=_SCHEMA,
                session_runner=runner,
            )
        spy.assert_not_called()
        runner.assert_called_once()
