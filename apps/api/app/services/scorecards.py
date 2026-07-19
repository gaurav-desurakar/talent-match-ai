from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import contains_protected_scoring_attribute
from app.core.text import is_verbatim_excerpt, normalize_for_verbatim_match
from app.db.models import JobDescriptionModel
from app.schemas.comparison import ProviderJobAnalysis, Requirement
from app.schemas.resources import (
    JobScorecardRequirement,
    JobScorecardResponse,
    JobScorecardStatus,
)
from app.services.persistence import audit

SCORECARD_METADATA_KEY = "talentmatch_scorecard"


def get_job_scorecard(job: JobDescriptionModel) -> JobScorecardResponse:
    metadata = job.parsed_content.get(SCORECARD_METADATA_KEY, {})
    status = JobScorecardStatus(metadata.get("status", JobScorecardStatus.EMPTY))
    reviewed_at_value = metadata.get("reviewed_at")
    reviewed_at = (
        datetime.fromisoformat(reviewed_at_value)
        if isinstance(reviewed_at_value, str)
        else None
    )
    return JobScorecardResponse(
        job_id=job.id,
        status=status,
        version=int(metadata.get("version", 0)),
        reviewed_at=reviewed_at,
        requirements=[JobScorecardRequirement.model_validate(item) for item in job.requirements],
        warnings=[str(item) for item in metadata.get("warnings", [])],
    )


def save_extracted_scorecard(
    db: Session,
    job: JobDescriptionModel,
    analysis: ProviderJobAnalysis,
) -> JobScorecardResponse:
    current = get_job_scorecard(job)
    warnings = list(analysis.warnings)
    requirements: list[JobScorecardRequirement] = []
    seen: set[str] = set()
    protected_count = 0
    for item in analysis.requirements:
        if not is_verbatim_excerpt(item.text, job.raw_text):
            continue
        if contains_protected_scoring_attribute(item.text):
            protected_count += 1
            continue
        normalized = normalize_for_verbatim_match(item.text)
        if normalized in seen:
            continue
        seen.add(normalized)
        requirements.append(
            JobScorecardRequirement(
                **item.model_dump(exclude={"id"}),
                id=f"req-{len(requirements) + 1}",
                included=True,
            )
        )
    if protected_count:
        warnings.append(
            f"Excluded {protected_count} requirement(s) containing protected characteristics."
        )
    if not requirements:
        raise ApiError(
            "JOB_SCORECARD_EMPTY",
            "No source-grounded, non-protected requirements could be extracted.",
            422,
        )
    version = current.version + 1 if current.status is JobScorecardStatus.REVIEWED else max(
        current.version, 1
    )
    return _persist_scorecard(
        db,
        job,
        requirements=requirements,
        status=JobScorecardStatus.DRAFT,
        version=version,
        reviewed_at=None,
        warnings=warnings,
        event_type="job.scorecard.extracted",
    )


def save_reviewed_scorecard(
    db: Session,
    job: JobDescriptionModel,
    requirements: list[JobScorecardRequirement],
    *,
    approve: bool,
) -> JobScorecardResponse:
    current = get_job_scorecard(job)
    _validate_scorecard_requirements(job, requirements)
    current_payload = [item.model_dump(mode="json") for item in current.requirements]
    next_payload = [item.model_dump(mode="json") for item in requirements]
    changed_after_review = (
        current.status is JobScorecardStatus.REVIEWED and current_payload != next_payload
    )
    version = max(current.version, 1) + (1 if changed_after_review else 0)
    status = JobScorecardStatus.REVIEWED if approve else JobScorecardStatus.DRAFT
    reviewed_at = datetime.now(UTC) if approve else None
    return _persist_scorecard(
        db,
        job,
        requirements=requirements,
        status=status,
        version=version,
        reviewed_at=reviewed_at,
        warnings=current.warnings,
        event_type="job.scorecard.reviewed" if approve else "job.scorecard.updated",
    )


def approved_requirements(job: JobDescriptionModel) -> tuple[list[Requirement], int | None]:
    scorecard = get_job_scorecard(job)
    if scorecard.status is not JobScorecardStatus.REVIEWED:
        return [], None
    included = [
        Requirement.model_validate(item.model_dump(exclude={"included"}))
        for item in scorecard.requirements
        if item.included
    ]
    return included, scorecard.version


def require_approved_requirements(
    job: JobDescriptionModel,
) -> tuple[list[Requirement], int]:
    requirements, version = approved_requirements(job)
    if not requirements or version is None:
        raise ApiError(
            "JOB_SCORECARD_NOT_APPROVED",
            "Approve the job scorecard before finding talent.",
            409,
        )
    return requirements, version


def _validate_scorecard_requirements(
    job: JobDescriptionModel, requirements: list[JobScorecardRequirement]
) -> None:
    for item in requirements:
        if not is_verbatim_excerpt(item.text, job.raw_text):
            raise ApiError(
                "JOB_SCORECARD_REQUIREMENT_NOT_FOUND",
                "Every scorecard requirement must be copied from the job description.",
                422,
                {"requirement_id": item.id},
            )
        if contains_protected_scoring_attribute(item.text):
            raise ApiError(
                "JOB_SCORECARD_PROTECTED_ATTRIBUTE",
                "Protected characteristics cannot be included in a job scorecard.",
                422,
                {"requirement_id": item.id},
            )


def _persist_scorecard(
    db: Session,
    job: JobDescriptionModel,
    *,
    requirements: list[JobScorecardRequirement],
    status: JobScorecardStatus,
    version: int,
    reviewed_at: datetime | None,
    warnings: list[str],
    event_type: str,
) -> JobScorecardResponse:
    metadata: dict[str, Any] = {
        "status": status.value,
        "version": version,
        "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
        "warnings": warnings,
    }
    job.requirements = [item.model_dump(mode="json") for item in requirements]
    job.parsed_content = {**job.parsed_content, SCORECARD_METADATA_KEY: metadata}
    audit(
        db,
        event_type,
        "job_description",
        job.id,
        {"version": version, "requirement_count": len(requirements)},
    )
    db.commit()
    db.refresh(job)
    return get_job_scorecard(job)
