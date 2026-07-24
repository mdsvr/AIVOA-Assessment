import io
from email import message_from_bytes
from email.message import Message
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.core.config import settings


class UnsupportedFileError(ValueError):
    pass


class FileTooLargeError(ValueError):
    pass


def validate_upload(filename: str, size_bytes: int) -> None:
    """Trust-boundary check: run before any parsing, matches the reference UI's
    stated 'Supported formats / Max file size' limits."""
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise UnsupportedFileError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(settings.allowed_extensions))}"
        )
    if size_bytes > settings.max_upload_bytes:
        raise FileTooLargeError(
            f"File exceeds max size of {settings.max_upload_bytes // (1024 * 1024)}MB"
        )


def _parse_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs)


def _parse_txt(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


def _decode_payload(payload: bytes, declared_charset: str | None) -> str:
    """Falls back to UTF-8 if the declared charset is missing OR unrecognized -- an
    unknown codec name (a typo, a rare/legacy encoding) would otherwise raise
    LookupError, which errors="replace" does not catch (that only handles bad bytes
    for a *valid* codec, not an invalid codec name)."""
    try:
        return payload.decode(declared_charset or "utf-8", errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _extract_eml_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            # Skip attachments: an emailed .txt attachment can otherwise be picked up
            # ahead of the actual message body since both are text/plain.
            if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
                payload = part.get_payload(decode=True) or b""
                return _decode_payload(payload, part.get_content_charset())
        return ""
    payload = msg.get_payload(decode=True) or b""
    return _decode_payload(payload, msg.get_content_charset())


def _parse_eml(content: bytes) -> str:
    msg = message_from_bytes(content)
    subject = msg.get("Subject", "")
    sender = msg.get("From", "")
    body = _extract_eml_body(msg)
    return f"Subject: {subject}\nFrom: {sender}\n\n{body}"


_PARSERS = {
    ".pdf": _parse_pdf,
    ".docx": _parse_docx,
    ".txt": _parse_txt,
    ".eml": _parse_eml,
}


def load_document(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    parser = _PARSERS.get(ext)
    if parser is None:
        raise UnsupportedFileError(f"Unsupported file type '{ext}'")
    return parser(content).strip()
