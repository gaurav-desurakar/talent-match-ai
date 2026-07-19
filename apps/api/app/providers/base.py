from abc import ABC, abstractmethod

from app.schemas.comparison import ProviderAnalysis, ProviderJobAnalysis, Requirement
from app.schemas.document import DocumentSourceReference


class LLMProvider(ABC):
    id: str
    model: str

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate configuration without exposing credential material."""

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return normalized model metadata."""

    @abstractmethod
    def generate_analysis(
        self,
        job_description_text: str,
        resume_text: str,
        *,
        blind_review: bool,
        job_source_references: list[DocumentSourceReference] | None = None,
        resume_source_references: list[DocumentSourceReference] | None = None,
        approved_requirements: list[Requirement] | None = None,
    ) -> ProviderAnalysis:
        """Return schema-validated structured evidence classifications."""

    @abstractmethod
    def generate_job_analysis(
        self,
        job_description_text: str,
        *,
        job_source_references: list[DocumentSourceReference] | None = None,
    ) -> ProviderJobAnalysis:
        """Return source-grounded job requirements for recruiter review."""

    @abstractmethod
    def health_check(self) -> str:
        """Return a normalized health state."""
