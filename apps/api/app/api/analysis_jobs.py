import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.providers import provider_for_request
from app.core.errors import ApiError
from app.db.models import CandidateModel, ComparisonModel, JobDescriptionModel, ResumeModel
from app.db.session import get_db
from app.schemas.analysis_job import (
    AnalysisJobRequest,
    AnalysisJobResponse,
    AnalysisJobStatus,
    AnalysisRetryRequest,
)
from app.schemas.comparison import CandidateComparisonInput, ScoringWeights
from app.services.background_jobs import BackgroundJobManager
from app.services.scorecards import require_approved_requirements

router = APIRouter(prefix="/api/analysis-jobs")
job_manager = BackgroundJobManager(provider_for_request)
Db = Annotated[Session, Depends(get_db)]


@router.post("", response_model=AnalysisJobResponse, status_code=202)
def start_analysis_job(request: AnalysisJobRequest, db: Db) -> AnalysisJobResponse:
    if request.job_id:
        job = db.get(JobDescriptionModel, request.job_id)
        if job is None:
            raise ApiError("JOB_NOT_FOUND", "The saved job description was not found.", 404)
        if job.raw_text.strip() != request.job_description_text.strip():
            raise ApiError(
                "JOB_DESCRIPTION_MISMATCH",
                "The submitted job description does not match the saved job.",
                409,
            )
        require_approved_requirements(job)
    for candidate_input in request.candidates:
        if not candidate_input.stored_candidate_id or not candidate_input.resume_id:
            continue
        resume = db.scalar(
            select(ResumeModel).where(
                ResumeModel.id == candidate_input.resume_id,
                ResumeModel.candidate_id == candidate_input.stored_candidate_id,
            )
        )
        if resume is None:
            raise ApiError(
                "CANDIDATE_RESUME_NOT_FOUND",
                "The selected saved resume was not found for this candidate.",
                404,
            )
        if resume.raw_text.strip() != candidate_input.resume_text.strip():
            raise ApiError(
                "CANDIDATE_RESUME_MISMATCH",
                "The submitted resume text does not match the saved resume version.",
                409,
            )
    return job_manager.start(
        request,
        require_approved_scorecard=request.job_id is not None,
    )


@router.get("/{job_id}", response_model=AnalysisJobResponse)
def get_analysis_job(job_id: str) -> AnalysisJobResponse:
    return job_manager.response(job_manager.get(job_id))


@router.delete("/{job_id}", response_model=AnalysisJobResponse)
def cancel_analysis_job(job_id: str) -> AnalysisJobResponse:
    return job_manager.cancel(job_id)


@router.post("/retry/{comparison_id}", response_model=AnalysisJobResponse, status_code=202)
def retry_analysis_job(
    comparison_id: str,
    data: AnalysisRetryRequest,
    db: Db,
) -> AnalysisJobResponse:
    comparison = db.scalar(
        select(ComparisonModel)
        .options(
            selectinload(ComparisonModel.job_description),
            selectinload(ComparisonModel.candidate).selectinload(CandidateModel.resumes),
        )
        .where(ComparisonModel.id == comparison_id)
    )
    if comparison is None or not comparison.candidate.resumes:
        raise ApiError("COMPARISON_NOT_FOUND", "The comparison was not found.", 404)
    resume = max(comparison.candidate.resumes, key=lambda item: item.created_at)
    weights = ScoringWeights.model_validate(comparison.scoring_configuration_snapshot)
    return job_manager.start(
        AnalysisJobRequest(
            job_id=comparison.job_description.id,
            job_title=comparison.job_description.title,
            job_description_text=comparison.job_description.raw_text,
            candidates=[
                CandidateComparisonInput(
                    candidate_id=comparison.candidate.id,
                    display_name=comparison.candidate.display_name,
                    stored_candidate_id=comparison.candidate.id,
                    resume_id=resume.id,
                    resume_text=resume.raw_text,
                )
            ],
            provider=data.provider,
            credential_session_id=data.credential_session_id,
            blind_review=data.blind_review,
            scoring_weights=weights,
        )
    )


@router.get("/{job_id}/events")
def analysis_job_events(job_id: str) -> StreamingResponse:
    job = job_manager.get(job_id)

    async def stream() -> AsyncIterator[str]:
        cursor = 0
        while True:
            while cursor < len(job.events):
                event = job.events[cursor]
                cursor += 1
                data = json.dumps(event.model_dump(mode="json"))
                yield f"id: {event.sequence}\nevent: progress\ndata: {data}\n\n"
            if job.status in {
                AnalysisJobStatus.COMPLETED,
                AnalysisJobStatus.FAILED,
                AnalysisJobStatus.CANCELLED,
            }:
                yield f"event: complete\ndata: {job_manager.response(job).model_dump_json()}\n\n"
                break
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.2)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
