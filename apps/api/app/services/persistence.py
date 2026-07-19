from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.db.models import (
    AnalysisRunModel,
    AuditEventModel,
    CandidateModel,
    ComparisonModel,
    JobDescriptionModel,
    RecruiterDispositionEventModel,
    RecruiterDispositionModel,
    RequirementMatchModel,
    ResumeModel,
    UserSettingsModel,
)
from app.providers.prompts import PROMPT_VERSION
from app.schemas.comparison import ComparisonResponse, ScoringWeights
from app.schemas.resources import (
    CandidateCreate,
    CandidateSummary,
    ComparisonHistoryItem,
    JobCreate,
    JobResponse,
    JobSummary,
    JobUpdate,
    RecruiterDispositionEvent,
    RecruiterDispositionResponse,
    RecruiterDispositionUpdate,
    ResumeCreate,
    SettingsUpdate,
    TriagePolicy,
)
from app.services.triage import calculate_triage_suggestion, policy_for_job


def audit(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEventModel(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            non_sensitive_metadata=metadata or {},
        )
    )


def resume_content_fingerprint(raw_text: str) -> str:
    normalized = " ".join(raw_text.split()).casefold()
    return sha256(normalized.encode("utf-8")).hexdigest()


def create_job(db: Session, data: JobCreate) -> JobDescriptionModel:
    default_policy = TriagePolicy.model_validate(
        get_or_create_settings(db).default_triage_policy or {}
    )
    job = JobDescriptionModel(
        **data.model_dump(),
        triage_policy=default_policy.model_dump(),
        triage_policy_version=1,
    )
    db.add(job)
    audit(db, "job.created", "job_description", job.id)
    db.commit()
    db.refresh(job)
    return job


def list_jobs(db: Session, offset: int, limit: int) -> list[JobDescriptionModel]:
    return list(
        db.scalars(
            select(JobDescriptionModel)
            .order_by(JobDescriptionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )


def job_summary(db: Session, job: JobDescriptionModel) -> JobSummary:
    comparison_count, candidate_count, last_analysis_at = db.execute(
        select(
            func.count(ComparisonModel.id),
            func.count(func.distinct(ComparisonModel.candidate_id)),
            func.max(ComparisonModel.completed_at),
        ).where(ComparisonModel.job_description_id == job.id)
    ).one()
    scorecard_metadata = job.parsed_content.get("talentmatch_scorecard", {})
    return JobSummary.model_validate(
        {
            **JobResponse.model_validate(job).model_dump(mode="python"),
            "comparison_count": comparison_count or 0,
            "candidate_count": candidate_count or 0,
            "last_analysis_at": last_analysis_at,
            "scorecard_status": scorecard_metadata.get("status", "empty"),
            "scorecard_version": int(scorecard_metadata.get("version", 0)),
            "scorecard_requirement_count": sum(
                bool(item.get("included", True)) for item in job.requirements
            ),
        }
    )


def list_job_summaries(db: Session, offset: int, limit: int) -> list[JobSummary]:
    return [job_summary(db, job) for job in list_jobs(db, offset, limit)]


def list_comparisons_for_job(
    db: Session, job_id: str, offset: int = 0, limit: int = 100
) -> list[ComparisonModel]:
    return list(
        db.scalars(
            select(ComparisonModel)
            .options(
                selectinload(ComparisonModel.job_description),
                selectinload(ComparisonModel.candidate),
                selectinload(ComparisonModel.recruiter_disposition),
            )
            .where(ComparisonModel.job_description_id == job_id)
            .order_by(ComparisonModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )


def update_job(db: Session, job: JobDescriptionModel, data: JobUpdate) -> JobDescriptionModel:
    updates = data.model_dump(exclude_none=True)
    if "external_job_id" in data.model_fields_set:
        updates["external_job_id"] = data.external_job_id
    scorecard = job.parsed_content.get("talentmatch_scorecard", {})
    has_scorecard = bool(job.requirements) or scorecard.get("status") in {
        "draft",
        "reviewed",
    }
    description_changed = (
        "raw_text" in updates and updates["raw_text"].strip() != job.raw_text.strip()
    )
    for key, value in updates.items():
        setattr(job, key, value)
    scorecard_invalidated = description_changed and has_scorecard
    if scorecard_invalidated:
        next_version = max(int(scorecard.get("version", 0)) + 1, 1)
        job.requirements = []
        job.parsed_content = {
            **job.parsed_content,
            "talentmatch_scorecard": {
                "status": "draft",
                "version": next_version,
                "reviewed_at": None,
                "warnings": ["The job description changed. Regenerate and approve the scorecard."],
            },
        }
    audit(
        db,
        "job.updated",
        "job_description",
        job.id,
        {"scorecard_invalidated": scorecard_invalidated},
    )
    db.commit()
    db.refresh(job)
    return job


def create_candidate(db: Session, data: CandidateCreate) -> CandidateModel:
    candidate = CandidateModel(
        display_name=data.display_name,
        anonymized_name=data.anonymized_name or "Candidate",
        candidate_metadata=data.metadata,
    )
    if data.resume:
        candidate.resumes.append(
            ResumeModel(
                **data.resume.model_dump(),
                content_sha256=resume_content_fingerprint(data.resume.raw_text),
            )
        )
    db.add(candidate)
    audit(db, "candidate.created", "candidate", candidate.id)
    db.commit()
    return get_candidate(db, candidate.id)  # type: ignore[return-value]


def get_candidate(db: Session, candidate_id: str) -> CandidateModel | None:
    return db.scalar(
        select(CandidateModel)
        .options(selectinload(CandidateModel.resumes))
        .where(CandidateModel.id == candidate_id)
    )


def find_candidate_by_resume_content(db: Session, raw_text: str) -> CandidateModel | None:
    return db.scalar(
        select(CandidateModel)
        .join(CandidateModel.resumes)
        .options(selectinload(CandidateModel.resumes))
        .where(ResumeModel.content_sha256 == resume_content_fingerprint(raw_text))
        .order_by(CandidateModel.created_at.asc())
        .limit(1)
    )


def add_candidate_resume(db: Session, candidate: CandidateModel, data: ResumeCreate) -> ResumeModel:
    content_sha256 = resume_content_fingerprint(data.raw_text)
    if any(resume.content_sha256 == content_sha256 for resume in candidate.resumes):
        raise ApiError(
            "CANDIDATE_RESUME_DUPLICATE",
            "This resume content is already saved for the candidate.",
            409,
        )
    resume = ResumeModel(
        **data.model_dump(),
        content_sha256=content_sha256,
    )
    candidate.resumes.append(resume)
    db.flush()
    audit(
        db,
        "candidate.resume_added",
        "candidate",
        candidate.id,
        {"resume_id": resume.id},
    )
    db.commit()
    db.refresh(resume)
    return resume


def list_candidates(db: Session, offset: int, limit: int) -> list[CandidateModel]:
    return list(
        db.scalars(
            select(CandidateModel)
            .options(selectinload(CandidateModel.resumes))
            .order_by(CandidateModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )


def candidate_summary(db: Session, candidate: CandidateModel) -> CandidateSummary:
    comparison_count, job_count, last_analysis_at = db.execute(
        select(
            func.count(ComparisonModel.id),
            func.count(func.distinct(ComparisonModel.job_description_id)),
            func.max(ComparisonModel.completed_at),
        ).where(ComparisonModel.candidate_id == candidate.id)
    ).one()
    latest_resume_at = max(
        (resume.created_at for resume in candidate.resumes),
        default=None,
    )
    return CandidateSummary(
        id=candidate.id,
        display_name=candidate.display_name,
        anonymized_name=candidate.anonymized_name,
        resume_count=len(candidate.resumes),
        comparison_count=comparison_count or 0,
        job_count=job_count or 0,
        latest_resume_at=latest_resume_at,
        last_analysis_at=last_analysis_at,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def list_candidate_summaries(db: Session, offset: int, limit: int) -> list[CandidateSummary]:
    return [candidate_summary(db, candidate) for candidate in list_candidates(db, offset, limit)]


def list_comparisons_for_candidate(
    db: Session, candidate_id: str, offset: int = 0, limit: int = 100
) -> list[ComparisonModel]:
    return list(
        db.scalars(
            select(ComparisonModel)
            .options(
                selectinload(ComparisonModel.job_description),
                selectinload(ComparisonModel.candidate),
                selectinload(ComparisonModel.recruiter_disposition),
            )
            .where(ComparisonModel.candidate_id == candidate_id)
            .order_by(ComparisonModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )


def get_or_create_settings(db: Session) -> UserSettingsModel:
    settings = db.scalar(select(UserSettingsModel).limit(1))
    if settings is None:
        settings = UserSettingsModel(
            scoring_configuration=ScoringWeights().model_dump(),
            default_triage_policy=TriagePolicy().model_dump(),
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_settings(db: Session, data: SettingsUpdate) -> UserSettingsModel:
    settings = get_or_create_settings(db)
    payload = data.model_dump()
    payload["scoring_configuration"] = data.scoring_configuration.model_dump()
    payload["default_triage_policy"] = data.default_triage_policy.model_dump()
    for key, value in payload.items():
        setattr(settings, key, value)
    audit(db, "settings.updated", "user_settings", settings.id)
    db.commit()
    db.refresh(settings)
    return settings


def persist_result(
    db: Session,
    job: JobDescriptionModel,
    candidate: CandidateModel,
    result: ComparisonResponse,
    weights: ScoringWeights,
    duration_ms: int,
    token_usage: dict[str, Any] | None = None,
    retry_count: int = 0,
) -> ComparisonModel:
    comparison = ComparisonModel(
        id=result.comparison_id,
        job_description_id=job.id,
        candidate_id=candidate.id,
        provider=result.provider,
        model=result.model,
        status=result.status,
        fit_score=result.fit_score,
        evidence_confidence_score=result.evidence_confidence_score,
        mandatory_status=result.mandatory_status.value,
        recommendation=result.recommendation.value,
        scoring_configuration_snapshot=weights.model_dump(),
        result=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
    )
    comparison.requirement_matches = [
        RequirementMatchModel(
            requirement_id=match.requirement.id,
            match_type=match.match_type.value,
            score=match.score,
            confidence=match.confidence,
            evidence=[item.model_dump(mode="json") for item in match.evidence],
            explanation=match.explanation,
            clarification_required=match.clarification_required,
        )
        for match in result.requirement_matches
    ]
    comparison.analysis_runs.append(
        AnalysisRunModel(
            prompt_version=PROMPT_VERSION,
            provider=result.provider,
            model=result.model,
            token_usage=token_usage or {},
            duration_ms=duration_ms,
            retry_count=retry_count,
        )
    )
    db.add(comparison)
    audit(db, "comparison.completed", "comparison", comparison.id, {"status": "completed"})
    db.commit()
    db.refresh(comparison)
    return comparison


def history_item(comparison: ComparisonModel) -> ComparisonHistoryItem:
    result_name = comparison.result.get("candidate_display_name")
    policy = policy_for_job(comparison.job_description)
    disposition = comparison.recruiter_disposition
    return ComparisonHistoryItem(
        id=comparison.id,
        job_description_id=comparison.job_description_id,
        candidate_id=comparison.candidate_id,
        job_title=comparison.job_description.title,
        candidate_display_name=(
            str(result_name) if result_name else comparison.candidate.display_name
        ),
        provider=comparison.provider,
        model=comparison.model,
        scorecard_version=(
            int(comparison.result["scorecard_version"])
            if comparison.result.get("scorecard_version") is not None
            else None
        ),
        status=comparison.status,
        fit_score=comparison.fit_score,
        evidence_confidence_score=comparison.evidence_confidence_score,
        mandatory_status=comparison.mandatory_status,
        recommendation=comparison.recommendation,
        recruiter_status=disposition.status if disposition else "new",
        triage_suggestion=calculate_triage_suggestion(comparison, policy),
        disposition_updated_at=disposition.updated_at if disposition else None,
        created_at=comparison.created_at,
        completed_at=comparison.completed_at,
    )


def list_comparisons(db: Session, offset: int, limit: int) -> list[ComparisonModel]:
    return list(
        db.scalars(
            select(ComparisonModel)
            .options(
                selectinload(ComparisonModel.job_description),
                selectinload(ComparisonModel.candidate),
                selectinload(ComparisonModel.recruiter_disposition),
            )
            .order_by(ComparisonModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )


def update_job_triage_policy(
    db: Session,
    job: JobDescriptionModel,
    policy: TriagePolicy,
) -> JobDescriptionModel:
    job.triage_policy = policy.model_dump()
    job.triage_policy_version += 1
    audit(
        db,
        "job.triage_policy_updated",
        "job_description",
        job.id,
        {"triage_policy_version": job.triage_policy_version},
    )
    db.commit()
    db.refresh(job)
    return job


def _disposition_event_response(
    event: RecruiterDispositionEventModel,
) -> RecruiterDispositionEvent:
    return RecruiterDispositionEvent(
        id=event.id,
        previous_status=event.previous_status,
        status=event.status,
        reason_code=event.reason_code,
        note=event.note,
        assigned_recruiter=event.assigned_recruiter,
        triage_suggestion=event.triage_suggestion_snapshot,
        triage_policy=event.triage_policy_snapshot,
        triage_policy_version=event.triage_policy_version,
        created_at=event.created_at,
    )


def disposition_response(comparison: ComparisonModel) -> RecruiterDispositionResponse:
    policy = policy_for_job(comparison.job_description)
    suggestion = calculate_triage_suggestion(comparison, policy)
    disposition = comparison.recruiter_disposition
    if disposition is None:
        return RecruiterDispositionResponse(
            comparison_id=comparison.id,
            status="new",
            triage_suggestion=suggestion,
            triage_policy=policy,
            triage_policy_version=comparison.job_description.triage_policy_version,
        )
    return RecruiterDispositionResponse(
        comparison_id=comparison.id,
        status=disposition.status,
        reason_code=disposition.reason_code,
        note=disposition.note,
        assigned_recruiter=disposition.assigned_recruiter,
        triage_suggestion=suggestion,
        triage_policy=policy,
        triage_policy_version=comparison.job_description.triage_policy_version,
        updated_at=disposition.updated_at,
        events=[
            _disposition_event_response(event)
            for event in sorted(disposition.events, key=lambda item: item.created_at, reverse=True)
        ],
    )


def update_recruiter_disposition(
    db: Session,
    comparison: ComparisonModel,
    data: RecruiterDispositionUpdate,
) -> RecruiterDispositionResponse:
    policy = policy_for_job(comparison.job_description)
    suggestion = calculate_triage_suggestion(comparison, policy)
    disposition = comparison.recruiter_disposition
    previous_status = disposition.status if disposition else None
    if disposition is None:
        disposition = RecruiterDispositionModel(
            comparison_id=comparison.id,
            status=data.status.value,
            reason_code=data.reason_code.value if data.reason_code else None,
            note=data.note,
            assigned_recruiter=data.assigned_recruiter,
            triage_suggestion_snapshot=suggestion.value,
            triage_policy_snapshot=policy.model_dump(),
            triage_policy_version=comparison.job_description.triage_policy_version,
        )
        comparison.recruiter_disposition = disposition
    else:
        disposition.status = data.status.value
        disposition.reason_code = data.reason_code.value if data.reason_code else None
        disposition.note = data.note
        disposition.assigned_recruiter = data.assigned_recruiter
        disposition.triage_suggestion_snapshot = suggestion.value
        disposition.triage_policy_snapshot = policy.model_dump()
        disposition.triage_policy_version = comparison.job_description.triage_policy_version
    disposition.events.append(
        RecruiterDispositionEventModel(
            previous_status=previous_status,
            status=data.status.value,
            reason_code=data.reason_code.value if data.reason_code else None,
            note=data.note,
            assigned_recruiter=data.assigned_recruiter,
            triage_suggestion_snapshot=suggestion.value,
            triage_policy_snapshot=policy.model_dump(),
            triage_policy_version=comparison.job_description.triage_policy_version,
        )
    )
    audit(
        db,
        "comparison.recruiter_disposition_updated",
        "comparison",
        comparison.id,
        {
            "previous_status": previous_status,
            "status": data.status.value,
            "reason_code": data.reason_code.value if data.reason_code else None,
        },
    )
    db.commit()
    db.refresh(disposition)
    return disposition_response(comparison)


def delete_all_data(db: Session) -> dict[str, int]:
    counts = {
        "jobs_deleted": db.scalar(select(func.count(JobDescriptionModel.id))) or 0,
        "candidates_deleted": db.scalar(select(func.count(CandidateModel.id))) or 0,
        "comparisons_deleted": db.scalar(select(func.count(ComparisonModel.id))) or 0,
        "audit_events_deleted": db.scalar(select(func.count(AuditEventModel.id))) or 0,
    }
    db.execute(delete(RecruiterDispositionEventModel))
    db.execute(delete(RecruiterDispositionModel))
    db.execute(delete(ComparisonModel))
    db.execute(delete(CandidateModel))
    db.execute(delete(JobDescriptionModel))
    db.execute(delete(AuditEventModel))
    db.commit()
    return counts


def run_retention(db: Session, retention_days: int) -> tuple[datetime, dict[str, int]]:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    old_comparisons = list(
        db.scalars(select(ComparisonModel).where(ComparisonModel.created_at < cutoff))
    )
    comparison_count = len(old_comparisons)
    for comparison in old_comparisons:
        db.delete(comparison)
    db.flush()
    orphan_candidates = list(
        db.scalars(select(CandidateModel).where(~CandidateModel.comparisons.any()))
    )
    orphan_jobs = list(
        db.scalars(select(JobDescriptionModel).where(~JobDescriptionModel.comparisons.any()))
    )
    for item in [*orphan_candidates, *orphan_jobs]:
        db.delete(item)
    audit(db, "retention.completed", "system", None, {"retention_days": retention_days})
    db.commit()
    return cutoff, {
        "deleted_comparisons": comparison_count,
        "deleted_candidates": len(orphan_candidates),
        "deleted_jobs": len(orphan_jobs),
    }
