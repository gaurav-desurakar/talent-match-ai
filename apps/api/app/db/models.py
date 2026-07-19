from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class UserSettingsModel(TimestampMixin, Base):
    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(50), default="mock")
    selected_model: Mapped[str] = mapped_column(String(120), default="mock-evidence-v1")
    encrypted_api_key_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retention_policy_days: Mapped[int] = mapped_column(Integer, default=30)
    scoring_configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    default_triage_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    skill_taxonomy: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    blind_review_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class JobDescriptionModel(TimestampMixin, Base):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200))
    external_job_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    requirements: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    triage_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    triage_policy_version: Mapped[int] = mapped_column(Integer, default=1)

    comparisons: Mapped[list["ComparisonModel"]] = relationship(
        back_populates="job_description", cascade="all, delete-orphan"
    )


class CandidateModel(TimestampMixin, Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(200))
    anonymized_name: Mapped[str] = mapped_column(String(100))
    candidate_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    resumes: Mapped[list["ResumeModel"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    comparisons: Mapped[list["ComparisonModel"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class ResumeModel(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    extraction_warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    candidate: Mapped[CandidateModel] = relationship(back_populates="resumes")


class ComparisonModel(Base):
    __tablename__ = "comparisons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_description_id: Mapped[str] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), index=True)
    fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mandatory_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(60), nullable=True)
    scoring_configuration_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job_description: Mapped[JobDescriptionModel] = relationship(back_populates="comparisons")
    candidate: Mapped[CandidateModel] = relationship(back_populates="comparisons")
    requirement_matches: Mapped[list["RequirementMatchModel"]] = relationship(
        back_populates="comparison", cascade="all, delete-orphan"
    )
    analysis_runs: Mapped[list["AnalysisRunModel"]] = relationship(
        back_populates="comparison", cascade="all, delete-orphan"
    )
    recruiter_disposition: Mapped["RecruiterDispositionModel | None"] = relationship(
        back_populates="comparison", cascade="all, delete-orphan", uselist=False
    )


class RecruiterDispositionModel(TimestampMixin, Base):
    __tablename__ = "recruiter_dispositions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    comparison_id: Mapped[str] = mapped_column(
        ForeignKey("comparisons.id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_recruiter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    triage_suggestion_snapshot: Mapped[str] = mapped_column(String(60))
    triage_policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    triage_policy_version: Mapped[int] = mapped_column(Integer)

    comparison: Mapped[ComparisonModel] = relationship(back_populates="recruiter_disposition")
    events: Mapped[list["RecruiterDispositionEventModel"]] = relationship(
        back_populates="disposition", cascade="all, delete-orphan"
    )


class RecruiterDispositionEventModel(Base):
    __tablename__ = "recruiter_disposition_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    disposition_id: Mapped[str] = mapped_column(
        ForeignKey("recruiter_dispositions.id", ondelete="CASCADE"), index=True
    )
    previous_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(40))
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_recruiter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    triage_suggestion_snapshot: Mapped[str] = mapped_column(String(60))
    triage_policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    triage_policy_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    disposition: Mapped[RecruiterDispositionModel] = relationship(back_populates="events")


class RequirementMatchModel(Base):
    __tablename__ = "requirement_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    comparison_id: Mapped[str] = mapped_column(
        ForeignKey("comparisons.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[str] = mapped_column(String(100))
    match_type: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    clarification_required: Mapped[bool] = mapped_column(Boolean, default=False)

    comparison: Mapped[ComparisonModel] = relationship(back_populates="requirement_matches")


class AnalysisRunModel(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    comparison_id: Mapped[str] = mapped_column(
        ForeignKey("comparisons.id", ondelete="CASCADE"), index=True
    )
    workflow_version: Mapped[str] = mapped_column(String(40), default="1.0")
    prompt_version: Mapped[str] = mapped_column(String(40), default="1.0")
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(120))
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    comparison: Mapped[ComparisonModel] = relationship(back_populates="analysis_runs")


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    non_sensitive_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
