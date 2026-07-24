from app.agents.extraction_graph import _normalize_null


def test_normalizes_string_null_variants():
    for value in ["null", "None", "N/A", "n/a", "unknown", "", "  NULL  "]:
        assert _normalize_null(value) is None


def test_leaves_real_values_alone():
    assert _normalize_null("2026-03-10") == "2026-03-10"
    assert _normalize_null(1200) == 1200
    assert _normalize_null(None) is None
