import json
import time
from collections.abc import Generator

from groq import Groq, RateLimitError

from app.core.config import settings

# Two clients so the chat assistant doesn't share a rate-limit bucket with the
# extraction pipeline -- both can genuinely run at once (chat is active during intake,
# before a complaint is saved). GROQ_API_KEY_CHAT is optional; unset falls back to the
# same key, matching pre-split behavior.
_extraction_client = Groq(api_key=settings.groq_api_key)
_chat_client = Groq(api_key=settings.groq_api_key_chat or settings.groq_api_key)


def chat(
    model: str,
    messages: list[dict],
    *,
    json_mode: bool = False,
    temperature: float = 0.2,
    timeout: float = 20.0,
) -> str:
    """One retry on 429 (free-tier rate limits are easy to hit live)."""
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    for attempt in range(2):
        try:
            resp = _extraction_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                timeout=timeout,
                **kwargs,
            )
            return resp.choices[0].message.content or ""
        except RateLimitError:
            if attempt == 0:
                time.sleep(2)
                continue
            raise


def chat_json(model: str, messages: list[dict], **kwargs) -> dict:
    """Raises json.JSONDecodeError on malformed model output rather than swallowing it --
    a required-node caller (extract_fields) needs that to surface as an extraction error,
    not a silently "successful" result full of nulls. Callers that want to tolerate a bad
    response (classify_risk) already wrap this in a broad try/except of their own."""
    raw = chat(model, messages, json_mode=True, **kwargs)
    return json.loads(raw)


def stream_chat(
    model: str,
    messages: list[dict],
    *,
    temperature: float = 0.3,
    timeout: float = 30.0,
) -> Generator[str, None, None]:
    stream = _chat_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        timeout=timeout,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
