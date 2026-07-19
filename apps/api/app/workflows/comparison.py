from collections.abc import Callable
from uuid import uuid4

from app.core.errors import ApiError
from app.core.security import detect_prompt_injection, redact_resume_identity
from app.core.text import is_verbatim_excerpt
from app.providers.base import LLMProvider
from app.schemas.comparison import (
    ClarificationFlag,
    ClarificationStatus,
    ComparisonRequest,
    ComparisonResponse,
    InterviewQuestion,
    ProviderRequirementMatch,
    Requirement,
    RequirementMatch,
    WorkflowEvent,
)
from app.scoring.engine import score_matches

DISCLAIMER = (
    "This tool provides evidence-based decision support. It should not be used as the sole "
    "basis for employment decisions."
)


class ComparisonWorkflow:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def run(
        self,
        request: ComparisonRequest,
        event_callback: Callable[[WorkflowEvent], None] | None = None,
        *,
        approved_requirements: list[Requirement] | None = None,
        scorecard_version: int | None = None,
    ) -> ComparisonResponse:
        events: list[WorkflowEvent] = []

        def event(node: str, label: str) -> None:
            item = WorkflowEvent(sequence=len(events) + 1, node=node, label=label)
            events.append(item)
            if event_callback:
                event_callback(item)

        event("document_ingestion", "Parsed document text")
        warnings = [
            *detect_prompt_injection(request.job_description_text, "job description"),
            *detect_prompt_injection(request.resume_text, "resume"),
        ]
        event("job_analysis", "Extracted job requirements")
        event("resume_analysis", "Analysed resume evidence")
        resume_text = (
            redact_resume_identity(request.resume_text)
            if request.blind_review
            else request.resume_text
        )
        analysis = self.provider.generate_analysis(
            request.job_description_text,
            resume_text,
            blind_review=request.blind_review,
            job_source_references=request.job_source_references,
            resume_source_references=(
                None if request.blind_review else request.resume_source_references
            ),
            approved_requirements=approved_requirements,
        )
        if approved_requirements:
            validate_approved_scorecard(analysis.matches, approved_requirements)
        validate_analysis_evidence(
            analysis.matches,
            request.job_description_text,
            resume_text,
        )
        event("skill_normalization", "Normalized equivalent and transferable skills")
        event("evidence_matching", "Mapped requirements to resume evidence")
        (
            fit_score,
            evidence_confidence,
            mandatory_status,
            recommendation,
            matches,
            breakdown,
        ) = score_matches(analysis.matches, request.scoring_weights)
        event("credibility_review", "Identified evidence requiring clarification")
        clarification_flags = build_clarification_flags(matches)
        event("deterministic_scoring", "Calculated deterministic scores")
        interview_questions = build_interview_questions(matches)
        event("interview_questions", "Generated targeted interview questions")
        event("quality_review", "Validated evidence links and protected-field boundaries")
        return ComparisonResponse(
            comparison_id=str(uuid4()),
            status="completed",
            provider=self.provider.id,
            model=self.provider.model,
            scorecard_version=scorecard_version,
            job_title=analysis.job_title,
            candidate_display_name=(
                "Candidate" if request.blind_review else analysis.candidate_display_name
            ),
            fit_score=fit_score,
            evidence_confidence_score=evidence_confidence,
            mandatory_status=mandatory_status,
            recommendation=recommendation,
            score_breakdown=breakdown,
            requirement_matches=matches,
            workflow_events=events,
            clarification_flags=clarification_flags,
            interview_questions=interview_questions,
            quality_checks=[
                "Every scored requirement has a validated source reference or an explicit "
                "evidence gap.",
                "Fit and mandatory status were calculated by deterministic application code.",
                "Protected characteristics were excluded from scoring.",
            ],
            warnings=[*warnings, *analysis.warnings],
            methodology_note=(
                "The mock provider classifies text into a validated schema. Application code "
                "calculates all displayed scores; active category weights are normalized when "
                "the pasted job description does not cover every scoring category."
            ),
            disclaimer=DISCLAIMER,
        )


def build_clarification_flags(matches: list[RequirementMatch]) -> list[ClarificationFlag]:
    flags: list[ClarificationFlag] = []
    for match in matches:
        if not match.clarification_required:
            continue
        status = (
            ClarificationStatus.INSUFFICIENT_EVIDENCE
            if not match.evidence
            else ClarificationStatus.NEEDS_CLARIFICATION
        )
        flags.append(
            ClarificationFlag(
                id=f"clarification-{len(flags) + 1}",
                status=status,
                title=match.requirement.canonical_concept or match.requirement.text[:100],
                explanation=(
                    "The resume does not provide supporting evidence; ask the candidate for a "
                    "specific example."
                    if not match.evidence
                    else "The available statement is partial and should be validated in interview."
                ),
                source_references=[item.source_reference for item in match.evidence],
            )
        )
    return flags


def build_interview_questions(matches: list[RequirementMatch]) -> list[InterviewQuestion]:
    questions: list[InterviewQuestion] = []
    ordered = sorted(
        matches,
        key=lambda item: (
            not item.clarification_required,
            -item.requirement.importance,
            item.requirement.id,
        ),
    )
    for match in ordered[:10]:
        concept = match.requirement.canonical_concept or match.requirement.text
        if match.evidence:
            question = (
                f"For your work related to {concept}, what was your individual contribution, "
                "the production context, and the measurable outcome?"
            )
            category = "technical_depth"
            rationale = "Validate depth, ownership, and outcome behind the cited resume evidence."
        else:
            question = (
                f"The resume does not describe {concept}. What relevant experience, if any, "
                "should the hiring team consider?"
            )
            category = "missing_information"
            rationale = "Clarify an important evidence gap without treating omission as absence."
        questions.append(
            InterviewQuestion(
                id=f"question-{len(questions) + 1}",
                category=category,
                question=question,
                rationale=rationale,
                source_requirement_id=match.requirement.id,
            )
        )
    return questions


def validate_analysis_evidence(
    matches: list[ProviderRequirementMatch],
    job_description_text: str,
    resume_text: str,
) -> None:
    for match in matches:
        if not is_verbatim_excerpt(match.requirement.text, job_description_text):
            raise ApiError(
                "PROVIDER_EVIDENCE_VALIDATION_FAILED",
                "The provider returned a requirement that was not found in the job description.",
                502,
            )
        for evidence in match.evidence:
            if not is_verbatim_excerpt(evidence.text, resume_text):
                raise ApiError(
                    "PROVIDER_EVIDENCE_VALIDATION_FAILED",
                    "The provider returned evidence that was not found in the resume.",
                    502,
                )


def validate_approved_scorecard(
    matches: list[ProviderRequirementMatch], approved_requirements: list[Requirement]
) -> None:
    expected = {item.id: item.model_dump(mode="json") for item in approved_requirements}
    actual = {
        item.requirement.id: item.requirement.model_dump(mode="json") for item in matches
    }
    if actual != expected:
        raise ApiError(
            "PROVIDER_SCORECARD_MISMATCH",
            "The provider response did not match the recruiter-approved scorecard.",
            502,
        )
