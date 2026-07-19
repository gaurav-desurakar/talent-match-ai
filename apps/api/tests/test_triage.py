import pytest

from app.db.models import ComparisonModel
from app.schemas.resources import TriagePolicy, TriageSuggestion
from app.services.triage import calculate_triage_suggestion


@pytest.mark.parametrize(
    ("fit_score", "evidence_score", "mandatory_status", "clarification_flags", "expected"),
    [
        (None, 90.0, "met", [], TriageSuggestion.INSUFFICIENT_INFORMATION),
        (90.0, 90.0, "partially_met", [], TriageSuggestion.MANDATORY_CONCERN),
        (90.0, 90.0, "met", [{"id": "clarify-1"}], TriageSuggestion.NEEDS_CLARIFICATION),
        (90.0, 79.0, "met", [], TriageSuggestion.NEEDS_CLARIFICATION),
        (80.0, 80.0, "met", [], TriageSuggestion.MEETS_SHORTLIST_THRESHOLD),
        (79.0, 90.0, "met", [], TriageSuggestion.BELOW_THRESHOLD),
    ],
)
def test_calculate_triage_suggestion_is_deterministic(
    fit_score: float | None,
    evidence_score: float,
    mandatory_status: str,
    clarification_flags: list[dict[str, str]],
    expected: TriageSuggestion,
) -> None:
    comparison = ComparisonModel(
        fit_score=fit_score,
        evidence_confidence_score=evidence_score,
        mandatory_status=mandatory_status,
        result={"clarification_flags": clarification_flags},
    )

    assert calculate_triage_suggestion(comparison, TriagePolicy()) is expected
