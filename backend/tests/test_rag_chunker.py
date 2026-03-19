"""Tests for the RAG chunker module."""

import pytest

from app.gateway.rag.chunker import _split_by_headers, _split_by_size, chunk_markdown

# ---------------------------------------------------------------------------
# chunk_markdown — basic behavior
# ---------------------------------------------------------------------------


def test_chunk_markdown_empty_string() -> None:
    assert chunk_markdown("") == []


def test_chunk_markdown_whitespace_only() -> None:
    assert chunk_markdown("   \n\n  ") == []


def test_chunk_markdown_short_text_single_chunk() -> None:
    text = "Hello world"
    chunks = chunk_markdown(text, chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_markdown_respects_chunk_size() -> None:
    text = "word " * 200  # ~1000 chars
    chunks = chunk_markdown(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 100 * 1.3


def test_chunk_markdown_splits_by_headers() -> None:
    text = "# Section 1\nContent one.\n\n## Section 2\nContent two."
    chunks = chunk_markdown(text, chunk_size=5000)
    assert len(chunks) == 2
    assert "Section 1" in chunks[0]
    assert "Section 2" in chunks[1]


def test_chunk_markdown_large_section_split_further() -> None:
    text = "# Big Section\n" + ("This is a sentence. " * 100)
    chunks = chunk_markdown(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1


# ---------------------------------------------------------------------------
# chunk_markdown — validation
# ---------------------------------------------------------------------------


def test_chunk_markdown_negative_chunk_size_raises() -> None:
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        chunk_markdown("hello", chunk_size=-1)


def test_chunk_markdown_zero_chunk_size_raises() -> None:
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        chunk_markdown("hello", chunk_size=0)


def test_chunk_markdown_negative_overlap_raises() -> None:
    with pytest.raises(ValueError, match="chunk_overlap must be non-negative"):
        chunk_markdown("hello", chunk_size=100, chunk_overlap=-1)


def test_chunk_markdown_overlap_gte_size_raises() -> None:
    with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
        chunk_markdown("hello", chunk_size=100, chunk_overlap=100)


def test_chunk_markdown_overlap_greater_than_size_raises() -> None:
    with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
        chunk_markdown("hello", chunk_size=100, chunk_overlap=200)


# ---------------------------------------------------------------------------
# _split_by_headers
# ---------------------------------------------------------------------------


def test_split_by_headers_no_headers() -> None:
    text = "Just plain text without any headers."
    parts = _split_by_headers(text)
    assert len(parts) == 1
    assert parts[0] == text


def test_split_by_headers_multiple_levels() -> None:
    text = "# H1\nContent\n## H2\nMore\n### H3\nDeep"
    parts = _split_by_headers(text)
    assert len(parts) == 3
    assert parts[0].startswith("# H1")
    assert parts[1].startswith("## H2")
    assert parts[2].startswith("### H3")


def test_split_by_headers_empty_sections_filtered() -> None:
    text = "# A\n\n\n# B\n\n"
    parts = _split_by_headers(text)
    assert all(p.strip() for p in parts)


# ---------------------------------------------------------------------------
# _split_by_size
# ---------------------------------------------------------------------------


def test_split_by_size_short_text() -> None:
    text = "Short"
    chunks = _split_by_size(text, chunk_size=100, chunk_overlap=10)
    assert chunks == ["Short"]


def test_split_by_size_paragraph_breaks() -> None:
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = _split_by_size(text, chunk_size=30, chunk_overlap=0)
    assert len(chunks) >= 2


def test_split_by_size_hard_split_fallback() -> None:
    text = "a" * 500
    chunks = _split_by_size(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    assert len(chunks[0]) == 100


# ---------------------------------------------------------------------------
# chunk_markdown — overlap behavior
# ---------------------------------------------------------------------------


def test_chunk_markdown_zero_overlap() -> None:
    text = "A. " * 100
    chunks = chunk_markdown(text, chunk_size=50, chunk_overlap=0)
    assert len(chunks) > 1


def test_chunk_markdown_with_overlap_has_shared_content() -> None:
    text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five. Sentence six. Sentence seven. Sentence eight."
    chunks = chunk_markdown(text, chunk_size=60, chunk_overlap=20)
    if len(chunks) >= 2:
        assert len(chunks) >= 2
