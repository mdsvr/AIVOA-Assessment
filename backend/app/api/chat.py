import json
import logging
from collections.abc import Generator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents import groq_client
from app.agents.chat_graph import build_chat_messages
from app.core.config import settings
from app.schemas.complaint import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_context(payload: ChatRequest) -> str:
    fields = payload.context.model_dump() if payload.context else {}
    if payload.ai_summary:
        fields["ai_summary"] = payload.ai_summary
    lines = [f"{key}: {value}" for key, value in fields.items() if value]
    if payload.source_text:
        lines.append(f"source_document: {payload.source_text[:4000]}")
    return "\n".join(lines)


def _stream_chat_response(payload: ChatRequest) -> Generator[str, None, None]:
    try:
        history = [m.model_dump() for m in payload.history]
        messages = build_chat_messages(_build_context(payload), history, payload.message)

        for token in groq_client.stream_chat(settings.chat_model, messages):
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
        yield "event: done\ndata: {}\n\n"
    except Exception:  # noqa: BLE001
        logger.exception("Chat request failed")
        yield f"event: error\ndata: {json.dumps({'message': 'Chat request failed. Please try again.'})}\n\n"


@router.post("/chat")
async def chat_with_assistant(payload: ChatRequest):
    """Stateless by design: the complaint being chatted about may not be saved yet (the
    reference UI shows the assistant active during intake, before Save). The frontend
    holds fields + conversation history in Redux and resends them each turn instead of
    the server looking a saved complaint up by id."""
    return StreamingResponse(
        _stream_chat_response(payload),
        media_type="text/event-stream",
    )
