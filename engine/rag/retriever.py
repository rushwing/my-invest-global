from __future__ import annotations

from dataclasses import dataclass

import lancedb

from engine.rag.embedder import Embedder, Reranker
from engine.rag.schema import RAGSchema


@dataclass
class RetrieveResult:
    chunk_id: str
    doc_id: str
    text: str
    ann_score: float       # ANN distance (lower = closer for L2; higher for cosine)
    rerank_score: float | None


def retrieve(
    query: str,
    db: lancedb.LanceDBConnection,
    embedder: Embedder,
    top_k_ann: int = 20,
    top_k_final: int = 5,
    reranker: Reranker | None = None,
) -> list[RetrieveResult]:
    table = db.open_table(RAGSchema.TABLE_NAME)
    vec = embedder.embed([query])[0].tolist()
    rows = table.search(vec).limit(top_k_ann).to_list()
    results = [
        RetrieveResult(
            chunk_id=r["chunk_id"],
            doc_id=r["doc_id"],
            text=r["text"],
            ann_score=float(r.get("_distance", 0.0)),
            rerank_score=None,
        )
        for r in rows
    ]
    if reranker and results:
        scores = reranker.rerank(query, [r.text for r in results])
        for res, sc in zip(results, scores):
            res.rerank_score = sc
        results.sort(key=lambda x: x.rerank_score or 0.0, reverse=True)
    return results[:top_k_final]
