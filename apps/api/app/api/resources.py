from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.models import CandidateModel, ComparisonModel, JobDescriptionModel, ResumeModel
from app.db.session import get_db
from app.schemas.comparison import ComparisonResponse
from app.schemas.resources import (
    CandidateCreate,
    CandidateOverview,
    CandidateResponse,
    CandidateSummary,
    ComparisonHistoryItem,
    DashboardSummary,
    DeletionSummary,
    JobCreate,
    JobOverview,
    JobResponse,
    JobSummary,
    JobTriagePolicyResponse,
    JobUpdate,
    RecruiterDispositionResponse,
    RecruiterDispositionUpdate,
    ResumeCreate,
    ResumeResponse,
    RetentionRunResponse,
    SettingsResponse,
    SettingsUpdate,
    TriagePolicy,
)
from app.services.persistence import (
    add_candidate_resume,
    audit,
    candidate_summary,
    create_candidate,
    create_job,
    delete_all_data,
    disposition_response,
    get_candidate,
    get_or_create_settings,
    history_item,
    job_summary,
    list_candidate_summaries,
    list_comparisons,
    list_comparisons_for_candidate,
    list_comparisons_for_job,
    list_job_summaries,
    run_retention,
    update_job,
    update_job_triage_policy,
    update_recruiter_disposition,
    update_settings,
)

router = APIRouter(prefix="/api")
Db = Annotated[Session, Depends(get_db)]
PageSize = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0)]


@router.get("/diagnostics")
def diagnostics(db: Db) -> dict[str, object]:
    settings = get_settings()
    if not settings.diagnostics_enabled:
        raise ApiError("DIAGNOSTICS_DISABLED", "Diagnostics are disabled.", 404)
    return {
        "environment": settings.environment,
        "database_dialect": db.bind.dialect.name if db.bind else "unknown",
        "jobs": db.scalar(select(func.count(JobDescriptionModel.id))) or 0,
        "candidates": db.scalar(select(func.count(CandidateModel.id))) or 0,
        "comparisons": db.scalar(select(func.count(ComparisonModel.id))) or 0,
        "credential_values_exposed": False,
    }


def _settings_response(settings) -> SettingsResponse:  # type: ignore[no-untyped-def]
    return SettingsResponse(
        id=settings.id,
        provider=settings.provider,
        selected_model=settings.selected_model,
        retention_policy_days=settings.retention_policy_days,
        scoring_configuration=settings.scoring_configuration,
        default_triage_policy=settings.default_triage_policy,
        skill_taxonomy=settings.skill_taxonomy,
        blind_review_enabled=settings.blind_review_enabled,
        credential_configured=bool(settings.encrypted_api_key_reference),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.post("/jobs", response_model=JobResponse, status_code=201)
def post_job(data: JobCreate, db: Db) -> JobDescriptionModel:
    return create_job(db, data)


@router.get("/jobs", response_model=list[JobSummary])
def get_jobs(db: Db, limit: PageSize = 25, offset: PageOffset = 0) -> list[JobSummary]:
    return list_job_summaries(db, offset, limit)


@router.get("/jobs/{job_id}/overview", response_model=JobOverview)
def get_job_overview(job_id: str, db: Db) -> JobOverview:
    job = db.get(JobDescriptionModel, job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "The job description was not found.", 404)
    comparisons = list_comparisons_for_job(db, job_id)
    return JobOverview(
        job=job_summary(db, job),
        comparisons=[history_item(item) for item in comparisons],
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Db) -> JobDescriptionModel:
    job = db.get(JobDescriptionModel, job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "The job description was not found.", 404)
    return job


@router.put("/jobs/{job_id}", response_model=JobResponse)
def put_job(job_id: str, data: JobUpdate, db: Db) -> JobDescriptionModel:
    job = db.get(JobDescriptionModel, job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "The job description was not found.", 404)
    return update_job(db, job, data)


@router.get("/jobs/{job_id}/triage-policy", response_model=JobTriagePolicyResponse)
def get_job_triage_policy(job_id: str, db: Db) -> JobTriagePolicyResponse:
    job = db.get(JobDescriptionModel, job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "The job description was not found.", 404)
    return JobTriagePolicyResponse(
        job_id=job.id,
        policy=TriagePolicy.model_validate(job.triage_policy or {}),
        version=job.triage_policy_version,
        updated_at=job.updated_at,
    )


@router.put("/jobs/{job_id}/triage-policy", response_model=JobTriagePolicyResponse)
def put_job_triage_policy(job_id: str, data: TriagePolicy, db: Db) -> JobTriagePolicyResponse:
    job = db.get(JobDescriptionModel, job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "The job description was not found.", 404)
    updated = update_job_triage_policy(db, job, data)
    return JobTriagePolicyResponse(
        job_id=updated.id,
        policy=TriagePolicy.model_validate(updated.triage_policy),
        version=updated.triage_policy_version,
        updated_at=updated.updated_at,
    )


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, db: Db) -> Response:
    job = db.get(JobDescriptionModel, job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "The job description was not found.", 404)
    db.delete(job)
    audit(db, "job.deleted", "job_description", job_id)
    db.commit()
    return Response(status_code=204)


@router.post("/candidates", response_model=CandidateResponse, status_code=201)
def post_candidate(data: CandidateCreate, db: Db) -> CandidateModel:
    return create_candidate(db, data)


@router.get("/candidates", response_model=list[CandidateSummary])
def get_candidates(db: Db, limit: PageSize = 25, offset: PageOffset = 0) -> list[CandidateSummary]:
    return list_candidate_summaries(db, offset, limit)


@router.get("/candidates/{candidate_id}/overview", response_model=CandidateOverview)
def get_candidate_overview(candidate_id: str, db: Db) -> CandidateOverview:
    candidate = get_candidate(db, candidate_id)
    if candidate is None:
        raise ApiError("CANDIDATE_NOT_FOUND", "The candidate was not found.", 404)
    comparisons = list_comparisons_for_candidate(db, candidate_id)
    return CandidateOverview(
        candidate=CandidateResponse.model_validate(candidate),
        summary=candidate_summary(db, candidate),
        comparisons=[history_item(item) for item in comparisons],
    )


@router.post(
    "/candidates/{candidate_id}/resumes",
    response_model=ResumeResponse,
    status_code=201,
)
def post_candidate_resume(candidate_id: str, data: ResumeCreate, db: Db) -> ResumeModel:
    candidate = get_candidate(db, candidate_id)
    if candidate is None:
        raise ApiError("CANDIDATE_NOT_FOUND", "The candidate was not found.", 404)
    return add_candidate_resume(db, candidate, data)


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
def get_candidate_route(candidate_id: str, db: Db) -> CandidateModel:
    candidate = get_candidate(db, candidate_id)
    if candidate is None:
        raise ApiError("CANDIDATE_NOT_FOUND", "The candidate was not found.", 404)
    return candidate


@router.delete("/candidates/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: str, db: Db) -> Response:
    candidate = db.get(CandidateModel, candidate_id)
    if candidate is None:
        raise ApiError("CANDIDATE_NOT_FOUND", "The candidate was not found.", 404)
    db.delete(candidate)
    audit(db, "candidate.deleted", "candidate", candidate_id)
    db.commit()
    return Response(status_code=204)


@router.get("/comparisons", response_model=list[ComparisonHistoryItem])
def get_comparisons(
    db: Db, limit: PageSize = 25, offset: PageOffset = 0
) -> list[ComparisonHistoryItem]:
    return [history_item(item) for item in list_comparisons(db, offset, limit)]


@router.get("/comparisons/{comparison_id}", response_model=ComparisonResponse)
def get_comparison(comparison_id: str, db: Db) -> ComparisonResponse:
    comparison = db.get(ComparisonModel, comparison_id)
    if comparison is None or not comparison.result:
        raise ApiError("COMPARISON_NOT_FOUND", "The comparison was not found.", 404)
    return ComparisonResponse.model_validate(comparison.result)


@router.get(
    "/comparisons/{comparison_id}/disposition",
    response_model=RecruiterDispositionResponse,
)
def get_comparison_disposition(comparison_id: str, db: Db) -> RecruiterDispositionResponse:
    comparison = db.get(ComparisonModel, comparison_id)
    if comparison is None or not comparison.result:
        raise ApiError("COMPARISON_NOT_FOUND", "The comparison was not found.", 404)
    return disposition_response(comparison)


@router.put(
    "/comparisons/{comparison_id}/disposition",
    response_model=RecruiterDispositionResponse,
)
def put_comparison_disposition(
    comparison_id: str, data: RecruiterDispositionUpdate, db: Db
) -> RecruiterDispositionResponse:
    comparison = db.get(ComparisonModel, comparison_id)
    if comparison is None or not comparison.result:
        raise ApiError("COMPARISON_NOT_FOUND", "The comparison was not found.", 404)
    return update_recruiter_disposition(db, comparison, data)


@router.delete("/comparisons/{comparison_id}", status_code=204)
def delete_comparison(comparison_id: str, db: Db) -> Response:
    comparison = db.get(ComparisonModel, comparison_id)
    if comparison is None:
        raise ApiError("COMPARISON_NOT_FOUND", "The comparison was not found.", 404)
    db.delete(comparison)
    audit(db, "comparison.deleted", "comparison", comparison_id)
    db.commit()
    return Response(status_code=204)


@router.get("/settings", response_model=SettingsResponse)
def get_settings_route(db: Db) -> SettingsResponse:
    return _settings_response(get_or_create_settings(db))


@router.put("/settings", response_model=SettingsResponse)
def put_settings(data: SettingsUpdate, db: Db) -> SettingsResponse:
    return _settings_response(update_settings(db, data))


@router.get("/scoring-config")
def get_scoring_config(db: Db) -> dict[str, object]:
    return get_or_create_settings(db).scoring_configuration


@router.put("/scoring-config")
def put_scoring_config(data: SettingsUpdate, db: Db) -> dict[str, object]:
    return update_settings(db, data).scoring_configuration


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(db: Db) -> DashboardSummary:
    comparisons = list_comparisons(db, 0, 5)
    total = db.scalar(select(func.count(ComparisonModel.id))) or 0
    average = db.scalar(select(func.avg(ComparisonModel.fit_score))) or 0.0
    clarification = (
        db.scalar(
            select(func.count(ComparisonModel.id)).where(
                ComparisonModel.recommendation == "consider_with_clarifications"
            )
        )
        or 0
    )
    settings = get_or_create_settings(db)
    return DashboardSummary(
        total_comparisons=total,
        active_jobs=db.scalar(select(func.count(JobDescriptionModel.id))) or 0,
        candidates_analyzed=db.scalar(select(func.count(CandidateModel.id))) or 0,
        average_fit_score=round(float(average), 1),
        requiring_clarification=clarification,
        provider_status="configured" if settings.provider != "mock" else "local mock ready",
        retention_days=settings.retention_policy_days,
        recent_comparisons=[history_item(item) for item in comparisons],
    )


@router.delete("/privacy/all-data", response_model=DeletionSummary)
def privacy_delete_all(db: Db) -> DeletionSummary:
    return DeletionSummary(**delete_all_data(db))


@router.post("/privacy/retention/run", response_model=RetentionRunResponse)
def retention_run(db: Db) -> RetentionRunResponse:
    retention_days = get_or_create_settings(db).retention_policy_days
    cutoff, counts = run_retention(db, retention_days)
    return RetentionRunResponse(cutoff=cutoff, **counts)
