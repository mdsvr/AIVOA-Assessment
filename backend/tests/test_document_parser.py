import io

import pytest
from docx import Document as DocxDocument

from app.services import document_parser


def test_parse_txt():
    text = document_parser.load_document("complaint.txt", b"Patient reported a defect.")
    assert "defect" in text


def test_parse_eml():
    raw = (
        b"Subject: Complaint about Batch 123\r\n"
        b"From: customer@example.com\r\n"
        b"Content-Type: text/plain\r\n\r\n"
        b"The tablets arrived discolored."
    )
    text = document_parser.load_document("complaint.eml", raw)
    assert "Batch 123" in text
    assert "discolored" in text


def test_parse_docx():
    doc = DocxDocument()
    doc.add_paragraph("Customer complaint: capsules cracked in transit.")
    buffer = io.BytesIO()
    doc.save(buffer)
    text = document_parser.load_document("complaint.docx", buffer.getvalue())
    assert "cracked" in text


def test_validate_upload_rejects_bad_extension():
    with pytest.raises(document_parser.UnsupportedFileError):
        document_parser.validate_upload("complaint.exe", 100)


def test_validate_upload_rejects_oversize():
    with pytest.raises(document_parser.FileTooLargeError):
        document_parser.validate_upload("complaint.txt", 999_999_999)
