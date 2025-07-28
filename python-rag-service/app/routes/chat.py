from fastapi import APIRouter
from pydantic import BaseModel
from app.services.question_answering import handle_ask_question

router = APIRouter()


class AskQuestionPayload(BaseModel):
    question: str
    documentId: str


@router.post("/ask-question")
async def ask_question(payload: AskQuestionPayload):
    return await handle_ask_question(payload.question, payload.documentId)
