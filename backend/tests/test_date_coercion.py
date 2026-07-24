import pytest
from pydantic import ValidationError

from app.schemas.complaint import ExtractedFields


def test_accepts_iso_date():
    fields = ExtractedFields(manufacturing_date="2026-03-10")
    assert str(fields.manufacturing_date) == "2026-03-10"


def test_rejects_non_iso_date():
    with pytest.raises(ValidationError):
        ExtractedFields(manufacturing_date="March 10, 2026")


def test_accepts_missing_date():
    assert ExtractedFields().manufacturing_date is None
