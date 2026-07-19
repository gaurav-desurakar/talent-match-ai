from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class ProviderId(StrEnum):
    MOCK = "mock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    COMPATIBLE = "compatible"
    OLLAMA = "ollama"


class CredentialSessionRequest(BaseModel):
    provider: ProviderId
    api_key: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    model: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    base_url: AnyHttpUrl | None = None
    # Full document analysis takes materially longer than the one-token
    # credential check. Keep the default below the application's five-minute ceiling,
    # but give structured generation enough time to finish.
    timeout_seconds: Annotated[float, Field(ge=1, le=300)] = 180
    max_retries: Annotated[int, Field(ge=0, le=5)] = 2

    @model_validator(mode="after")
    def validate_provider_configuration(self) -> "CredentialSessionRequest":
        if self.provider is ProviderId.COMPATIBLE and self.base_url is None:
            raise ValueError("A base URL is required for a compatible provider")
        return self


class CredentialSessionResponse(BaseModel):
    session_id: str
    provider: ProviderId
    model: str
    base_url: str
    masked_key: str | None
    expires_at: datetime
    storage_mode: str = "server_memory"
    sends_documents_externally: bool


class ProviderValidationRequest(BaseModel):
    credential_session_id: str


class ProviderValidationResponse(BaseModel):
    provider: ProviderId
    status: str
    models: list[str]
    message: str
