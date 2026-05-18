from __future__ import annotations

from engine.kg.connection import KGConnection

CONSTRAINTS: list[str] = [
    "CREATE CONSTRAINT stock_code_unique IF NOT EXISTS FOR (s:Stock) REQUIRE s.code IS UNIQUE",
    "CREATE CONSTRAINT sector_id_unique IF NOT EXISTS FOR (s:Sector) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT subsector_id_unique IF NOT EXISTS"
    " FOR (s:SubSector) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT concept_id_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT institution_name_unique IF NOT EXISTS"
    " FOR (i:Institution) REQUIRE i.name IS UNIQUE",
    "CREATE CONSTRAINT document_id_unique IF NOT EXISTS"
    " FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
]

INDEXES: list[str] = [
    "CREATE INDEX stock_name_idx IF NOT EXISTS FOR (s:Stock) ON (s.name)",
    "CREATE INDEX concept_theme_idx IF NOT EXISTS FOR (c:Concept) ON (c.theme)",
    "CREATE INDEX document_type_idx IF NOT EXISTS FOR (d:Document) ON (d.doc_type)",
]


def run_schema_init(conn: KGConnection) -> None:
    """Idempotent: safe to call multiple times."""
    with conn.driver().session() as session:
        for stmt in CONSTRAINTS + INDEXES:
            session.run(stmt)
