from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.api.providers import provider_for_request
from app.core.config import get_settings
from app.providers.mock import MockProvider
from app.schemas.comparison import (
    BatchComparisonRequest,
    BatchComparisonResponse,
    ComparisonRequest,
    ComparisonResponse,
    ProviderInfo,
)
from app.schemas.document import DocumentExtractionResponse, DocumentType
from app.services.document_ingestion import ingest_document, read_upload_limited
from app.workflows.batch_comparison import BatchComparisonWorkflow
from app.workflows.comparison import ComparisonWorkflow

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/providers", response_model=list[ProviderInfo])
def list_providers() -> list[ProviderInfo]:
    provider = MockProvider()
    return [
        ProviderInfo(
            id=provider.id,
            name="Deterministic local mock",
            models=provider.list_models(),
            requires_api_key=False,
            sends_documents_externally=False,
            status=provider.health_check(),
        ),
        ProviderInfo(
            id="openai",
            name="OpenAI",
            models=["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
            requires_api_key=True,
            sends_documents_externally=True,
            status="not_configured",
        ),
        ProviderInfo(
            id="anthropic",
            name="Anthropic",
            models=["claude-sonnet-4-5", "claude-haiku-4-5"],
            requires_api_key=True,
            sends_documents_externally=True,
            status="not_configured",
        ),
        ProviderInfo(
            id="google",
            name="Google Gemini",
            models=["gemini-2.5-flash", "gemini-2.5-pro"],
            requires_api_key=True,
            sends_documents_externally=True,
            status="not_configured",
        ),
        ProviderInfo(
            id="groq",
            name="Groq",
            models=["llama-3.3-70b-versatile", "openai/gpt-oss-20b"],
            requires_api_key=True,
            sends_documents_externally=True,
            status="not_configured",
        ),
        ProviderInfo(
            id="compatible",
            name="OpenAI-compatible endpoint",
            models=["default"],
            requires_api_key=True,
            sends_documents_externally=True,
            status="not_configured",
        ),
        ProviderInfo(
            id="ollama",
            name="Ollama local model",
            models=["llama3.2", "qwen2.5"],
            requires_api_key=False,
            sends_documents_externally=False,
            status="not_configured",
        ),
    ]


@router.post("/comparisons", response_model=ComparisonResponse, status_code=201)
def create_comparison(request: ComparisonRequest) -> ComparisonResponse:
    provider = provider_for_request(request.provider, request.credential_session_id)
    return ComparisonWorkflow(provider).run(request)


@router.post("/comparisons/batch", response_model=BatchComparisonResponse, status_code=201)
def create_batch_comparison(request: BatchComparisonRequest) -> BatchComparisonResponse:
    provider = provider_for_request(request.provider, request.credential_session_id)
    return BatchComparisonWorkflow(provider).run(request)


async def _extract_upload(
    file: UploadFile, document_type: DocumentType
) -> DocumentExtractionResponse:
    settings = get_settings()
    data = await read_upload_limited(file, settings.max_upload_bytes)
    return ingest_document(
        data,
        file.filename or "upload",
        document_type,
        max_text_characters=settings.max_text_characters,
        max_pdf_pages=settings.max_pdf_pages,
    )


@router.post(
    "/job-descriptions/upload",
    response_model=DocumentExtractionResponse,
    status_code=201,
)
async def upload_job_description(
    file: Annotated[UploadFile, File()],
) -> DocumentExtractionResponse:
    return await _extract_upload(file, DocumentType.JOB_DESCRIPTION)


@router.post("/resumes/upload", response_model=DocumentExtractionResponse, status_code=201)
async def upload_resume(
    file: Annotated[UploadFile, File()],
) -> DocumentExtractionResponse:
    return await _extract_upload(file, DocumentType.RESUME)
