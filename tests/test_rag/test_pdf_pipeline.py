"""TC-026-01..05 — RAG PDF pipeline: parse, ingest, retrieve, download."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

_parser_mod = pytest.importorskip(
    "engine.rag.pdf_parser",
    reason="engine.rag.pdf_parser not yet implemented (pending req_impl)",
)
_ingest_mod = pytest.importorskip(
    "engine.rag.ingest",
    reason="engine.rag.ingest not yet implemented (pending req_impl)",
)
_retriever_mod = pytest.importorskip(
    "engine.rag.retriever",
    reason="engine.rag.retriever not yet implemented (pending req_impl)",
)
_fetcher_mod = pytest.importorskip(
    "engine.rag.pdf_fetcher",
    reason="engine.rag.pdf_fetcher not yet implemented (pending req_impl)",
)
lancedb = pytest.importorskip("lancedb", reason="lancedb not installed (rag optional group)")

parse_pdf_to_chunks = _parser_mod.parse_pdf_to_chunks
ParsedChunk = _parser_mod.ParsedChunk
DocMeta = _ingest_mod.DocMeta
ingest_pdf = _ingest_mod.ingest_pdf
RetrieveResult = _retriever_mod.RetrieveResult
retrieve = _retriever_mod.retrieve
AnnualReportMeta = _fetcher_mod.AnnualReportMeta
download_pdf = _fetcher_mod.download_pdf

_CHUNK_ID_RE = re.compile(r"^.+_\d{4}$")


def _mock_embedder() -> MagicMock:
    emb = MagicMock()
    emb.embed.side_effect = lambda texts, **_: np.zeros((len(texts), 1024))
    return emb


def _meta(doc_id: str = "annual2025") -> DocMeta:
    return DocMeta(
        doc_id=doc_id,
        title="2025年报",
        doc_type="annual_report",
        pub_date="2026-01-01",
        source="cninfo",
        code="300308",
    )


def _annual_report_meta() -> AnnualReportMeta:
    return AnnualReportMeta(
        code="300308",
        year=2025,
        doc_id="abc123",
        title="2025年报",
        pub_date="2026-01-01",
        pdf_url="https://static.cninfo.com.cn/test.pdf",
    )


# ── TC-026-01 ──────────────────────────────────────────────────────────────────


class TestParsePdfToChunks:
    """TC-026-01: parse_pdf_to_chunks generates non-empty chunks with consecutive chunk_index."""

    def _make_mock_doc(self, n_pages: int, words_per_page: int):
        page_text = " ".join(f"word{i}" for i in range(words_per_page))
        mock_page = MagicMock()
        mock_page.get_text.return_value = page_text
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page] * n_pages))
        return mock_doc

    def test_produces_at_least_one_chunk(self):
        mock_doc = self._make_mock_doc(n_pages=3, words_per_page=300)
        with patch("fitz.open", return_value=mock_doc):
            chunks = parse_pdf_to_chunks(Path("mock.pdf"))
        assert len(chunks) >= 1

    def test_all_chunks_have_nonempty_text(self):
        mock_doc = self._make_mock_doc(n_pages=3, words_per_page=300)
        with patch("fitz.open", return_value=mock_doc):
            chunks = parse_pdf_to_chunks(Path("mock.pdf"))
        for c in chunks:
            assert c.text.strip() != ""

    def test_chunk_index_consecutive_from_zero(self):
        mock_doc = self._make_mock_doc(n_pages=3, words_per_page=300)
        with patch("fitz.open", return_value=mock_doc):
            chunks = parse_pdf_to_chunks(Path("mock.pdf"))
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_page_start_le_page_end(self):
        mock_doc = self._make_mock_doc(n_pages=3, words_per_page=300)
        with patch("fitz.open", return_value=mock_doc):
            chunks = parse_pdf_to_chunks(Path("mock.pdf"))
        for c in chunks:
            assert c.page_start <= c.page_end


# ── TC-026-02 ──────────────────────────────────────────────────────────────────


class TestIngestPdf:
    """TC-026-02: ingest_pdf returns chunk count and writes all rows to LanceDB."""

    def _chunks(self, n: int) -> list[ParsedChunk]:
        return [
            ParsedChunk(text=f"chunk text {i}", chunk_index=i, page_start=0, page_end=0)
            for i in range(n)
        ]

    def test_returns_correct_count(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        result = ingest_pdf(_meta(), self._chunks(3), db, _mock_embedder())
        assert result == 3

    def test_table_row_count_matches(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        ingest_pdf(_meta(), self._chunks(3), db, _mock_embedder())
        from engine.rag.schema import RAGSchema
        rows = db.open_table(RAGSchema.TABLE_NAME).to_pandas()
        assert len(rows) == 3

    def test_chunk_total_field_correct(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        ingest_pdf(_meta(), self._chunks(3), db, _mock_embedder())
        from engine.rag.schema import RAGSchema
        rows = db.open_table(RAGSchema.TABLE_NAME).to_pandas()
        assert (rows["chunk_total"] == 3).all()


# ── TC-026-03 ──────────────────────────────────────────────────────────────────


class TestRetrieve:
    """TC-026-03: retrieve returns RetrieveResult list with correctly formatted chunk_ids."""

    def _ingest_3_chunks(self, db):
        chunks = [
            ParsedChunk(text=f"液冷散热内容 {i}", chunk_index=i, page_start=0, page_end=0)
            for i in range(3)
        ]
        ingest_pdf(_meta(), chunks, db, _mock_embedder())

    def test_returns_list_of_retrieve_results(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        self._ingest_3_chunks(db)
        results = retrieve("液冷散热收入", db, _mock_embedder(), top_k_ann=3, top_k_final=2)
        assert isinstance(results, list)
        assert len(results) >= 1
        assert all(isinstance(r, RetrieveResult) for r in results)

    def test_chunk_id_format(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        self._ingest_3_chunks(db)
        results = retrieve("液冷散热", db, _mock_embedder(), top_k_ann=3, top_k_final=3)
        for r in results:
            assert _CHUNK_ID_RE.match(r.chunk_id), f"Bad chunk_id: {r.chunk_id!r}"

    def test_text_nonempty(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        self._ingest_3_chunks(db)
        results = retrieve("散热", db, _mock_embedder())
        for r in results:
            assert r.text.strip() != ""


# ── TC-026-04 ──────────────────────────────────────────────────────────────────


class TestIngestPdfSingleEmbedCall:
    """TC-026-04: ingest_pdf calls embedder.embed exactly once with all texts."""

    def test_single_embed_call(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        embedder = _mock_embedder()
        chunks = [
            ParsedChunk(text=f"text {i}", chunk_index=i, page_start=0, page_end=0)
            for i in range(3)
        ]
        ingest_pdf(_meta(), chunks, db, embedder)
        assert embedder.embed.call_count == 1

    def test_embed_receives_all_texts_in_order(self, tmp_path):
        db = lancedb.connect(str(tmp_path))
        embedder = _mock_embedder()
        chunks = [
            ParsedChunk(text=f"text {i}", chunk_index=i, page_start=0, page_end=0)
            for i in range(3)
        ]
        ingest_pdf(_meta(), chunks, db, embedder)
        call_texts = embedder.embed.call_args.args[0]
        assert call_texts == [c.text for c in chunks]


# ── TC-026-05 ──────────────────────────────────────────────────────────────────


class TestDownloadPdfShortCircuit:
    """TC-026-05: download_pdf returns existing file without HTTP call."""

    def test_skips_http_when_file_exists(self, tmp_path: Path):
        meta = _annual_report_meta()
        existing = tmp_path / "300308_2025_abc123.pdf"
        existing.write_bytes(b"existing content")

        with patch("httpx.stream") as mock_stream:
            result = download_pdf(meta, tmp_path)

        mock_stream.assert_not_called()
        assert result == existing

    def test_existing_file_content_unchanged(self, tmp_path: Path):
        meta = _annual_report_meta()
        existing = tmp_path / "300308_2025_abc123.pdf"
        original = b"do not overwrite"
        existing.write_bytes(original)

        with patch("httpx.stream"):
            download_pdf(meta, tmp_path)

        assert existing.read_bytes() == original
