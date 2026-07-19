from collections import defaultdict

from app.schemas.comparison import (
    MandatoryStatus,
    ProviderRequirementMatch,
    Recommendation,
    RequirementClassification,
    RequirementMatch,
    ScoreBreakdown,
    ScoreCategory,
    ScoringWeights,
)


def _requirement_score(item: ProviderRequirementMatch) -> float:
    return round(item.match_strength * item.evidence_strength * 100, 1)


def score_matches(
    provider_matches: list[ProviderRequirementMatch], weights: ScoringWeights
) -> tuple[
    float,
    float,
    MandatoryStatus,
    Recommendation,
    list[RequirementMatch],
    list[ScoreBreakdown],
]:
    if not provider_matches:
        raise ValueError("At least one requirement match is required")

    matches: list[RequirementMatch] = []
    by_category: dict[ScoreCategory, list[tuple[float, float, int]]] = defaultdict(list)

    for item in provider_matches:
        score = _requirement_score(item)
        confidence = round(item.evidence_strength * 100, 1)
        evidence_count = len(item.evidence)
        matches.append(
            RequirementMatch(
                requirement=item.requirement,
                match_type=item.match_type,
                score=score,
                confidence=confidence,
                evidence=item.evidence,
                explanation=item.explanation,
                uncertainties=item.uncertainties,
                clarification_required=score < 65 or bool(item.uncertainties),
            )
        )
        by_category[item.requirement.category].append(
            (score, item.requirement.importance, evidence_count)
        )

    weight_map = {ScoreCategory(key): value for key, value in weights.model_dump().items()}
    breakdown: list[ScoreBreakdown] = []
    weighted_total = 0.0
    active_weight = 0
    for category, values in by_category.items():
        importance_total = sum(importance for _, importance, _ in values)
        category_score = (
            sum(score * importance for score, importance, _ in values) / importance_total
        )
        category_weight = weight_map[category]
        active_weight += category_weight
        weighted_total += category_score * category_weight
        evidence_count = sum(count for _, _, count in values)
        breakdown.append(
            ScoreBreakdown(
                category=category,
                weight=category_weight,
                score=round(category_score, 1),
                evidence_count=evidence_count,
                explanation=(
                    f"Based on {len(values)} extracted requirement(s) and "
                    f"{evidence_count} evidence passage(s)."
                ),
            )
        )

    fit_score = round(weighted_total / active_weight, 1) if active_weight else 0.0
    linked = sum(1 for match in matches if match.evidence)
    reference_coverage = sum(
        1 for match in matches for evidence in match.evidence if evidence.source_reference
    )
    evidence_confidence = round(
        min(100.0, (linked / len(matches) * 70) + (reference_coverage / len(matches) * 10)), 1
    )
    mandatory_status = calculate_mandatory_status(matches)
    recommendation = calculate_recommendation(fit_score, evidence_confidence, mandatory_status)
    return (
        fit_score,
        evidence_confidence,
        mandatory_status,
        recommendation,
        matches,
        sorted(breakdown, key=lambda item: item.category.value),
    )


def calculate_mandatory_status(matches: list[RequirementMatch]) -> MandatoryStatus:
    mandatory = [
        match
        for match in matches
        if match.requirement.classification is RequirementClassification.MANDATORY
    ]
    if not mandatory:
        return MandatoryStatus.NOT_APPLICABLE
    if all(match.score >= 70 for match in mandatory):
        return MandatoryStatus.MET
    if all(match.score == 0 for match in mandatory):
        return MandatoryStatus.NOT_MET
    if any(match.score >= 40 for match in mandatory):
        return MandatoryStatus.PARTIALLY_MET
    return MandatoryStatus.UNCLEAR


def calculate_recommendation(
    fit_score: float, evidence_confidence: float, mandatory_status: MandatoryStatus
) -> Recommendation:
    if evidence_confidence < 25:
        return Recommendation.INSUFFICIENT_INFORMATION
    if mandatory_status in {MandatoryStatus.NOT_MET, MandatoryStatus.UNCLEAR}:
        return Recommendation.CONSIDER_WITH_CLARIFICATIONS
    if fit_score >= 85 and evidence_confidence >= 70:
        return Recommendation.STRONG_SHORTLIST
    if fit_score >= 70:
        return Recommendation.SHORTLIST
    if fit_score >= 45:
        return Recommendation.CONSIDER_WITH_CLARIFICATIONS
    return Recommendation.SIGNIFICANT_GAPS
