from __future__ import annotations

import lancedb
from lancedb.pydantic import LanceModel, Vector


class DocChunk(LanceModel):
    chunk_id: str        # "{doc_id}_{chunk_index:04d}"
    doc_id: str
    title: str
    doc_type: str        # "annual_report" | "research_report" | "announcement" | "news"
    pub_date: str        # ISO date string "YYYY-MM-DD"
    source: str          # "cninfo" | "eastmoney" | "akshare" | "local"
    code: str            # primary stock code; empty string if multi-stock document
    chunk_index: int
    chunk_total: int
    text: str
    vector: Vector(1024)  # type: ignore[valid-type]  # BGE-M3 dense embedding


class RAGSchema:
    TABLE_NAME = "doc_chunks"

    @staticmethod
    def create_table(db: lancedb.LanceDBConnection) -> lancedb.table.LanceTable:
        """Idempotent: returns existing table if already created."""
        return db.create_table(RAGSchema.TABLE_NAME, schema=DocChunk, exist_ok=True)
