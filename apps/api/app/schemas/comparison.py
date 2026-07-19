from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from app.schemas.document import DocumentSourceReference


class ScoreCategory(StrEnum):
    CORE_TECHNICAL_SKILLS = "core_technical_skills"
    RESPONSIBILITY_ALIGNMENT = "responsibility_alignment"
    RELEVANT_EXPERIENCE = "relevant_experience"
    PROJECT_SIMILARITY = "project_similarity"
    SENIORITY_AND_OWNERSHIP = "seniority_and_ownership"
    MEASURABLE_ACHIEVEMENTS = "measurable_achievements"
    DOMAIN_EXPERIENCE = "domain_experience"
    STAKEHOLDER_AND_CUSTOMER_EXPERIENCE = "stakeholder_and_customer_experience"
    EDUCATION_AND_CERTIFICATIONS = "education_and_certifications"
    CAREER_PROGRESSION = "career_progression"


class RequirementClassification(StrEnum):
    MANDATORY = "mandatory"
    STRONGLY_PREFERRED = "strongly_preferred"
    PREFERRED = "preferred"
    CONTEXTUAL = "contextual"
    INFORMATIONAL = "informational"


class MatchType(StrEnum):
    EXACT = "exact"
    EQUIVALENT = "equivalent"
    TRANSFERABLE = "transferable"
    ADJACENT = "adjacent"
    NO_EVIDENCE = "no_evidence"


class MandatoryStatus(StrEnum):
    MET = "met"
    PARTIALLY_MET = "partially_met"
    NOT_MET = "not_met"
    UNCLEAR = "unclear"
    NOT_APPLICABLE = "not_applicable"


class Recommendation(StrEnum):
    STRONG_SHORTLIST = "strong_shortlist"
    SHORTLIST = "shortlist"
    CONSIDER_WITH_CLARIFICATIONS = "consider_with_clarifications"
    SIGNIFICANT_GAPS = "significant_gaps"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class ScoringWeights(BaseModel):
    core_technical_skills: Annotated[int, Field(ge=0, le=100)] = 20
    responsibility_alignment: Annotated[int, Field(ge=0, le=100)] = 18
    relevant_experience: Annotated[int, Field(ge=0, le=100)] = 15
    project_similarity: Annotated[int, Field(ge=0, le=100)] = 10
    seniority_and_ownership: Annotated[int, Field(ge=0, le=100)] = 10
    measurable_achievements: Annotated[int, Field(ge=0, le=100)] = 10
    domain_experience: Annotated[int, Field(ge=0, le=100)] = 6
    stakeholder_and_customer_experience: Annotated[int, Field(ge=0, le=100)] = 5
    education_and_certifications: Annotated[int, Field(ge=0, le=100)] = 3
    career_progression: Annotated[int, Field(ge=0, le=100)] = 3

    @model_validator(mode="after")
    def weights_total_one_hundred(self) -> "ScoringWeights":
        if sum(self.model_dump().values()) != 100:
            raise ValueError("Scoring weights must total exactly 100")
        return self


class ComparisonRequest(BaseModel):
    job_description_text: Annotated[str, Field(min_length=30, max_length=100_000)]
    resume_text: Annotated[str, Field(min_length=30, max_length=100_000)]
    provider: str = Field(
        default="mock",
        pattern=r"^(mock|openai|anthropic|google|groq|compatible|ollama)$",
    )
    credential_session_id: str | None = Field(default=None, max_length=100)
    blind_review: bool = False
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)
    job_source_references: list[DocumentSourceReference] = Field(
        default_factory=list, max_length=5_000
    )
    resume_source_references: list[DocumentSourceReference] = Field(
        default_factory=list, max_length=5_000
    )

    @model_validator(mode="after")
    def source_references_match_document_text(self) -> "ComparisonRequest":
        pairs = (
            ("job description", self.job_description_text, self.job_source_references),
            ("resume", self.resume_text, self.resume_source_references),
        )
        for label, text, references in pairs:
            if references:
                referenced_text = "\n".join(reference.text for reference in references)
                if referenced_text.strip() != text.strip():
                    raise ValueError(
                        f"The {label} source references do not match the submitted text"
                    )
        return self


class SourceEvidence(BaseModel):
    text: str
    source_reference: str
    section: str = "Resume"


class Requirement(BaseModel):
    id: str
    text: str
    canonical_concept: str | None = None
    classification: RequirementClassification
    category: ScoreCategory
    importance: Annotated[float, Field(ge=0.1, le=1.0)]
    source_reference: str


class ProviderRequirementMatch(BaseModel):
    requirement: Requirement
    match_type: MatchType
    match_strength: Annotated[float, Field(ge=0.0, le=1.0)]
    evidence_strength: Annotated[float, Field(ge=0.0, le=1.0)]
    evidence: list[SourceEvidence] = Field(max_length=5)
    explanation: str
    uncertainties: list[str] = Field(default_factory=list)


class ProviderAnalysis(BaseModel):
    job_title: str
    candidate_display_name: str
    matches: list[ProviderRequirementMatch] = Field(min_length=1, max_length=50)
    warnings: list[str] = Field(default_factory=list)


class ProviderJobAnalysis(BaseModel):
    job_title: str
    requirements: list[Requirement] = Field(min_length=1, max_length=50)
    warnings: list[str] = Field(default_factory=list)


class RequirementMatch(BaseModel):
    requirement: Requirement
    match_type: MatchType
    score: Annotated[float, Field(ge=0.0, le=100.0)]
    confidence: Annotated[float, Field(ge=0.0, le=100.0)]
    evidence: list[SourceEvidence]
    explanation: str
    uncertainties: list[str]
    clarification_required: bool


class ScoreBreakdown(BaseModel):
    category: ScoreCategory
    weight: int
    score: Annotated[float, Field(ge=0.0, le=100.0)]
    evidence_count: int
    explanation: str


class WorkflowEvent(BaseModel):
    sequence: int
    node: str
    label: str
    status: str = "completed"


class ClarificationStatus(StrEnum):
    WELL_SUPPORTED = "well_supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    NEEDS_CLARIFICATION = "needs_clarification"
    INTERNALLY_INCONSISTENT = "internally_inconsistent"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ClarificationFlag(BaseModel):
    id: str
    status: ClarificationStatus
    title: str
    explanation: str
    source_references: list[str] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    id: str
    category: str
    question: str
    rationale: str
    source_requirement_id: str | None = None
    selected: bool = True


class ComparisonResponse(BaseModel):
    comparison_id: str
    status: str
    provider: str
    model: str
    scorecard_version: int | None = None
    job_title: str
    candidate_display_name: str
    fit_score: Annotated[float, Field(ge=0.0, le=100.0)]
    evidence_confidence_score: Annotated[float, Field(ge=0.0, le=100.0)]
    mandatory_status: MandatoryStatus
    recommendation: Recommendation
    score_breakdown: list[ScoreBreakdown]
    requirement_matches: list[RequirementMatch]
    workflow_events: list[WorkflowEvent]
    clarification_flags: list[ClarificationFlag] = Field(default_factory=list)
    interview_questions: list[InterviewQuestion] = Field(default_factory=list)
    quality_checks: list[str] = Field(default_factory=list)
    warnings: list[str]
    methodology_note: str
    disclaimer: str


class CandidateComparisonInput(BaseModel):
    candidate_id: Annotated[str, Field(min_length=1, max_length=100)]
    display_name: Annotated[str, Field(min_length=1, max_length=100)]
    stored_candidate_id: str | None = Field(default=None, max_length=36)
    resume_id: str | None = Field(default=None, max_length=36)
    resume_text: Annotated[str, Field(min_length=30, max_length=100_000)]
    resume_source_references: list[DocumentSourceReference] = Field(
        default_factory=list, max_length=5_000
    )

    @model_validator(mode="after")
    def source_references_match_resume(self) -> "CandidateComparisonInput":
        if bool(self.stored_candidate_id) != bool(self.resume_id):
            raise ValueError(
                "Stored candidate and resume identifiers must be provided together"
            )
        if self.resume_source_references:
            referenced_text = "\n".join(
                reference.text for reference in self.resume_source_references
            )
            if referenced_text.strip() != self.resume_text.strip():
                raise ValueError("The resume source references do not match the submitted text")
        return self


class BatchComparisonRequest(BaseModel):
    job_description_text: Annotated[str, Field(min_length=30, max_length=100_000)]
    candidates: list[CandidateComparisonInput] = Field(min_length=1, max_length=5)
    provider: str = Field(
        default="mock",
        pattern=r"^(mock|openai|anthropic|google|groq|compatible|ollama)$",
    )
    credential_session_id: str | None = Field(default=None, max_length=100)
    blind_review: bool = False
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)
    job_source_references: list[DocumentSourceReference] = Field(
        default_factory=list, max_length=5_000
    )

    @model_validator(mode="after")
    def validate_batch(self) -> "BatchComparisonRequest":
        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Candidate identifiers must be unique within a batch")
        if self.job_source_references:
            referenced_text = "\n".join(reference.text for reference in self.job_source_references)
            if referenced_text.strip() != self.job_description_text.strip():
                raise ValueError(
                    "The job description source references do not match the submitted text"
                )
        return self


class CandidateComparisonResult(BaseModel):
    candidate_id: str
    display_name: str
    comparison: ComparisonResponse


class BatchComparisonResponse(BaseModel):
    batch_id: str
    status: str
    candidate_count: int
    comparisons: list[CandidateComparisonResult]


class ProviderInfo(BaseModel):
    id: str
    name: str
    models: list[str]
    requires_api_key: bool
    sends_documents_externally: bool
    status: str
