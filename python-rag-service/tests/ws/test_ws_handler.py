import os
import shutil
import pytest
from fastapi.testclient import TestClient

# Set FAISS store path before importing the app
os.environ["FAISS_STORE_PATH"] = "./.test_faiss_index"
os.makedirs(os.environ["FAISS_STORE_PATH"], exist_ok=True)

from app.main import app

# ---------- Cleanup ----------

@pytest.fixture(scope="session", autouse=True)
def cleanup_faiss_dir():
    """
    Ensure that the test FAISS directory is removed after the test session.
    """
    yield
    shutil.rmtree(os.environ["FAISS_STORE_PATH"], ignore_errors=True)

# ---------- Tests ----------

def test_websocket_stream(monkeypatch):
    """
    Simulates a valid WebSocket connection and tests streaming of messages.
    Mocks the stream_ask_question generator to emit fake response events.
    """

    # Mock stream_ask_question generator
    async def fake_stream_ask_question(question: str, document_id: str):
        yield {"type": "sources", "sources": [{"pageNumber": 1}]}
        yield {"type": "answer", "token": "Hello"}
        yield {"type": "done"}

    # Monkeypatch the actual function
    monkeypatch.setattr("app.ws.ws_handler.stream_ask_question", fake_stream_ask_question)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Send a valid payload
            websocket.send_json({"question": "What is X?", "documentId": "doc-1"})

            msg1 = websocket.receive_json()
            msg2 = websocket.receive_json()
            msg3 = websocket.receive_json()

            # Assert expected events
            assert msg1["type"] == "sources"
            assert msg2["type"] == "answer"
            assert msg2["token"] == "Hello"
            assert msg3["type"] == "done"

def test_websocket_missing_fields():
    """
    Sends an incomplete WebSocket payload (missing question).
    Expects an error response from the server.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"documentId": "doc-1"})  # Missing "question"

            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "question and documentId" in msg["message"]
