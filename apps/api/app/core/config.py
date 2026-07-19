from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TalentMatch AI API"
    environment: str = Field(default="development", validation_alias="TALENTMATCH_ENV")
    cors_origins: str = Field(
        default="http://localhost:3000", validation_alias="TALENTMATCH_CORS_ORIGINS"
    )
    max_text_characters: int = Field(
        default=100_000,
        ge=1_000,
        le=1_000_000,
        validation_alias="TALENTMATCH_MAX_TEXT_CHARACTERS",
    )
    max_upload_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        le=25 * 1024 * 1024,
        validation_alias="TALENTMATCH_MAX_UPLOAD_BYTES",
    )
    max_pdf_pages: int = Field(
        default=100,
        ge=1,
        le=500,
        validation_alias="TALENTMATCH_MAX_PDF_PAGES",
    )
    database_url: str = Field(
        default="sqlite:///./talentmatch.db",
        validation_alias="TALENTMATCH_DATABASE_URL",
    )
    credential_session_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86_400,
        validation_alias="TALENTMATCH_CREDENTIAL_SESSION_TTL_SECONDS",
    )
    diagnostics_enabled: bool = Field(
        default=False,
        validation_alias="TALENTMATCH_DIAGNOSTICS_ENABLED",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
