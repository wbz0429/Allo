"""Cosine similarity retriever for RAG pipeline.

Performs in-memory cosine similarity search over stored chunk embeddings.
Embeddings are stored as JSON text in the database.
"""

import json
import logging
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.db.models import KnowledgeChunk

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Cosine similarity score in [-1, 1].
    """
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


async def search_chunks(
    db: AsyncSession,
    query_embedding: list[float],
    kb_id: str,
    top_k: int = 5,
) -> list[dict]:
    """Search for the most relevant chunks in a knowledge base.

    Loads all chunk embeddings for the given KB, computes cosine similarity
    against the query embedding, and returns the top-k results.

    Args:
        db: Async database session.
        query_embedding: Embedding vector of the search query.
        kb_id: Knowledge base ID to search within.
        top_k: Number of top results to return.

    Returns:
        List of dicts with keys: id, content, score, chunk_index, doc_id, metadata_json.
    """
    stmt = select(KnowledgeChunk).where(KnowledgeChunk.kb_id == kb_id)
    result = await db.execute(stmt)
    chunks = result.scalars().all()

    if not chunks:
        return []

    scored: list[tuple[float, KnowledgeChunk]] = []
    for chunk in chunks:
        try:
            embedding = json.loads(chunk.embedding)
        except (json.JSONDecodeError, TypeError):
            continue

        if not embedding:
            continue

        score = _cosine_similarity(query_embedding, embedding)
        scored.append((score, chunk))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, chunk in scored[:top_k]:
        results.append(
            {
                "id": chunk.id,
                "content": chunk.content,
                "score": round(score, 4),
                "chunk_index": chunk.chunk_index,
                "doc_id": chunk.doc_id,
                "metadata_json": chunk.metadata_json,
            }
        )

    return results
