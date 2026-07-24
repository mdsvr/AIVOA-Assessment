import json
import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from app.agents import groq_client
from app.agents.prompts import (
    EXTRACTION_FIELDS,
    EXTRACTION_SYSTEM_PROMPT,
    PRIORITY_VALUES,
    REQUIRED_FIELDS,
    RISK_SYSTEM_PROMPT,
    SEVERITY_VALUES,
    SUMMARY_SYSTEM_PROMPT,
)
from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.complaint import ExtractedFields
from app.services import document_parser
from app.services.duplicates import find_duplicates

logger = logging.getLogger(__name__)

# Cap raw document text sent to the LLM -- demo-scale complaints, not full dossiers.
MAX_CONTEXT_CHARS = 8000


class ExtractionState(TypedDict, total=False):
    filename: str
    content: bytes | None
    pasted_text: str | None

    source_text: str
    fields: dict[str, Any]
    completeness_score: float
    risk_classification: str | None
    duplicates: list[dict]
    duplicates_error: str | None
    summary: str | None


def load_document(state: ExtractionState) -> dict:
    if state.get("pasted_text"):
        text = state["pasted_text"]
    else:
        text = document_parser.load_document(state["filename"], state["content"])
    return {"source_text": text}


_NULL_SENTINELS = {"null", "none", "n/a", "na", "unknown", ""}


def _normalize_null(value: Any) -> Any:
    """Smaller models in JSON mode sometimes write the string "null" (or similar) for a
    field they don't have, instead of the JSON null literal -- Pydantic's date/float
    validators don't treat that as empty, they try to parse "null" as a date and fail.
    Same "don't guess" intent as the null-if-missing prompt instruction, just also
    catching the model's own stringified version of it before validation sees it."""
    if isinstance(value, str) and value.strip().lower() in _NULL_SENTINELS:
        return None
    return value


def extract_fields(state: ExtractionState) -> dict:
    """Required node -- the plan says extraction must succeed for the form to populate,
    everything downstream is enrichment. Validating through the same ExtractedFields
    schema Save/Chat use (rather than a bespoke per-field coercion) means a malformed
    response -- wrong date format, a string where a number belongs -- fails extraction
    up front with a clear error, instead of silently emitting a bad value that only
    surfaces later as an opaque 422 on Save/Chat."""
    document = state["source_text"]
    if len(document) > MAX_CONTEXT_CHARS:
        raise ValueError(
            f"Document exceeds the supported extraction size of {MAX_CONTEXT_CHARS} characters"
        )
    # Passed as a JSON-quoted string rather than interpolated beside instruction text --
    # the document can't break out of its own JSON string value the way it could break
    # out of a plain-text delimiter (e.g. by containing a fake closing tag). The
    # untrusted-data handling rule itself lives in EXTRACTION_SYSTEM_PROMPT.
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps({"document": document})},
    ]
    data = groq_client.chat_json(settings.extraction_model, messages)
    if not isinstance(data, dict) or set(data) - set(EXTRACTION_FIELDS):
        raise ValueError("Model returned fields outside the expected extraction schema")
    raw = {key: _normalize_null(data.get(key)) for key in EXTRACTION_FIELDS}
    try:
        validated = ExtractedFields(**raw)
    except ValidationError as exc:
        raise ValueError(f"Model returned data that doesn't match the expected schema: {exc}") from exc
    return {"fields": validated.model_dump(mode="json")}


def check_completeness(state: ExtractionState) -> dict:
    fields = state["fields"]
    filled = sum(1 for f in REQUIRED_FIELDS if fields.get(f))
    return {"completeness_score": round(filled / len(REQUIRED_FIELDS), 2)}


def classify_risk(state: ExtractionState) -> dict:
    fields = dict(state["fields"])
    try:
        messages = [
            {"role": "system", "content": RISK_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"product_name: {fields.get('product_name')}\n"
                    f"complaint_type: {fields.get('complaint_type')}\n"
                    f"description: {fields.get('description')}"
                ),
            },
        ]
        data = groq_client.chat_json(settings.extraction_model, messages)
    except Exception:
        data = {}

    severity = data.get("initial_severity")
    priority = data.get("priority")
    # Never write an unvalidated AI value into a field the UI renders as a fixed dropdown.
    fields["initial_severity"] = severity if severity in SEVERITY_VALUES else None
    fields["priority"] = priority if priority in PRIORITY_VALUES else None

    rationale = data.get("rationale")
    label = " / ".join(filter(None, [fields["initial_severity"], fields["priority"]]))
    risk_classification = f"{label}: {rationale}" if label and rationale else rationale

    return {"fields": fields, "risk_classification": risk_classification}


def detect_duplicates(state: ExtractionState) -> dict:
    # Session scoped to this node only, not held open across the surrounding LLM calls
    # (extract_fields, classify_risk, summarize can each take several seconds) -- a
    # long-lived session sitting idle through three network round-trips is an easy way
    # to exhaust the connection pool under concurrent extractions.
    db = SessionLocal()
    try:
        return {"duplicates": find_duplicates(db, state["fields"]), "duplicates_error": None}
    except Exception:
        # Distinct from a confirmed empty result: the UI needs to know the check
        # didn't run, not that it ran and found nothing.
        logger.exception("Duplicate check failed")
        return {"duplicates": [], "duplicates_error": "Duplicate check unavailable"}
    finally:
        db.close()


def summarize(state: ExtractionState) -> dict:
    try:
        messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": state["source_text"][:MAX_CONTEXT_CHARS]},
        ]
        summary = groq_client.chat(settings.extraction_model, messages, temperature=0.3)
    except Exception:
        summary = None
    return {"summary": summary}


def build_extraction_graph():
    graph = StateGraph(ExtractionState)
    graph.add_node("load_document", load_document)
    graph.add_node("extract_fields", extract_fields)
    graph.add_node("check_completeness", check_completeness)
    graph.add_node("classify_risk", classify_risk)
    graph.add_node("detect_duplicates", detect_duplicates)
    graph.add_node("summarize", summarize)

    graph.set_entry_point("load_document")
    graph.add_edge("load_document", "extract_fields")
    graph.add_edge("extract_fields", "check_completeness")
    graph.add_edge("check_completeness", "classify_risk")
    graph.add_edge("classify_risk", "detect_duplicates")
    graph.add_edge("detect_duplicates", "summarize")
    graph.add_edge("summarize", END)
    return graph.compile()


extraction_graph = build_extraction_graph()
