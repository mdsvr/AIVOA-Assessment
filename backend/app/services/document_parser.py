import io
import zipfile
from email import message_from_bytes
from email.message import Message
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.core.config import settings

# Bounds below the trust boundary (validate_upload's 10MB file-size cap): a small
# compressed PDF/DOCX can still expand to way more pages/text/archive content than that
# cap implies -- these stop a zip-bomb-style upload from consuming unbounded memory/CPU
# during parsing.
MAX_PDF_PAGES = 200
MAX_EXTRACTED_CHARS = 2_000_000
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024


class UnsupportedFileError(ValueError):
    pass


class FileTooLargeError(ValueError):
    pass


class DocumentTooLargeError(ValueError):
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
    if len(reader.pages) > MAX_PDF_PAGES:
        raise DocumentTooLargeError(f"PDF exceeds max page count of {MAX_PDF_PAGES}")
    text_parts = []
    extracted_chars = 0
    for page in reader.pages:
        page_text = page.extract_text() or ""
        # +1 per page after the first for the "\n" the final join will insert, so the
        # running total matches the actual length of the returned string.
        extracted_chars += len(page_text) + (1 if text_parts else 0)
        if extracted_chars > MAX_EXTRACTED_CHARS:
            raise DocumentTooLargeError("PDF extracted text exceeds max allowed size")
        text_parts.append(page_text)
    return "\n".join(text_parts)


def _parse_docx(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        uncompressed_size = sum(info.file_size for info in zf.infolist())
        if uncompressed_size > MAX_DOCX_UNCOMPRESSED_BYTES:
            raise DocumentTooLargeError("DOCX archive exceeds max allowed expanded size")

    doc = Document(io.BytesIO(content))
    text = "\n".join(p.text for p in doc.paragraphs)
    if len(text) > MAX_EXTRACTED_CHARS:
        raise DocumentTooLargeError("DOCX extracted text exceeds max allowed size")
    return text


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
        html_fallback = None
        for part in msg.walk():
            # Skip attachments: an emailed .txt/.html attachment can otherwise be picked
            # up ahead of the actual message body since both share the same content type.
            if part.get_content_disposition() == "attachment" or part.get_filename() is not None:
                continue
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True) or b""
                return _decode_payload(payload, part.get_content_charset())
            if content_type == "text/html" and html_fallback is None:
                payload = part.get_payload(decode=True) or b""
                html_fallback = _decode_payload(payload, part.get_content_charset())
        # No text/plain part found -- fall back to the first HTML body rather than
        # returning empty text for an HTML-only email.
        return html_fallback or ""
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
