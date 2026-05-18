from __future__ import annotations

import re
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import Neo4jGraph
from pydantic import BaseModel

from engine.kg.connection import KGConnection

_WRITE_PATTERN = re.compile(
    r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|DETACH)\b",
    re.IGNORECASE,
)

_CYPHER_GENERATION_PROMPT = ChatPromptTemplate.from_template(
    "You are a Neo4j Cypher expert. Based on the schema below, write a Cypher MATCH query "
    "that answers the question. Return ONLY the Cypher statement, nothing else.\n\n"
    "Schema:\n{schema}\n\n"
    "Question: {question}\n\n"
    "Cypher:"
)

_ANSWER_PROMPT = ChatPromptTemplate.from_template(
    "Given the following Cypher query results, answer the question in Chinese.\n\n"
    "Question: {question}\n"
    "Results: {results}\n\n"
    "Answer:"
)


class KGQueryResult(BaseModel):
    question: str
    cypher_used: str
    raw_results: list[dict[str, Any]]
    answer: str
    error: str | None = None


def _is_write_cypher(cypher: str) -> bool:
    return bool(_WRITE_PATTERN.search(cypher))


class KGQuerier:
    def __init__(
        self,
        conn: KGConnection,
        model: str = "claude-haiku-4-5-20251001",
    ) -> None:
        self._conn = conn
        self._model = model
        self._schema: str | None = None
        self._llm: ChatAnthropic | None = None

    def _get_llm(self) -> ChatAnthropic:
        if self._llm is None:
            self._llm = ChatAnthropic(model=self._model, max_tokens=512)  # type: ignore[call-arg]
        return self._llm

    def _get_schema(self) -> str:
        if self._schema is None:
            graph = Neo4jGraph(
                url=self._conn._settings.neo4j_uri,
                username=self._conn._settings.neo4j_user,
                password=self._conn._settings.neo4j_password,
            )
            self._schema = graph.schema
        return self._schema

    def _generate_cypher(self, question: str) -> str:
        chain = _CYPHER_GENERATION_PROMPT | self._get_llm()
        result = chain.invoke({"schema": self._get_schema(), "question": question})
        return str(result.content).strip()

    def _run_cypher(self, cypher: str) -> list[dict[str, Any]]:
        with self._conn.driver().session() as session:
            result = session.run(cypher)
            return [dict(r) for r in result]

    def _summarize(self, question: str, results: list[dict[str, Any]]) -> str:
        chain = _ANSWER_PROMPT | self._get_llm()
        resp = chain.invoke({"question": question, "results": str(results)})
        return str(resp.content).strip()

    def query(
        self,
        question: str,
        *,
        llm: ChatAnthropic | None = None,
        schema: str | None = None,
        session_runner: Any = None,
    ) -> KGQueryResult:
        """
        Injecting `llm`, `schema`, `session_runner` enables full unit-test coverage
        without a live Neo4j connection.

        Pre-execution read-only guard: _is_write_cypher() is checked BEFORE any DB call.
        """
        try:
            if llm is not None:
                self._llm = llm
            if schema is not None:
                self._schema = schema

            cypher = self._generate_cypher(question)

            if _is_write_cypher(cypher):
                return KGQueryResult(
                    question=question,
                    cypher_used=cypher,
                    raw_results=[],
                    answer="",
                    error="read_only_violation",
                )

            run = session_runner if session_runner is not None else self._run_cypher
            raw: list[dict[str, Any]] = run(cypher)
            answer = self._summarize(question, raw)
            return KGQueryResult(
                question=question,
                cypher_used=cypher,
                raw_results=raw if isinstance(raw, list) else [],
                answer=answer,
            )
        except Exception as exc:
            return KGQueryResult(
                question=question,
                cypher_used="",
                raw_results=[],
                answer="",
                error=str(exc),
            )
