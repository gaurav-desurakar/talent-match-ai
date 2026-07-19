import os

from fastapi import APIRouter, Response
from pydantic import AnyHttpUrl, TypeAdapter

from app.core.config import get_settings
from app.core.errors import ApiError
from app.providers.base import LLMProvider
from app.providers.factory import create_provider
from app.providers.mock import MockProvider
from app.schemas.provider import (
    CredentialSessionRequest,
    CredentialSessionResponse,
    ProviderValidationRequest,
    ProviderValidationResponse,
)
from app.services.credential_store import CredentialSessionStore, mask_key

router = APIRouter(prefix="/api/providers")
credential_store = CredentialSessionStore(get_settings().credential_session_ttl_seconds)
SYSTEM_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
}


def provider_for_request(provider_id: str, session_id: str | None) -> LLMProvider:
    if provider_id == "mock":
        return MockProvider()
    if not session_id:
        raise ApiError(
            "CREDENTIAL_SESSION_REQUIRED",
            "Configure a provider session before starting external analysis.",
            400,
        )
    session = credential_store.get(session_id)
    if session.provider.value != provider_id:
        raise ApiError(
            "PROVIDER_SESSION_MISMATCH",
            "The credential session does not match the selected provider.",
            400,
        )
    return create_provider(session)


@router.post("/session", response_model=CredentialSessionResponse, status_code=201)
def create_credential_session(data: CredentialSessionRequest) -> CredentialSessionResponse:
    api_key = data.api_key or (
        os.getenv(SYSTEM_KEY_ENV[data.provider.value])
        if data.provider.value in SYSTEM_KEY_ENV
        else None
    )
    if data.provider.value not in {"mock", "ollama"} and not api_key:
        raise ApiError(
            "PROVIDER_API_KEY_REQUIRED",
            "An API key is required for the selected provider.",
            400,
        )
    base_url = data.base_url
    if data.provider.value == "ollama" and base_url is None:
        configured = os.getenv("OLLAMA_BASE_URL")
        if configured:
            base_url = TypeAdapter(AnyHttpUrl).validate_python(configured)
    session = credential_store.create(
        data.model_copy(update={"api_key": api_key, "base_url": base_url})
    )
    return CredentialSessionResponse(
        session_id=session.session_id,
        provider=session.provider,
        model=session.model,
        base_url=session.base_url,
        masked_key=mask_key(session.api_key),
        expires_at=session.expires_at,
        sends_documents_externally=session.provider.value not in {"mock", "ollama"},
    )


@router.delete("/session/{session_id}", status_code=204)
def remove_credential_session(session_id: str) -> Response:
    if not credential_store.remove(session_id):
        raise ApiError(
            "CREDENTIAL_SESSION_NOT_FOUND",
            "The provider session is missing or has expired.",
            404,
        )
    return Response(status_code=204)


@router.post("/validate", response_model=ProviderValidationResponse)
def validate_provider(data: ProviderValidationRequest) -> ProviderValidationResponse:
    session = credential_store.get(data.credential_session_id)
    provider = create_provider(session)
    provider.validate_credentials()
    return ProviderValidationResponse(
        provider=session.provider,
        status="available",
        models=provider.list_models(),
        message="Connection succeeded. No candidate documents were transmitted.",
    )


@router.get("/{provider_id}/models", response_model=list[str])
def provider_models(provider_id: str) -> list[str]:
    from app.schemas.provider import ProviderId
    from app.services.credential_store import DEFAULT_MODELS

    try:
        provider = ProviderId(provider_id)
    except ValueError:
        raise ApiError("PROVIDER_NOT_FOUND", "The provider was not found.", 404) from None
    return [DEFAULT_MODELS[provider]]
