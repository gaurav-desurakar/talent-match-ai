from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.providers import provider_for_request
from app.core.errors import ApiError
from app.db.models import JobDescriptionModel
from app.db.session import get_db
from app.schemas.resources import (
    JobScorecardExtractionRequest,
    JobScorecardResponse,
    JobScorecardUpdateRequest,
)
from app.services.scorecards import (
    get_job_scorecard,
    save_extracted_scorecard,
    save_reviewed_scorecard,
)

router = APIRouter(prefix="/api/jobs")
Db = Annotated[Session, Depends(get_db)]


def _get_job(db: Session, job_id: str) -> JobDescriptionModel:
    job = db.get(JobDescriptionModel, job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "The job description was not found.", 404)
    return job


@router.get("/{job_id}/scorecard", response_model=JobScorecardResponse)
def get_scorecard(job_id: str, db: Db) -> JobScorecardResponse:
    return get_job_scorecard(_get_job(db, job_id))


@router.post("/{job_id}/scorecard/extract", response_model=JobScorecardResponse)
def extract_scorecard(
    job_id: str,
    data: JobScorecardExtractionRequest,
    db: Db,
) -> JobScorecardResponse:
    job = _get_job(db, job_id)
    provider = provider_for_request(data.provider, data.credential_session_id)
    analysis = provider.generate_job_analysis(job.raw_text)
    return save_extracted_scorecard(db, job, analysis)


@router.put("/{job_id}/scorecard", response_model=JobScorecardResponse)
def put_scorecard(
    job_id: str,
    data: JobScorecardUpdateRequest,
    db: Db,
) -> JobScorecardResponse:
    return save_reviewed_scorecard(
        db,
        _get_job(db, job_id),
        data.requirements,
        approve=data.approve,
    )
