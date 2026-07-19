from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.comparison import BatchComparisonRequest


class AnalysisJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisJobRequest(BatchComparisonRequest):
    job_id: str | None = Field(default=None, max_length=36)
    job_title: str | None = Field(default=None, max_length=200)


class AnalysisRetryRequest(BaseModel):
    provider: str = Field(
        default="mock",
        pattern=r"^(mock|openai|anthropic|google|groq|compatible|ollama)$",
    )
    credential_session_id: str | None = Field(default=None, max_length=100)
    blind_review: bool = False


class AnalysisProgressEvent(BaseModel):
    sequence: int
    timestamp: datetime
    node: str
    label: str
    status: str
    candidate_id: str | None = None


class AnalysisJobResponse(BaseModel):
    job_id: str
    status: AnalysisJobStatus
    candidate_count: int
    completed_count: int
    comparison_ids: list[str]
    events_url: str
    latest_event: AnalysisProgressEvent | None = None
    error: dict[str, str] | None = None
    created_at: datetime
    completed_at: datetime | None = None
