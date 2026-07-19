from app.providers.base import LLMProvider
from app.providers.http_adapters import (
    AnthropicProvider,
    CompatibleProvider,
    GoogleProvider,
    GroqProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
)
from app.providers.mock import MockProvider
from app.schemas.provider import ProviderId
from app.services.credential_store import CredentialSession


def create_provider(session: CredentialSession) -> LLMProvider:
    providers: dict[ProviderId, type[LLMProvider]] = {
        ProviderId.OPENAI: OpenAICompatibleProvider,
        ProviderId.ANTHROPIC: AnthropicProvider,
        ProviderId.GOOGLE: GoogleProvider,
        ProviderId.GROQ: GroqProvider,
        ProviderId.COMPATIBLE: CompatibleProvider,
        ProviderId.OLLAMA: OllamaProvider,
    }
    if session.provider is ProviderId.MOCK:
        return MockProvider()
    return providers[session.provider](session)  # type: ignore[call-arg]
