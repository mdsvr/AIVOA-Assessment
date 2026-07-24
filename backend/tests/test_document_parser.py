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


def test_parse_eml_html_only():
    raw = (
        b"Subject: Complaint about Batch 456\r\n"
        b"From: customer@example.com\r\n"
        b"Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: text/html\r\n\r\n"
        b"<html><body><p>The capsules were discolored on arrival.</p></body></html>\r\n"
        b"--BOUNDARY--\r\n"
    )
    text = document_parser.load_document("complaint.eml", raw)
    assert "discolored" in text


def test_parse_eml_skips_filename_bearing_body_part():
    raw = (
        b"Subject: Complaint about Batch 789\r\n"
        b"From: customer@example.com\r\n"
        b"Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: text/plain\r\n"
        b"Content-Disposition: inline; filename=\"notes.txt\"\r\n\r\n"
        b"Do not select this filename-bearing part.\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: text/plain\r\n\r\n"
        b"The actual complaint body is here.\r\n"
        b"--BOUNDARY--\r\n"
    )
    text = document_parser.load_document("complaint.eml", raw)
    assert "actual complaint body" in text
    assert "filename-bearing" not in text


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
