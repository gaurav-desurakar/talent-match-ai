from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    comparison_ids: list[str] = Field(min_length=1, max_length=5)


class InterviewGuideExportRequest(BaseModel):
    comparison_id: str
    selected_question_ids: list[str] = Field(default_factory=list, max_length=100)
    custom_questions: list[str] = Field(default_factory=list, max_length=50)
