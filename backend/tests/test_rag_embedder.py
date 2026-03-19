"""Tests for the RAG embedder module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.gateway.rag.embedder import embed_text, embed_texts


@pytest.mark.asyncio
async def test_embed_texts_empty_list() -> None:
    result = await embed_texts([])
    assert result == []


@pytest.mark.asyncio
async def test_embed_texts_no_api_key_raises() -> None:
    with patch("app.gateway.rag.embedder.os.getenv", return_value=None):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            await embed_texts(["hello"])


@pytest.mark.asyncio
async def test_embed_texts_calls_openai_api() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"index": 0, "embedding": [0.1, 0.2, 0.3]},
            {"index": 1, "embedding": [0.4, 0.5, 0.6]},
        ]
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.gateway.rag.embedder.os.getenv", side_effect=lambda k, d=None: "test-key" if k == "OPENAI_API_KEY" else d),
        patch("app.gateway.rag.embedder.httpx.AsyncClient", return_value=mock_client),
    ):
        result = await embed_texts(["hello", "world"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.4, 0.5, 0.6]


@pytest.mark.asyncio
async def test_embed_texts_sorts_by_index() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"index": 1, "embedding": [0.4, 0.5]},
            {"index": 0, "embedding": [0.1, 0.2]},
        ]
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.gateway.rag.embedder.os.getenv", side_effect=lambda k, d=None: "test-key" if k == "OPENAI_API_KEY" else d),
        patch("app.gateway.rag.embedder.httpx.AsyncClient", return_value=mock_client),
    ):
        result = await embed_texts(["a", "b"])

    assert result[0] == [0.1, 0.2]
    assert result[1] == [0.4, 0.5]


@pytest.mark.asyncio
async def test_embed_text_delegates_to_embed_texts() -> None:
    with patch("app.gateway.rag.embedder.embed_texts", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        result = await embed_text("hello")

    assert result == [0.1, 0.2, 0.3]
    mock_embed.assert_awaited_once_with(["hello"], model="text-embedding-3-small")


@pytest.mark.asyncio
async def test_embed_text_custom_model() -> None:
    with patch("app.gateway.rag.embedder.embed_texts", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [[0.7, 0.8]]
        result = await embed_text("test", model="text-embedding-3-large")

    mock_embed.assert_awaited_once_with(["test"], model="text-embedding-3-large")
    assert result == [0.7, 0.8]
