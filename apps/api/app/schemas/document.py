from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"


class SourceLocationType(StrEnum):
    LINE = "line"
    PARAGRAPH = "paragraph"
    TABLE_ROW = "table_row"


class DocumentSourceReference(BaseModel):
    id: Annotated[str, Field(min_length=1, max_length=200)]
    text: Annotated[str, Field(min_length=1, max_length=2_000)]
    location_type: SourceLocationType
    page: int | None = None
    paragraph: int | None = None
    line: int | None = None
    table: int | None = None
    row: int | None = None


class ExtractedSection(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    text: str
    source_reference_ids: list[str]


class DocumentExtractionResponse(BaseModel):
    document_id: str
    document_type: DocumentType
    filename: str
    media_type: str
    sha256: str
    raw_text: str
    sections: list[ExtractedSection]
    source_references: list[DocumentSourceReference]
    warnings: list[str] = Field(default_factory=list)
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    character_count: int = Field(ge=0)
