import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.services.open_ai import (
    get_answer_from_openai,
    get_answer_stream_from_openai,
    _truncate_to_tokens,
    _count_tokens
)

# ---------- Tests: get_answer_from_openai (REST) ----------

@pytest.mark.asyncio
@patch("app.services.open_ai.get_openai_client")
async def test_get_answer_from_openai_success(mock_get_client):
    """Test successful OpenAI completion response (first model succeeds)."""
    # Arrange
    fake_response = AsyncMock()
    fake_response.choices = [AsyncMock()]
    fake_response.choices[0].message.content = "Test answer"
    fake_response.usage.total_tokens = 123

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = fake_response
    mock_get_client.return_value = mock_client

    # Act
    result = await get_answer_from_openai("context text", "What is the contract value?")

    # Assert
    assert result["text"] == "Test answer"
    assert result["tokens_used"] == 123
    assert result["model"] is not None


@pytest.mark.asyncio
@patch("app.services.open_ai.get_openai_client")
async def test_get_answer_from_openai_all_models_fail(mock_get_client):
    """Test fallback behavior when both primary and fallback models fail."""
    # Arrange
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("OpenAI down")
    mock_get_client.return_value = mock_client

    # Act
    result = await get_answer_from_openai("context text", "Any question")

    # Assert
    assert result["text"].startswith("All models failed")
    assert result["tokens_used"] == 0
    assert result["model"] is None


# ---------- Tests: get_answer_stream_from_openai (WebSocket) ----------

@pytest.mark.asyncio
@patch("app.services.open_ai.get_openai_client")
async def test_get_answer_stream_from_openai(mock_get_client):
    """Test streaming token response from OpenAI."""
    # Arrange
    mock_chunk = AsyncMock()
    mock_chunk.choices = [AsyncMock()]
    mock_chunk.choices[0].delta.content = "Hello, "

    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = [mock_chunk]

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_stream
    mock_get_client.return_value = mock_client

    # Act
    result = []
    async for token in get_answer_stream_from_openai("context", "question"):
        result.append(token)

    # Assert
    assert result == ["Hello, "]


# ---------- Tests: Utility Functions ----------

def test_truncate_to_tokens_no_encoder():
    """Test that _truncate_to_tokens reduces text when no encoder is available."""
    long_text = "abc " * 1000
    result = _truncate_to_tokens(long_text, 100)

    assert isinstance(result, str)
    assert len(result) < len(long_text)


def test_count_tokens_basic():
    """Test _count_tokens returns a reasonable token estimate."""
    assert _count_tokens("Hello world") >= 2
