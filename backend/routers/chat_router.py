"""Chat router - powers the floating chat agent."""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import load_config
from services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str]
    error: Optional[str] = None


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        config = load_config()
        history = [m.dict() for m in request.history]
        result = chat_service.chat(config=config, user_message=request.message, history=history)
        return ChatResponse(**result)
    except Exception as exc:
        logger.error("Chat endpoint failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}")