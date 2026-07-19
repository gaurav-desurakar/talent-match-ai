from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock
from uuid import uuid4

from app.core.errors import ApiError
from app.schemas.provider import CredentialSessionRequest, ProviderId


@dataclass(frozen=True)
class CredentialSession:
    session_id: str
    provider: ProviderId
    api_key: str | None = field(repr=False)
    model: str
    base_url: str
    timeout_seconds: float
    max_retries: int
    expires_at: datetime


DEFAULT_MODELS = {
    ProviderId.MOCK: "mock-evidence-v1",
    ProviderId.OPENAI: "gpt-4.1-mini",
    ProviderId.ANTHROPIC: "claude-sonnet-4-5",
    ProviderId.GOOGLE: "gemini-2.5-flash",
    ProviderId.GROQ: "llama-3.3-70b-versatile",
    ProviderId.COMPATIBLE: "default",
    ProviderId.OLLAMA: "llama3.2",
}
DEFAULT_BASE_URLS = {
    ProviderId.MOCK: "local://mock",
    ProviderId.OPENAI: "https://api.openai.com",
    ProviderId.ANTHROPIC: "https://api.anthropic.com",
    ProviderId.GOOGLE: "https://generativelanguage.googleapis.com",
    ProviderId.GROQ: "https://api.groq.com/openai",
    ProviderId.COMPATIBLE: "",
    ProviderId.OLLAMA: "http://localhost:11434",
}


def mask_key(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:3]}{'•' * 8}{value[-4:]}"


class CredentialSessionStore:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, CredentialSession] = {}
        self._lock = RLock()

    def create(self, data: CredentialSessionRequest) -> CredentialSession:
        now = datetime.now(UTC)
        session = CredentialSession(
            session_id=str(uuid4()),
            provider=data.provider,
            api_key=data.api_key,
            model=data.model or DEFAULT_MODELS[data.provider],
            base_url=str(data.base_url).rstrip("/")
            if data.base_url
            else DEFAULT_BASE_URLS[data.provider],
            timeout_seconds=data.timeout_seconds,
            max_retries=data.max_retries,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        with self._lock:
            self._purge_expired(now)
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> CredentialSession:
        now = datetime.now(UTC)
        with self._lock:
            self._purge_expired(now)
            session = self._sessions.get(session_id)
        if session is None:
            raise ApiError(
                "CREDENTIAL_SESSION_NOT_FOUND",
                "The provider session is missing or has expired.",
                404,
            )
        return session

    def remove(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def _purge_expired(self, now: datetime) -> None:
        expired = [key for key, value in self._sessions.items() if value.expires_at <= now]
        for key in expired:
            del self._sessions[key]
