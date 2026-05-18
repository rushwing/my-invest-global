"""TC-025-01..05 — BGE-M3 Embedder lazy loading and LanceDB DocChunk schema."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

_embedder_mod = pytest.importorskip(
    "engine.rag.embedder",
    reason="engine.rag.embedder not yet implemented (pending req_impl)",
)
_schema_mod = pytest.importorskip(
    "engine.rag.schema",
    reason="engine.rag.schema not yet implemented (pending req_impl)",
)
lancedb = pytest.importorskip("lancedb", reason="lancedb not installed (rag optional group)")

Embedder = _embedder_mod.Embedder
DocChunk = _schema_mod.DocChunk
RAGSchema = _schema_mod.RAGSchema


# ── TC-025-01 ──────────────────────────────────────────────────────────────────


class TestEmbedShape:
    """TC-025-01: embed() returns (N, 1024) ndarray from BGE-M3 encode."""

    def _fake_model(self):
        m = MagicMock()
        m.encode.return_value = {"dense_vecs": np.zeros((1, 1024))}
        return m

    def test_shape_is_1_by_1024(self):
        embedder = Embedder(device="cpu")
        embedder._model = self._fake_model()
        result = embedder.embed(["测试文本"])
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1024)

    def test_encode_called_with_max_length_8192(self):
        fake = self._fake_model()
        embedder = Embedder(device="cpu")
        embedder._model = fake
        embedder.embed(["测试"])
        fake.encode.assert_called_once()
        _, kwargs = fake.encode.call_args
        assert kwargs.get("max_length") == 8192

    def test_encode_called_once_per_embed_call(self):
        fake = self._fake_model()
        fake.encode.return_value = {"dense_vecs": np.zeros((2, 1024))}
        embedder = Embedder(device="cpu")
        embedder._model = fake
        embedder.embed(["text A", "text B"])
        assert fake.encode.call_count == 1


# ── TC-025-02 ──────────────────────────────────────────────────────────────────


class TestCreateTable:
    """TC-025-02: create_table on a LanceDB connection returns a usable table."""

    def test_returns_table_with_add(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        table = RAGSchema.create_table(db)
        assert hasattr(table, "add")

    def test_table_name_matches_constant(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        table = RAGSchema.create_table(db)
        assert table.name == RAGSchema.TABLE_NAME


# ── TC-025-03 ──────────────────────────────────────────────────────────────────


class TestDocChunkValidation:
    """TC-025-03: constructing DocChunk without chunk_id raises Pydantic ValidationError."""

    def test_missing_chunk_id(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            DocChunk(
                doc_id="d1",
                title="Test",
                doc_type="annual_report",
                pub_date="2026-01-01",
                source="cninfo",
                code="300308",
                chunk_index=0,
                chunk_total=1,
                text="some text",
                vector=[0.0] * 1024,
            )
        assert "chunk_id" in str(exc_info.value)


# ── TC-025-04 ──────────────────────────────────────────────────────────────────


class TestCreateTableIdempotent:
    """TC-025-04: calling create_table twice on the same db does not raise."""

    def test_double_create_ok(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        t1 = RAGSchema.create_table(db)
        t2 = RAGSchema.create_table(db)
        assert hasattr(t1, "add")
        assert hasattr(t2, "add")


# ── TC-025-05 ──────────────────────────────────────────────────────────────────


class TestEmbedderLazyLoad:
    """TC-025-05: _model is None before any embed() call is made."""

    def test_model_none_on_init(self):
        embedder = Embedder(device="cpu")
        assert embedder._model is None

    def test_model_still_none_without_embed(self):
        # Constructing Embedder must not trigger FlagEmbedding import/download
        embedder = Embedder(device="cpu")
        # Access _model directly — should not change
        _ = embedder._model_name
        assert embedder._model is None
