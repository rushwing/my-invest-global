from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CHUNK_TOKENS = 800
OVERLAP_TOKENS = 128


@dataclass
class ParsedChunk:
    text: str
    chunk_index: int
    page_start: int   # first page (0-indexed) contributing to this chunk
    page_end: int     # last page (inclusive)


def parse_pdf_to_chunks(
    pdf_path: Path,
    chunk_tokens: int = CHUNK_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[ParsedChunk]:
    """Sliding window word-level chunker using pymupdf for text extraction."""
    import fitz  # lazy import to keep tests fast when fitz is mocked

    doc = fitz.open(pdf_path)
    page_texts = [page.get_text() for page in doc]
    doc.close()

    full_words: list[str] = []
    word_page: list[int] = []
    for page_idx, text in enumerate(page_texts):
        words = text.split()
        full_words.extend(words)
        word_page.extend([page_idx] * len(words))

    chunks: list[ParsedChunk] = []
    step = max(1, chunk_tokens - overlap_tokens)
    total = len(full_words)
    i = 0
    while i < total:
        end = min(i + chunk_tokens, total)
        chunk_words = full_words[i:end]
        if not chunk_words:
            break
        chunks.append(ParsedChunk(
            text=" ".join(chunk_words),
            chunk_index=len(chunks),
            page_start=word_page[i],
            page_end=word_page[end - 1],
        ))
        i += step
    return chunks
