from app.agents.extraction_graph import check_completeness
from app.agents.prompts import REQUIRED_FIELDS


def test_check_completeness_full():
    fields = {f: "value" for f in REQUIRED_FIELDS}
    result = check_completeness({"fields": fields})
    assert result["completeness_score"] == 1.0


def test_check_completeness_half():
    fields = {f: ("value" if i % 2 == 0 else None) for i, f in enumerate(REQUIRED_FIELDS)}
    result = check_completeness({"fields": fields})
    assert 0 < result["completeness_score"] < 1
