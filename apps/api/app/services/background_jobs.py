import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Event, RLock
from time import perf_counter
from uuid import uuid4

from app.core.errors import ApiError
from app.db.models import JobDescriptionModel
from app.db.session import SessionLocal
from app.providers.base import LLMProvider
from app.schemas.analysis_job import (
    AnalysisJobRequest,
    AnalysisJobResponse,
    AnalysisJobStatus,
    AnalysisProgressEvent,
)
from app.schemas.comparison import ComparisonRequest, WorkflowEvent
from app.schemas.resources import CandidateCreate, JobCreate, ResumeCreate
from app.services.persistence import (
    create_candidate,
    create_job,
    find_candidate_by_resume_content,
    get_candidate,
    persist_result,
)
from app.services.scorecards import approved_requirements as load_approved_requirements
from app.services.scorecards import require_approved_requirements
from app.workflows.comparison import ComparisonWorkflow

logger = logging.getLogger("talentmatch.analysis")


class AnalysisCancelled(Exception):
    pass


@dataclass
class AnalysisJob:
    id: str
    request: AnalysisJobRequest | None
    candidate_count: int
    status: AnalysisJobStatus = AnalysisJobStatus.QUEUED
    completed_count: int = 0
    comparison_ids: list[str] = field(default_factory=list)
    events: list[AnalysisProgressEvent] = field(default_factory=list)
    error: dict[str, str] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    cancel_requested: Event = field(default_factory=Event, repr=False)
    require_approved_scorecard: bool = False


ProviderResolver = Callable[[str, str | None], LLMProvider]


class BackgroundJobManager:
    def __init__(self, provider_resolver: ProviderResolver, max_workers: int = 2) -> None:
        self.provider_resolver = provider_resolver
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="analysis")
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = RLock()

    def start(
        self,
        request: AnalysisJobRequest,
        *,
        require_approved_scorecard: bool = False,
    ) -> AnalysisJobResponse:
        job = AnalysisJob(
            id=str(uuid4()),
            request=request.model_copy(deep=True),
            candidate_count=len(request.candidates),
            require_approved_scorecard=require_approved_scorecard,
        )
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run, job)
        return self.response(job)

    def get(self, job_id: str) -> AnalysisJob:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise ApiError("ANALYSIS_JOB_NOT_FOUND", "The analysis job was not found.", 404)
        return job

    def cancel(self, job_id: str) -> AnalysisJobResponse:
        job = self.get(job_id)
        if job.status in {AnalysisJobStatus.QUEUED, AnalysisJobStatus.RUNNING}:
            job.cancel_requested.set()
            self._emit(job, "cancellation", "Cancellation requested", "running")
        return self.response(job)

    def response(self, job: AnalysisJob) -> AnalysisJobResponse:
        return AnalysisJobResponse(
            job_id=job.id,
            status=job.status,
            candidate_count=job.candidate_count,
            completed_count=job.completed_count,
            comparison_ids=list(job.comparison_ids),
            events_url=f"/api/analysis-jobs/{job.id}/events",
            latest_event=job.events[-1] if job.events else None,
            error=job.error,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )

    def _emit(
        self,
        job: AnalysisJob,
        node: str,
        label: str,
        status: str = "completed",
        candidate_id: str | None = None,
    ) -> None:
        with self._lock:
            job.events.append(
                AnalysisProgressEvent(
                    sequence=len(job.events) + 1,
                    timestamp=datetime.now(UTC),
                    node=node,
                    label=label,
                    status=status,
                    candidate_id=candidate_id,
                )
            )

    def _run(self, job: AnalysisJob) -> None:
        request = job.request
        if request is None:
            return
        job.status = AnalysisJobStatus.RUNNING
        self._emit(job, "workflow", "Analysis started")
        try:
            provider = self.provider_resolver(request.provider, request.credential_session_id)
            with SessionLocal() as db:
                if request.job_id:
                    job_record = db.get(JobDescriptionModel, request.job_id)
                    if job_record is None:
                        raise ApiError(
                            "JOB_NOT_FOUND", "The saved job description was not found.", 404
                        )
                    if job_record.raw_text.strip() != request.job_description_text.strip():
                        raise ApiError(
                            "JOB_DESCRIPTION_MISMATCH",
                            "The submitted job description does not match the saved job.",
                            409,
                        )
                else:
                    title = request.job_title or next(
                        (
                            line.strip()
                            for line in request.job_description_text.splitlines()
                            if line.strip()
                        ),
                        "Untitled role",
                    )
                    job_record = create_job(
                        db,
                        JobCreate(title=title[:200], raw_text=request.job_description_text),
                    )
                scorecard_version: int | None
                if job.require_approved_scorecard:
                    scorecard_requirements, scorecard_version = (
                        require_approved_requirements(job_record)
                    )
                else:
                    scorecard_requirements, scorecard_version = (
                        load_approved_requirements(job_record)
                    )
                for index, item in enumerate(request.candidates, start=1):
                    self._check_cancelled(job)
                    candidate = (
                        get_candidate(db, item.stored_candidate_id)
                        if item.stored_candidate_id
                        else find_candidate_by_resume_content(db, item.resume_text)
                    )
                    if candidate is None and item.stored_candidate_id:
                        raise ApiError(
                            "CANDIDATE_NOT_FOUND",
                            "The selected saved candidate was not found.",
                            404,
                        )
                    if candidate is None:
                        candidate = create_candidate(
                            db,
                            CandidateCreate(
                                display_name=item.display_name,
                                anonymized_name=f"Candidate {index}",
                                resume=ResumeCreate(raw_text=item.resume_text),
                            ),
                        )
                    comparison_request = ComparisonRequest(
                        job_description_text=request.job_description_text,
                        resume_text=item.resume_text,
                        provider=request.provider,
                        credential_session_id=request.credential_session_id,
                        blind_review=request.blind_review,
                        scoring_weights=request.scoring_weights,
                        job_source_references=request.job_source_references,
                        resume_source_references=item.resume_source_references,
                    )
                    started = perf_counter()

                    def on_event(
                        event: WorkflowEvent,
                        candidate_id: str = item.candidate_id,
                    ) -> None:
                        self._check_cancelled(job)
                        self._emit(
                            job,
                            event.node,
                            event.label,
                            event.status,
                            candidate_id,
                        )

                    result = ComparisonWorkflow(provider).run(
                        comparison_request,
                        event_callback=on_event,
                        approved_requirements=scorecard_requirements,
                        scorecard_version=scorecard_version,
                    )
                    display_name = (
                        f"Candidate {index}"
                        if request.blind_review
                        else candidate.display_name
                    )
                    result = result.model_copy(update={"candidate_display_name": display_name})
                    persist_result(
                        db,
                        job_record,
                        candidate,
                        result,
                        request.scoring_weights,
                        round((perf_counter() - started) * 1000),
                        token_usage=getattr(provider, "last_usage", {}),
                        retry_count=getattr(provider, "last_retry_count", 0),
                    )
                    job.comparison_ids.append(result.comparison_id)
                    job.completed_count += 1
                job.status = AnalysisJobStatus.COMPLETED
                self._emit(job, "workflow", "Analysis completed")
        except AnalysisCancelled:
            job.status = AnalysisJobStatus.CANCELLED
            self._emit(job, "workflow", "Analysis cancelled", "cancelled")
        except ApiError as exc:
            job.status = AnalysisJobStatus.FAILED
            job.error = {"code": exc.code, "message": exc.message}
            self._emit(job, "workflow", "Analysis failed", "failed")
        except Exception as exc:
            logger.error(
                "analysis job failed",
                extra={"job_id": job.id, "error_type": type(exc).__name__},
            )
            job.status = AnalysisJobStatus.FAILED
            job.error = {
                "code": "ANALYSIS_FAILED",
                "message": "The analysis could not be completed.",
            }
            self._emit(job, "workflow", "Analysis failed", "failed")
        finally:
            job.completed_at = datetime.now(UTC)
            job.request = None

    @staticmethod
    def _check_cancelled(job: AnalysisJob) -> None:
        if job.cancel_requested.is_set():
            raise AnalysisCancelled
