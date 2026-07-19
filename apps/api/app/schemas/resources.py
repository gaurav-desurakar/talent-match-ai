from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.comparison import Requirement, ScoringWeights


class JobScorecardStatus(StrEnum):
    EMPTY = "empty"
    DRAFT = "draft"
    REVIEWED = "reviewed"


class RecruiterStatus(StrEnum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    NEEDS_CLARIFICATION = "needs_clarification"
    SHORTLISTED = "shortlisted"
    INTERVIEW_PLANNED = "interview_planned"
    INTERVIEW_COMPLETED = "interview_completed"
    ON_HOLD = "on_hold"
    TALENT_POOL = "talent_pool"
    NOT_PROGRESSING = "not_progressing"
    WITHDRAWN = "withdrawn"
    OFFER = "offer"
    HIRED = "hired"


class RecruiterReasonCode(StrEnum):
    MANDATORY_REQUIREMENT_NOT_EVIDENCED = "mandatory_requirement_not_evidenced"
    INSUFFICIENT_RELEVANT_EXPERIENCE = "insufficient_relevant_experience"
    ROLE_ALIGNMENT_GAP = "role_alignment_gap"
    APPLICATION_INCOMPLETE = "application_incomplete"
    CANDIDATE_WITHDREW = "candidate_withdrew"
    DUPLICATE_APPLICATION = "duplicate_application"
    POSITION_CLOSED = "position_closed"
    OTHER = "other"


class TriageSuggestion(StrEnum):
    MEETS_SHORTLIST_THRESHOLD = "meets_shortlist_threshold"
    NEEDS_CLARIFICATION = "needs_clarification"
    MANDATORY_CONCERN = "mandatory_concern"
    BELOW_THRESHOLD = "below_threshold"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class TriagePolicy(BaseModel):
    shortlist_fit_threshold: Annotated[float, Field(ge=0.0, le=100.0)] = 80.0
    shortlist_evidence_threshold: Annotated[float, Field(ge=0.0, le=100.0)] = 80.0
    require_mandatory_met: bool = True
    require_no_clarification_flags: bool = True


class JobScorecardRequirement(Requirement):
    included: bool = True


class JobScorecardExtractionRequest(BaseModel):
    provider: str = Field(
        default="mock",
        pattern=r"^(mock|openai|anthropic|google|groq|compatible|ollama)$",
    )
    credential_session_id: str | None = Field(default=None, max_length=100)


class JobScorecardUpdateRequest(BaseModel):
    requirements: list[JobScorecardRequirement] = Field(min_length=1, max_length=50)
    approve: bool = False

    @model_validator(mode="after")
    def requirement_ids_are_unique(self) -> "JobScorecardUpdateRequest":
        ids = [item.id for item in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("Scorecard requirement identifiers must be unique")
        if self.approve and not any(item.included for item in self.requirements):
            raise ValueError("An approved scorecard must include at least one requirement")
        return self


class JobScorecardResponse(BaseModel):
    job_id: str
    status: JobScorecardStatus
    version: int
    reviewed_at: datetime | None = None
    requirements: list[JobScorecardRequirement]
    warnings: list[str] = Field(default_factory=list)


class JobCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    external_job_id: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    raw_text: Annotated[str, Field(min_length=30, max_length=100_000)]
    parsed_content: dict[str, Any] = Field(default_factory=dict)
    requirements: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    source_file: str | None = Field(default=None, max_length=255)

    @field_validator("external_job_id")
    @classmethod
    def normalize_external_job_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Job ID must not be blank")
        return normalized


class JobUpdate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    external_job_id: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    raw_text: Annotated[str, Field(min_length=30, max_length=100_000)] | None = None
    parsed_content: dict[str, Any] | None = None
    requirements: list[dict[str, Any]] | None = Field(default=None, max_length=100)

    @field_validator("external_job_id")
    @classmethod
    def normalize_external_job_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Job ID must not be blank")
        return normalized


class JobResponse(JobCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    triage_policy: TriagePolicy = Field(default_factory=TriagePolicy)
    triage_policy_version: int = 1
    created_at: datetime
    updated_at: datetime


class ResumeCreate(BaseModel):
    raw_text: Annotated[str, Field(min_length=30, max_length=100_000)]
    parsed_content: dict[str, Any] = Field(default_factory=dict)
    source_file: str | None = Field(default=None, max_length=255)
    sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")
    extraction_warnings: list[str] = Field(default_factory=list, max_length=100)


class CandidateCreate(BaseModel):
    display_name: Annotated[str, Field(min_length=1, max_length=200)]
    anonymized_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    resume: ResumeCreate | None = None


class ResumeResponse(ResumeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str
    created_at: datetime


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    anonymized_name: str
    metadata: dict[str, Any] = Field(validation_alias="candidate_metadata")
    resumes: list[ResumeResponse]
    created_at: datetime
    updated_at: datetime


class CandidateSummary(BaseModel):
    id: str
    display_name: str
    anonymized_name: str
    resume_count: int = 0
    comparison_count: int = 0
    job_count: int = 0
    latest_resume_at: datetime | None = None
    last_analysis_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SettingsUpdate(BaseModel):
    provider: str = Field(default="mock", max_length=50)
    selected_model: str = Field(default="mock-evidence-v1", max_length=120)
    retention_policy_days: Annotated[int, Field(ge=0, le=3650)] = 30
    scoring_configuration: ScoringWeights = Field(default_factory=ScoringWeights)
    default_triage_policy: TriagePolicy = Field(default_factory=TriagePolicy)
    skill_taxonomy: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    blind_review_enabled: bool = False


class SettingsResponse(SettingsUpdate):
    id: str
    credential_configured: bool = False
    created_at: datetime
    updated_at: datetime


class ComparisonHistoryItem(BaseModel):
    id: str
    job_description_id: str
    candidate_id: str
    job_title: str
    candidate_display_name: str
    provider: str
    model: str
    scorecard_version: int | None = None
    status: str
    fit_score: float | None
    evidence_confidence_score: float | None
    mandatory_status: str | None
    recommendation: str | None
    recruiter_status: RecruiterStatus = RecruiterStatus.NEW
    triage_suggestion: TriageSuggestion
    disposition_updated_at: datetime | None = None
    created_at: datetime
    completed_at: datetime | None


class JobSummary(JobResponse):
    comparison_count: int = 0
    candidate_count: int = 0
    last_analysis_at: datetime | None = None
    scorecard_status: JobScorecardStatus = JobScorecardStatus.EMPTY
    scorecard_version: int = 0
    scorecard_requirement_count: int = 0


class JobOverview(BaseModel):
    job: JobSummary
    comparisons: list[ComparisonHistoryItem]


class JobTriagePolicyResponse(BaseModel):
    job_id: str
    policy: TriagePolicy
    version: int
    updated_at: datetime


class RecruiterDispositionUpdate(BaseModel):
    status: RecruiterStatus
    reason_code: RecruiterReasonCode | None = None
    note: Annotated[str, Field(max_length=2_000)] | None = None
    assigned_recruiter: Annotated[str, Field(max_length=200)] | None = None

    @field_validator("note", "assigned_recruiter")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_not_progressing_reason(self) -> "RecruiterDispositionUpdate":
        if self.status is RecruiterStatus.NOT_PROGRESSING and self.reason_code is None:
            raise ValueError("Select a job-related reason when a candidate is not progressing")
        if self.status is not RecruiterStatus.NOT_PROGRESSING and self.reason_code is not None:
            raise ValueError("Reason codes are only valid when a candidate is not progressing")
        if self.reason_code is RecruiterReasonCode.OTHER and not self.note:
            raise ValueError("Add a note when the reason is Other")
        return self


class RecruiterDispositionEvent(BaseModel):
    id: str
    previous_status: RecruiterStatus | None
    status: RecruiterStatus
    reason_code: RecruiterReasonCode | None
    note: str | None
    assigned_recruiter: str | None
    triage_suggestion: TriageSuggestion
    triage_policy: TriagePolicy
    triage_policy_version: int
    created_at: datetime


class RecruiterDispositionResponse(BaseModel):
    comparison_id: str
    status: RecruiterStatus
    reason_code: RecruiterReasonCode | None = None
    note: str | None = None
    assigned_recruiter: str | None = None
    triage_suggestion: TriageSuggestion
    triage_policy: TriagePolicy
    triage_policy_version: int
    updated_at: datetime | None = None
    events: list[RecruiterDispositionEvent] = Field(default_factory=list)


class CandidateOverview(BaseModel):
    candidate: CandidateResponse
    summary: CandidateSummary
    comparisons: list[ComparisonHistoryItem]


class DashboardSummary(BaseModel):
    total_comparisons: int
    active_jobs: int
    candidates_analyzed: int
    average_fit_score: float
    requiring_clarification: int
    provider_status: str
    retention_days: int
    recent_comparisons: list[ComparisonHistoryItem]


class DeletionSummary(BaseModel):
    jobs_deleted: int
    candidates_deleted: int
    comparisons_deleted: int
    audit_events_deleted: int


class RetentionRunResponse(BaseModel):
    cutoff: datetime
    deleted_comparisons: int
    deleted_candidates: int
    deleted_jobs: int
