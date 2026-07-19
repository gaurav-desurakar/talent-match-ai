from uuid import uuid4

from app.providers.base import LLMProvider
from app.schemas.comparison import (
    BatchComparisonRequest,
    BatchComparisonResponse,
    CandidateComparisonResult,
    ComparisonRequest,
)
from app.workflows.comparison import ComparisonWorkflow


class BatchComparisonWorkflow:
    """Run independent comparisons in input order without automatically ranking candidates."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def run(self, request: BatchComparisonRequest) -> BatchComparisonResponse:
        comparisons: list[CandidateComparisonResult] = []
        for index, candidate in enumerate(request.candidates, start=1):
            comparison_request = ComparisonRequest(
                job_description_text=request.job_description_text,
                resume_text=candidate.resume_text,
                provider=request.provider,
                credential_session_id=request.credential_session_id,
                blind_review=request.blind_review,
                scoring_weights=request.scoring_weights,
                job_source_references=request.job_source_references,
                resume_source_references=candidate.resume_source_references,
            )
            result = ComparisonWorkflow(self.provider).run(comparison_request)
            display_name = f"Candidate {index}" if request.blind_review else candidate.display_name
            result = result.model_copy(update={"candidate_display_name": display_name})
            comparisons.append(
                CandidateComparisonResult(
                    candidate_id=candidate.candidate_id,
                    display_name=display_name,
                    comparison=result,
                )
            )
        return BatchComparisonResponse(
            batch_id=str(uuid4()),
            status="completed",
            candidate_count=len(comparisons),
            comparisons=comparisons,
        )
