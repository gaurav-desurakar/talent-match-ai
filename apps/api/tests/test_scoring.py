import pytest
from pydantic import ValidationError

from app.providers.mock import MockProvider
from app.schemas.comparison import (
    MandatoryStatus,
    Recommendation,
    ScoringWeights,
)
from app.scoring.engine import score_matches

JOB = """Senior AI Engineer
Must have production experience with Python and RAG applications.
Experience with Docker is preferred.
Lead technical architecture and work with stakeholders.
"""

RESUME = """Alex Morgan
Senior Software Engineer
Designed and deployed a Python retrieval-augmented generation service used by 12,000 users.
Owned Docker production deployment and monitoring.
Led architecture reviews with business stakeholders.
"""


def test_default_weights_total_one_hundred() -> None:
    assert sum(ScoringWeights().model_dump().values()) == 100


def test_invalid_weights_are_rejected() -> None:
    with pytest.raises(ValidationError, match="total exactly 100"):
        ScoringWeights(core_technical_skills=19)


def test_deterministic_scoring_and_mandatory_handling() -> None:
    analysis = MockProvider().generate_analysis(JOB, RESUME, blind_review=False)
    result = score_matches(analysis.matches, ScoringWeights())
    fit_score, evidence_confidence, mandatory_status, recommendation, matches, _ = result

    assert fit_score >= 75
    assert evidence_confidence >= 70
    assert mandatory_status is MandatoryStatus.MET
    assert recommendation in {Recommendation.SHORTLIST, Recommendation.STRONG_SHORTLIST}
    assert all(match.evidence for match in matches)


def test_taxonomy_normalizes_leadership_and_stakeholder_language() -> None:
    analysis = MockProvider().generate_analysis(JOB, RESUME, blind_review=False)
    concepts = {match.requirement.canonical_concept for match in analysis.matches}

    assert "Leadership" in concepts
    assert "Stakeholder management" in concepts


def test_missing_mandatory_evidence_is_separate_from_fit_score() -> None:
    analysis = MockProvider().generate_analysis(
        "AI Engineer\nPython is required.\nKubernetes is required.",
        "Candidate\nBuilt and deployed Python services for several teams.",
        blind_review=False,
    )
    _, _, mandatory_status, recommendation, matches, _ = score_matches(
        analysis.matches, ScoringWeights()
    )

    assert mandatory_status is MandatoryStatus.PARTIALLY_MET
    assert recommendation is not Recommendation.STRONG_SHORTLIST
    assert any(match.score == 0 for match in matches)
