from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

_DEFAULT_MODEL = "BAAI/bge-m3"
_DEFAULT_RERANKER = "BAAI/bge-reranker-v2-m3"


class Embedder:
    """Lazy-loaded BGE-M3 dense embedder. Model downloaded once to HF cache."""

    def __init__(self, model_name: str = _DEFAULT_MODEL, device: str = "cpu") -> None:
        self._model_name = model_name
        self._device = device
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from FlagEmbedding import BGEM3FlagModel  # lazy: avoids torch load on import
            self._model = BGEM3FlagModel(self._model_name, use_fp16=False, device=self._device)
        return self._model

    def embed(self, texts: list[str], batch_size: int = 12) -> npt.NDArray[np.float32]:
        """Return dense vectors, shape (len(texts), 1024)."""
        model = self._get_model()
        raw: Any = model.encode(texts, batch_size=batch_size, max_length=8192)
        vecs: npt.NDArray[np.float32] = raw["dense_vecs"]
        return vecs


class Reranker:
    """BGE-reranker-v2-m3 cross-encoder for ANN result re-ranking."""

    def __init__(self, model_name: str = _DEFAULT_RERANKER, device: str = "cpu") -> None:
        from FlagEmbedding import FlagReranker
        self._reranker: Any = FlagReranker(model_name, use_fp16=False, device=device)

    def rerank(self, query: str, passages: list[str]) -> list[float]:
        """Return relevance scores (higher = more relevant) for each passage."""
        pairs = [[query, p] for p in passages]
        return [float(s) for s in self._reranker.compute_score(pairs)]
