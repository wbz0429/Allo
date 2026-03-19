"""Embedding generation via OpenAI API.

Calls the OpenAI embeddings endpoint directly via httpx (no langchain dependency).
"""

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")


async def embed_texts(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """Generate embeddings for a list of texts using the OpenAI API.

    Args:
        texts: List of text strings to embed.
        model: OpenAI embedding model name.

    Returns:
        List of embedding vectors (each a list of floats), one per input text.

    Raises:
        ValueError: If OPENAI_API_KEY is not set.
        httpx.HTTPStatusError: If the API returns an error status.
    """
    if not texts:
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for embeddings")

    url = f"{OPENAI_API_BASE}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": texts,
        "model": model,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    data = response.json()
    # Sort by index to ensure correct ordering
    embeddings_data = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in embeddings_data]


async def embed_text(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """Generate an embedding for a single text string.

    Args:
        text: Text to embed.
        model: OpenAI embedding model name.

    Returns:
        Embedding vector as a list of floats.
    """
    results = await embed_texts([text], model=model)
    return results[0]
