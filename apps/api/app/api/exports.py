from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import ComparisonModel
from app.db.session import get_db
from app.schemas.comparison import ComparisonResponse
from app.schemas.export import ExportRequest, InterviewGuideExportRequest
from app.services.exports import (
    comparisons_csv,
    comparisons_json,
    interview_guide_pdf,
    report_pdf,
)

router = APIRouter(prefix="/api/export")
Db = Annotated[Session, Depends(get_db)]


def _load(db: Session, comparison_id: str) -> ComparisonResponse:
    record = db.get(ComparisonModel, comparison_id)
    if record is None or not record.result:
        raise ApiError("COMPARISON_NOT_FOUND", "The comparison was not found.", 404)
    return ComparisonResponse.model_validate(record.result)


@router.post("/report")
def export_report(data: ExportRequest, db: Db) -> Response:
    if len(data.comparison_ids) != 1:
        raise ApiError("ONE_REPORT_REQUIRED", "Select exactly one comparison for a PDF report.")
    result = _load(db, data.comparison_ids[0])
    return Response(
        report_pdf(result),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="talentmatch-report.pdf"'},
    )


@router.post("/json")
def export_json(data: ExportRequest, db: Db) -> Response:
    results = [_load(db, value) for value in data.comparison_ids]
    return Response(
        comparisons_json(results),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="talentmatch-results.json"'},
    )


@router.post("/csv")
def export_csv(data: ExportRequest, db: Db) -> Response:
    results = [_load(db, value) for value in data.comparison_ids]
    return Response(
        comparisons_csv(results),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="talentmatch-summary.csv"'},
    )


@router.post("/interview-guide")
def export_interview_guide(data: InterviewGuideExportRequest, db: Db) -> Response:
    result = _load(db, data.comparison_id)
    return Response(
        interview_guide_pdf(
            result,
            set(data.selected_question_ids),
            data.custom_questions,
        ),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="interview-guide.pdf"'},
    )
