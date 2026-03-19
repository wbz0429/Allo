"""Text chunking for RAG pipeline.

Splits markdown text by headers first, then by size using a recursive
character text splitter approach.
"""

import re


def _split_by_headers(text: str) -> list[str]:
    """Split markdown text into sections by header boundaries.

    Args:
        text: Markdown text to split.

    Returns:
        List of text sections, each starting with a header (if present).
    """
    # Split on markdown headers (##, ###, etc.) keeping the header with its content
    parts = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _split_by_size(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into chunks of approximately chunk_size characters.

    Uses paragraph breaks, then sentence breaks, then word breaks as separators.

    Args:
        text: Text to split.
        chunk_size: Target maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.

    Returns:
        List of text chunks.
    """
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", " "]
    return _recursive_split(text, separators, chunk_size, chunk_overlap)


def _recursive_split(text: str, separators: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """Recursively split text using a hierarchy of separators.

    Args:
        text: Text to split.
        separators: Ordered list of separators to try (coarsest first).
        chunk_size: Target maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.

    Returns:
        List of text chunks.
    """
    if len(text) <= chunk_size:
        return [text]

    if not separators:
        # Last resort: hard split at chunk_size
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - chunk_overlap if end < len(text) else end
        return chunks

    sep = separators[0]
    remaining_seps = separators[1:]

    parts = text.split(sep)
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = (current + sep + part).strip() if current else part.strip()

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If this single part exceeds chunk_size, split it further
            if len(part.strip()) > chunk_size:
                sub_chunks = _recursive_split(part.strip(), remaining_seps, chunk_size, chunk_overlap)
                chunks.extend(sub_chunks)
                current = ""
            else:
                current = part.strip()

    if current:
        chunks.append(current)

    # Apply overlap between chunks
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            overlap_text = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
            # Only prepend overlap if it doesn't make the chunk too large
            candidate = overlap_text + " " + chunks[i]
            if len(candidate) <= chunk_size * 1.2:
                overlapped.append(candidate)
            else:
                overlapped.append(chunks[i])
        return overlapped

    return chunks


def chunk_markdown(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Split markdown text into chunks suitable for embedding.

    Strategy:
    1. Split by markdown headers into sections.
    2. For each section, if it exceeds chunk_size, split further by size.

    Args:
        text: Markdown text to chunk.
        chunk_size: Target maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between adjacent chunks.

    Returns:
        List of text chunks. Empty list if input is empty.
    """
    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    sections = _split_by_headers(text)
    chunks: list[str] = []

    for section in sections:
        if len(section) <= chunk_size:
            chunks.append(section)
        else:
            sub_chunks = _split_by_size(section, chunk_size, chunk_overlap)
            chunks.extend(sub_chunks)

    return chunks
