from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from app.services.rag import stream_ask_question

ws_router = APIRouter()

@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            question = payload.get("question")
            document_id = payload.get("documentId")

            if not question or not document_id:
                await websocket.send_json({"type": "error", "message": "question and documentId are required"})
                continue

            async for event in stream_ask_question(question, document_id):
                await websocket.send_json(event)
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})

