from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
from neo4j import Session

_QUERY_SHAREHOLDERS = """
SELECT DISTINCT holder_name, holder_type, code, hold_ratio, report_date
FROM stock_shareholders
WHERE hold_ratio IS NOT NULL
  AND code IN (SELECT code FROM stocks WHERE active = true)
ORDER BY holder_name, code
"""

_MERGE_INSTITUTION = """
MERGE (i:Institution {name: $name})
ON CREATE SET i.holder_type = $holder_type
"""

_MERGE_HOLDS = """
MATCH (i:Institution {name: $holder_name})
MATCH (s:Stock {code: $code})
MERGE (i)-[h:HOLDS {report_date: date($report_date)}]->(s)
ON CREATE SET h.hold_ratio = $hold_ratio
ON MATCH SET  h.hold_ratio = $hold_ratio
"""


@dataclass
class HoldsRow:
    holder_name: str
    holder_type: str
    code: str
    hold_ratio: float
    report_date: date


def load_from_duckdb(db_path: str) -> list[HoldsRow]:
    """Read shareholder data from DuckDB (read-only)."""
    con = duckdb.connect(db_path, read_only=True)
    try:
        rows = con.execute(_QUERY_SHAREHOLDERS).fetchall()
    finally:
        con.close()
    return [
        HoldsRow(
            holder_name=r[0],
            holder_type=r[1],
            code=r[2],
            hold_ratio=float(r[3]),
            report_date=r[4] if isinstance(r[4], date) else date.fromisoformat(str(r[4])),
        )
        for r in rows
    ]


def run_institution_load(session: Session, rows: list[HoldsRow]) -> None:
    """Upsert Institution nodes and HOLDS edges. Idempotent."""
    seen: set[str] = set()
    for r in rows:
        if r.holder_name not in seen:
            session.run(_MERGE_INSTITUTION, name=r.holder_name, holder_type=r.holder_type)
            seen.add(r.holder_name)
    for r in rows:
        session.run(
            _MERGE_HOLDS,
            holder_name=r.holder_name,
            code=r.code,
            hold_ratio=r.hold_ratio,
            report_date=str(r.report_date),
        )
