import json
import logging
from collections.abc import Generator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.extraction_graph import extraction_graph
from app.core.config import settings
from app.db.models import Complaint, ComplaintDocument
from app.db.session import get_db
from app.schemas.complaint import ComplaintCreate, ComplaintOut
from app.services.document_parser import (
    FileTooLargeError,
    UnsupportedFileError,
    validate_upload,
)

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_CHUNK_BYTES = 1024 * 1024  # 1MB


async def _read_upload_bounded(file: UploadFile, max_bytes: int) -> bytes:
    """Read in chunks and bail out as soon as the cap is exceeded, instead of buffering
    an arbitrarily large upload into memory before the size check ever runs."""
    content = bytearray()
    while True:
        chunk = await file.read(UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_bytes:
            raise FileTooLargeError(f"File exceeds max size of {max_bytes // (1024 * 1024)}MB")
    return bytes(content)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _run_extraction_stream(
    filename: str, content: bytes | None, pasted_text: str | None
) -> Generator[str, None, None]:
    initial_state = {
        "filename": filename,
        "content": content,
        "pasted_text": pasted_text,
    }
    try:
        final_state: dict = {}
        for step in extraction_graph.stream(initial_state):
            node_name, node_output = next(iter(step.items()))
            final_state.update(node_output)
            yield _sse("progress", {"node": node_name})

        result = {
            "fields": final_state.get("fields", {}),
            "completeness_score": final_state.get("completeness_score", 0),
            "risk_classification": final_state.get("risk_classification"),
            "ai_summary": final_state.get("summary"),
            "duplicates": final_state.get("duplicates", []),
            "duplicates_error": final_state.get("duplicates_error"),
            "source_text": final_state.get("source_text", ""),
            "source_filename": filename,
        }
        yield _sse("result", result)
    except Exception:  # noqa: BLE001 -- surface to the client instead of a bare 500 mid-stream
        logger.exception("Extraction failed")
        yield _sse("error", {"message": "Extraction failed. Please try again."})


@router.post("/extract")
async def extract_complaint(
    file: UploadFile | None = File(None),
    pasted_text: str | None = Form(None),
):
    if not file and not pasted_text:
        raise HTTPException(400, "Provide either a file or pasted_text")

    content: bytes | None = None
    filename = "pasted-text.txt"
    if file:
        try:
            content = await _read_upload_bounded(file, settings.max_upload_bytes)
            validate_upload(file.filename, len(content))
        except (UnsupportedFileError, FileTooLargeError) as exc:
            raise HTTPException(400, str(exc)) from exc
        filename = file.filename

    return StreamingResponse(
        _run_extraction_stream(filename, content, pasted_text),
        media_type="text/event-stream",
    )


@router.post("", response_model=ComplaintOut)
def save_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"source_text", "source_filename"})
    complaint = Complaint(**data)
    db.add(complaint)

    try:
        db.flush()  # assigns complaint.id without committing, so the document can reference it
        if payload.source_text:
            file_type = (
                payload.source_filename.rsplit(".", 1)[-1] if payload.source_filename else "text"
            )
            db.add(
                ComplaintDocument(
                    complaint_id=complaint.id,
                    filename=payload.source_filename or "pasted-text.txt",
                    file_type=file_type,
                    extracted_text=payload.source_text,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to save complaint")
        raise HTTPException(500, "Could not save complaint. Please try again.") from None

    db.refresh(complaint)
    return complaint


@router.get("", response_model=list[ComplaintOut])
def list_complaints(db: Session = Depends(get_db)):
    return db.execute(select(Complaint).order_by(Complaint.created_at.desc())).scalars().all()


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    return complaint
