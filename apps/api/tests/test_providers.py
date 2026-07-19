import json

import httpx
import pytest

from app.providers.http_adapters import OpenAICompatibleProvider, ProviderRequestError
from app.providers.mock import MockProvider
from app.schemas.comparison import MatchType
from app.schemas.provider import CredentialSessionRequest, ProviderId
from app.services.credential_store import CredentialSessionStore, mask_key


def test_credential_session_masks_and_removes_secret() -> None:
    store = CredentialSessionStore(ttl_seconds=60)
    session = store.create(
        CredentialSessionRequest(
            provider=ProviderId.OPENAI,
            api_key="sk-super-secret-value-1234",
        )
    )
    masked = mask_key(session.api_key)
    assert masked is not None
    assert "super-secret" not in masked
    assert store.get(session.session_id).api_key == "sk-super-secret-value-1234"
    assert store.remove(session.session_id) is True
    with pytest.raises(Exception, match="missing or has expired"):
        store.get(session.session_id)


def test_provider_session_api_never_returns_key(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post(
        "/api/providers/session",
        json={"provider": "openai", "api_key": "sk-private-value-123456"},
    )
    assert response.status_code == 201
    body = response.text
    assert "sk-private-value-123456" not in body
    assert response.json()["storage_mode"] == "server_memory"
    assert response.json()["sends_documents_externally"] is True


def test_mock_provider_session_can_be_tested_and_removed(client) -> None:  # type: ignore[no-untyped-def]
    created = client.post("/api/providers/session", json={"provider": "mock"})
    assert created.status_code == 201
    session_id = created.json()["session_id"]
    validation = client.post(
        "/api/providers/validate",
        json={"credential_session_id": session_id},
    )
    assert validation.status_code == 200
    assert validation.json()["status"] == "available"
    assert validation.json()["models"] == ["mock-evidence-v1"]
    assert client.delete(f"/api/providers/session/{session_id}").status_code == 204
    missing = client.delete(f"/api/providers/session/{session_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "CREDENTIAL_SESSION_NOT_FOUND"


def test_provider_env_key_fallback_and_model_lookup(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENAI_API_KEY", "system-openai-key")
    response = client.post("/api/providers/session", json={"provider": "openai"})
    assert response.status_code == 201
    assert "system-openai-key" not in response.text
    assert client.get("/api/providers/openai/models").json() == ["gpt-4.1-mini"]
    assert client.get("/api/providers/not-real/models").status_code == 404


def test_external_provider_requires_session_or_environment_key(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post("/api/providers/session", json={"provider": "anthropic"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PROVIDER_API_KEY_REQUIRED"


def test_external_comparison_requires_matching_session(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post(
        "/api/comparisons",
        json={
            "provider": "openai",
            "job_description_text": "AI Engineer requiring production Python experience.",
            "resume_text": "Candidate built Python production services for enterprise teams.",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CREDENTIAL_SESSION_REQUIRED"


def test_adapter_normalizes_authentication_and_invalid_output() -> None:
    store = CredentialSessionStore()
    session = store.create(
        CredentialSessionRequest(provider=ProviderId.OPENAI, api_key="secret-api-key")
    )

    def auth_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret-api-key"
        return httpx.Response(401, json={"error": "invalid"})

    provider = OpenAICompatibleProvider(session, transport=httpx.MockTransport(auth_handler))
    with pytest.raises(ProviderRequestError) as auth_error:
        provider.validate_credentials()
    assert auth_error.value.code == "PROVIDER_AUTHENTICATION_FAILED"

    def invalid_handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"invalid": True})}}]},
        )

    provider = OpenAICompatibleProvider(session, transport=httpx.MockTransport(invalid_handler))
    with pytest.raises(ProviderRequestError) as invalid_error:
        provider.generate_analysis(
            "AI Engineer requiring production Python experience.",
            "Candidate built production Python services for enterprise teams.",
            blind_review=True,
        )
    assert invalid_error.value.code == "PROVIDER_INVALID_STRUCTURED_OUTPUT"


def test_provider_session_uses_full_analysis_timeout_by_default() -> None:
    session = CredentialSessionStore().create(
        CredentialSessionRequest(provider=ProviderId.OPENAI, api_key="secret-api-key")
    )
    assert session.timeout_seconds == 180


def test_adapter_preserves_safe_request_rejection_metadata() -> None:
    session = CredentialSessionStore().create(
        CredentialSessionRequest(provider=ProviderId.OPENAI, api_key="secret-api-key")
    )

    def rejected_handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "potentially sensitive provider text",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": "model_not_supported",
                }
            },
        )

    provider = OpenAICompatibleProvider(
        session, transport=httpx.MockTransport(rejected_handler)
    )
    with pytest.raises(ProviderRequestError) as rejected_error:
        provider.generate_analysis(
            "AI Engineer requiring production Python experience.",
            "Candidate built production Python services for enterprise teams.",
            blind_review=True,
        )
    assert rejected_error.value.code == "PROVIDER_REQUEST_REJECTED"
    assert rejected_error.value.details == {
        "provider_status": 400,
        "provider_code": "model_not_supported",
        "provider_error_type": "invalid_request_error",
        "provider_parameter": "model",
    }
    assert "potentially sensitive" not in rejected_error.value.message


def test_adapter_repairs_paraphrased_evidence_with_verbatim_excerpt() -> None:
    job = "AI Engineer\nProduction Python experience is required."
    resume = "Candidate\nBuilt and deployed Python production services."
    valid = MockProvider().generate_analysis(job, resume, blind_review=False)
    invalid = valid.model_copy(deep=True)
    invalid.matches[0].evidence[0].text = "Deployed production services using Python."
    responses = iter((invalid, valid))
    prompts: list[str] = []

    def repair_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        prompts.append(body["messages"][1]["content"])
        analysis = next(responses)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": analysis.model_dump_json()}}]},
        )

    session = CredentialSessionStore().create(
        CredentialSessionRequest(provider=ProviderId.OPENAI, api_key="secret-api-key")
    )
    provider = OpenAICompatibleProvider(session, transport=httpx.MockTransport(repair_handler))
    repaired = provider.generate_analysis(job, resume, blind_review=False)

    assert repaired == valid
    assert len(prompts) == 2
    assert "contiguous verbatim excerpt" in prompts[1]


def test_adapter_conservatively_discards_evidence_that_remains_paraphrased() -> None:
    job = "AI Engineer\nProduction Python experience is required."
    resume = "Candidate\nBuilt and deployed Python production services."
    invalid = MockProvider().generate_analysis(job, resume, blind_review=False)
    invalid.matches[0].evidence[0].text = "Deployed production services using Python."

    def invalid_evidence_handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": invalid.model_dump_json()}}]},
        )

    session = CredentialSessionStore().create(
        CredentialSessionRequest(provider=ProviderId.OPENAI, api_key="secret-api-key")
    )
    provider = OpenAICompatibleProvider(
        session, transport=httpx.MockTransport(invalid_evidence_handler)
    )
    grounded = provider.generate_analysis(job, resume, blind_review=False)

    assert grounded.matches[0].match_type is MatchType.NO_EVIDENCE
    assert grounded.matches[0].match_strength == 0
    assert grounded.matches[0].evidence_strength == 0
    assert grounded.matches[0].evidence == []
    assert "Excluded 1 non-verbatim resume evidence statement(s)." in grounded.warnings


def test_adapter_extracts_source_grounded_job_requirements() -> None:
    job = "AI Engineer\nProduction Python experience is required."
    expected = MockProvider().generate_job_analysis(job)
    prompts: list[str] = []

    def job_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        prompts.append(body["messages"][1]["content"])
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": expected.model_dump_json()}}]},
        )

    session = CredentialSessionStore().create(
        CredentialSessionRequest(provider=ProviderId.OPENAI, api_key="secret-api-key")
    )
    provider = OpenAICompatibleProvider(session, transport=httpx.MockTransport(job_handler))
    result = provider.generate_job_analysis(job)

    assert result == expected
    assert "Do not return a candidate evaluation" in prompts[0]
