from __future__ import annotations

from dataclasses import dataclass

import lancedb

from engine.rag.embedder import Embedder
from engine.rag.pdf_parser import ParsedChunk
from engine.rag.schema import DocChunk, RAGSchema


@dataclass
class DocMeta:
    doc_id: str
    title: str
    doc_type: str   # "annual_report" | "research_report" | "announcement" | "news"
    pub_date: str   # ISO date
    source: str
    code: str


def ingest_pdf(
    meta: DocMeta,
    chunks: list[ParsedChunk],
    db: lancedb.LanceDBConnection,
    embedder: Embedder,
) -> int:
    """Embed and store chunks. Returns number of rows inserted."""
    table = RAGSchema.create_table(db)
    texts = [c.text for c in chunks]
    vectors = embedder.embed(texts)
    rows = [
        DocChunk(
            chunk_id=f"{meta.doc_id}_{c.chunk_index:04d}",
            doc_id=meta.doc_id,
            title=meta.title,
            doc_type=meta.doc_type,
            pub_date=meta.pub_date,
            source=meta.source,
            code=meta.code,
            chunk_index=c.chunk_index,
            chunk_total=len(chunks),
            text=c.text,
            vector=vectors[i].tolist(),
        )
        for i, c in enumerate(chunks)
    ]
    table.add([r.model_dump() for r in rows])
    return len(rows)
