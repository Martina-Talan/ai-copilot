import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from langchain_core.documents import Document

os.environ["FAISS_STORE_PATH"] = "tests/faiss_test_index"
os.makedirs("tests/faiss_test_index", exist_ok=True)

from app.services.rag import get_qa_service


# ---------- Helper ----------

async def async_gen(tokens):
    for token in tokens:
        yield token


# ---------- Fixtures ----------

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def qa_service():
    return get_qa_service()


@pytest.fixture
def mock_chunks():
    return [
        Document(
            page_content="Test content page 1",
            metadata={
                "pageNumber": 1,
                "heading": "Intro",
                "chunkId": "c1",
                "vec_score": 0.9,
                "fusion_score": 0.95,
            },
        ),
        Document(
            page_content="Test content page 2",
            metadata={
                "pageNumber": 2,
                "heading": "Details",
                "chunkId": "c2",
                "vec_score": 0.8,
                "fusion_score": 0.85,
            },
        ),
    ]


# ---------- ask_question Tests ----------

@pytest.mark.anyio
async def test_ask_question_success(mock_chunks, qa_service):
    with patch.object(qa_service, "hybrid_retrieve", AsyncMock(return_value=mock_chunks)), \
         patch(
             "app.services.rag.get_answer_stream_from_openai",
             return_value=async_gen(["Part1 ", "Part2"]),
         ):

        result = await qa_service.ask_question("What is this?", "doc-123")

        assert result["documentId"] == "doc-123"
        assert result["answer"]["text"] == "Part1 Part2"
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) == 2
        assert result["sources"][0]["pageNumber"] == 1
        assert result["sources"][0]["chunkId"] == "c1"


@pytest.mark.anyio
async def test_ask_question_missing_input(qa_service):
    with pytest.raises(HTTPException) as exc:
        await qa_service.ask_question("", "doc-id")

    assert exc.value.status_code == 400
    assert "required" in exc.value.detail


@pytest.mark.anyio
async def test_ask_question_no_chunks(qa_service):
    with patch.object(qa_service, "hybrid_retrieve", AsyncMock(return_value=[])):
        with pytest.raises(HTTPException) as exc:
            await qa_service.ask_question("Hello?", "doc-404")

        assert exc.value.status_code == 404
        assert "No relevant content found" in exc.value.detail


# ---------- stream_answer Tests ----------

@pytest.mark.anyio
async def test_stream_answer_success(mock_chunks, qa_service):
    with patch.object(qa_service, "hybrid_retrieve", AsyncMock(return_value=mock_chunks)), \
         patch(
             "app.services.rag.get_answer_stream_from_openai",
             return_value=async_gen(["A", "B", "C"]),
         ):

        events = []
        async for event in qa_service.stream_answer("Explain X", "doc-xyz"):
            events.append(event)

        assert events[0]["type"] == "sources"

        answer_events = [e for e in events if e["type"] == "answer"]
        assert [e["token"] for e in answer_events] == ["A", "B", "C"]

        source_ref_event = next(e for e in events if e["type"] == "source_references")
        assert source_ref_event["chunkIds"] == ["c1", "c2"]
        assert source_ref_event["pageNumbers"] == [1, 2]
        assert source_ref_event["fullAnswer"] == "ABC"

        assert events[-1]["type"] == "done"


@pytest.mark.anyio
async def test_stream_answer_missing_input(qa_service):
    events = []
    async for event in qa_service.stream_answer("", ""):
        events.append(event)

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "required" in events[0]["message"]


@pytest.mark.anyio
async def test_stream_answer_no_chunks(qa_service):
    with patch.object(qa_service, "hybrid_retrieve", AsyncMock(return_value=[])):
        events = []
        async for event in qa_service.stream_answer("Who?", "doc-none"):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "No relevant content found" in events[0]["message"]


@pytest.mark.anyio
async def test_stream_answer_openai_error(mock_chunks, qa_service):
    async def fake_stream(*args, **kwargs):
        raise Exception("API error")
        yield

    with patch.object(qa_service, "hybrid_retrieve", AsyncMock(return_value=mock_chunks)), \
         patch(
             "app.services.rag.get_answer_stream_from_openai",
             side_effect=fake_stream,
         ):

        events = []
        async for event in qa_service.stream_answer("Error?", "doc-err"):
            events.append(event)

        assert events[0]["type"] == "sources"
        assert events[-1]["type"] == "error"
        assert "Internal server error" in events[-1]["message"]