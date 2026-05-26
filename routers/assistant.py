from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from services.groq_service import stream_chat, analyze_issue

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


class IssueAnalysisRequest(BaseModel):
    issue: dict


@router.post("/chat")
async def chat(req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    return StreamingResponse(stream_chat(messages), media_type="text/plain")


@router.post("/analyze-issue")
async def analyze(req: IssueAnalysisRequest):
    return StreamingResponse(analyze_issue(req.issue), media_type="text/plain")
