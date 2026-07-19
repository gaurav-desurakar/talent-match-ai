from app.db.models import ComparisonModel, JobDescriptionModel
from app.schemas.resources import TriagePolicy, TriageSuggestion


def policy_for_job(job: JobDescriptionModel) -> TriagePolicy:
    return TriagePolicy.model_validate(job.triage_policy or {})


def calculate_triage_suggestion(
    comparison: ComparisonModel,
    policy: TriagePolicy,
) -> TriageSuggestion:
    if comparison.fit_score is None or comparison.evidence_confidence_score is None:
        return TriageSuggestion.INSUFFICIENT_INFORMATION
    if policy.require_mandatory_met and comparison.mandatory_status not in {
        "met",
        "not_applicable",
    }:
        return TriageSuggestion.MANDATORY_CONCERN
    if policy.require_no_clarification_flags and comparison.result.get("clarification_flags", []):
        return TriageSuggestion.NEEDS_CLARIFICATION
    if comparison.evidence_confidence_score < policy.shortlist_evidence_threshold:
        return TriageSuggestion.NEEDS_CLARIFICATION
    if comparison.fit_score >= policy.shortlist_fit_threshold:
        return TriageSuggestion.MEETS_SHORTLIST_THRESHOLD
    return TriageSuggestion.BELOW_THRESHOLD
