from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class ExtractedFields(BaseModel):
    complaint_source: str | None = None
    customer_name: str | None = None
    product_name: str | None = None
    product_strength: str | None = None
    batch_lot_number: str | None = None
    manufacturing_date: date | None = None
    expiry_date: date | None = None
    quantity_affected: float | None = None
    quantity_unit: str | None = None
    complaint_type: str | None = None
    complaint_date: date | None = None
    description: str | None = None
    initial_severity: str | None = None
    priority: str | None = None


class DuplicateMatch(BaseModel):
    complaint_id: int
    similarity: float
    product_name: str | None = None
    customer_name: str | None = None


class ExtractionResult(BaseModel):
    fields: ExtractedFields
    completeness_score: float
    risk_classification: str | None = None
    ai_summary: str | None = None
    duplicates: list[DuplicateMatch] = []
    source_text: str
    source_filename: str


class ComplaintCreate(ExtractedFields):
    source_text: str | None = None
    source_filename: str | None = None
    completeness_score: float | None = None
    risk_classification: str | None = None
    ai_summary: str | None = None
    raw_extraction: dict | None = None


class ComplaintOut(ExtractedFields):
    id: int
    status: str
    completeness_score: float | None = None
    risk_classification: str | None = None
    ai_summary: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryMessage(BaseModel):
    # Literal, not str: prevents a caller from injecting a "system" role into the
    # message list assemble_context builds for the LLM.
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    # Bounds are generous for real usage but reject pathological payloads (e.g. a
    # multi-MB "message") before they reach the LLM call.
    message: str = Field(max_length=4000)
    context: ExtractedFields | None = None
    source_text: str | None = Field(default=None, max_length=20000)
    ai_summary: str | None = None
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=40)
