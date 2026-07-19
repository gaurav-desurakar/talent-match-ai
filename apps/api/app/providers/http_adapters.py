import time
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.errors import ApiError
from app.core.text import is_verbatim_excerpt
from app.providers.base import LLMProvider
from app.providers.prompts import SYSTEM_PROMPT, analysis_prompt, job_analysis_prompt
from app.schemas.comparison import (
    MatchType,
    ProviderAnalysis,
    ProviderJobAnalysis,
    ProviderRequirementMatch,
    Requirement,
)
from app.schemas.document import DocumentSourceReference
from app.schemas.provider import ProviderId
from app.services.credential_store import CredentialSession


class ProviderRequestError(ApiError):
    pass


class HTTPProvider(LLMProvider):
    id = "external"
    known_models: tuple[str, ...] = ()

    def __init__(
        self,
        session: CredentialSession,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.session = session
        self.model = session.model
        self._transport = transport
        self.last_usage: dict[str, Any] = {}
        self.last_retry_count = 0

    def list_models(self) -> list[str]:
        return list(dict.fromkeys((self.model, *self.known_models)))

    def health_check(self) -> str:
        return "configured"

    def validate_credentials(self) -> bool:
        self._request("connection test", validate_only=True)
        return True

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
        del job_source_references, resume_source_references
        prompt = analysis_prompt(
            job_description_text,
            resume_text,
            blind_review,
            approved_requirements,
        )
        last_error: ValidationError | None = None
        last_analysis: ProviderAnalysis | None = None
        for repair_attempt in range(2):
            repair_prompt = prompt
            if repair_attempt:
                repair_prompt += (
                    "\nThe previous response was invalid. Return a complete, schema-valid JSON "
                    "object without Markdown. Copy requirement.text as a contiguous verbatim "
                    "excerpt from the job description and every evidence.text as a contiguous "
                    "verbatim excerpt from the resume. Use no_evidence with an empty evidence "
                    "list when the resume has no exact supporting excerpt."
                )
            raw = self._request(repair_prompt)
            try:
                analysis = ProviderAnalysis.model_validate_json(raw)
            except ValidationError as exc:
                last_error = exc
                continue
            last_analysis = analysis
            if self._evidence_issue_count(
                analysis, job_description_text, resume_text
            ) == 0 and self._matches_approved_scorecard(analysis, approved_requirements):
                return analysis
        if last_analysis is not None:
            if approved_requirements:
                return self._ground_to_approved_scorecard(
                    last_analysis, approved_requirements, resume_text
                )
            return self._discard_unverified_evidence(
                last_analysis, job_description_text, resume_text
            )
        raise ProviderRequestError(
            "PROVIDER_INVALID_STRUCTURED_OUTPUT",
            "The provider returned an invalid structured response after a repair retry.",
            502,
            {"validation_issue_count": last_error.error_count() if last_error else 0},
        )

    def generate_job_analysis(
        self,
        job_description_text: str,
        *,
        job_source_references: list[DocumentSourceReference] | None = None,
    ) -> ProviderJobAnalysis:
        del job_source_references
        prompt = job_analysis_prompt(job_description_text)
        last_error: ValidationError | None = None
        last_analysis: ProviderJobAnalysis | None = None
        for repair_attempt in range(2):
            repair_prompt = prompt
            if repair_attempt:
                repair_prompt += (
                    "\nThe previous response was invalid. Return schema-valid JSON and copy "
                    "every requirement.text as one contiguous verbatim excerpt from the job "
                    "description. Do not add inferred criteria."
                )
            raw = self._request(repair_prompt)
            try:
                analysis = ProviderJobAnalysis.model_validate_json(raw)
            except ValidationError as exc:
                last_error = exc
                continue
            last_analysis = analysis
            if all(
                is_verbatim_excerpt(item.text, job_description_text)
                for item in analysis.requirements
            ):
                return analysis
        if last_analysis is not None:
            grounded = [
                item
                for item in last_analysis.requirements
                if is_verbatim_excerpt(item.text, job_description_text)
            ]
            if grounded:
                return last_analysis.model_copy(
                    update={
                        "requirements": grounded,
                        "warnings": [
                            *last_analysis.warnings,
                            "Unverified extracted requirements were excluded.",
                        ],
                    }
                )
        raise ProviderRequestError(
            "PROVIDER_INVALID_JOB_ANALYSIS",
            "The provider did not return source-grounded job requirements.",
            502,
            {"validation_issue_count": last_error.error_count() if last_error else 0},
        )

    @staticmethod
    def _matches_approved_scorecard(
        analysis: ProviderAnalysis, approved_requirements: list[Requirement] | None
    ) -> bool:
        if not approved_requirements:
            return True
        expected = {item.id: item.model_dump(mode="json") for item in approved_requirements}
        actual = {
            item.requirement.id: item.requirement.model_dump(mode="json")
            for item in analysis.matches
        }
        return actual == expected

    @staticmethod
    def _ground_to_approved_scorecard(
        analysis: ProviderAnalysis,
        approved_requirements: list[Requirement],
        resume_text: str,
    ) -> ProviderAnalysis:
        """Conservatively align provider matches to the recruiter-approved criteria."""
        provided = {item.requirement.id: item for item in analysis.matches}
        grounded_matches: list[ProviderRequirementMatch] = []
        excluded_evidence = 0
        missing_matches = 0
        for requirement in approved_requirements:
            match = provided.get(requirement.id)
            if match is None:
                missing_matches += 1
                grounded_matches.append(
                    ProviderRequirementMatch(
                        requirement=requirement,
                        match_type=MatchType.NO_EVIDENCE,
                        match_strength=0.0,
                        evidence_strength=0.0,
                        evidence=[],
                        explanation=(
                            "The provider did not return a match for this approved requirement; "
                            "it was treated as an evidence gap."
                        ),
                        uncertainties=["Candidate evidence requires human review."],
                    )
                )
                continue
            evidence = [
                item
                for item in match.evidence
                if is_verbatim_excerpt(item.text, resume_text)
            ]
            excluded_evidence += len(match.evidence) - len(evidence)
            if not match.evidence and match.match_type is MatchType.NO_EVIDENCE:
                grounded_matches.append(match.model_copy(update={"requirement": requirement}))
                continue
            if not evidence:
                grounded_matches.append(
                    match.model_copy(
                        update={
                            "requirement": requirement,
                            "match_type": MatchType.NO_EVIDENCE,
                            "match_strength": 0.0,
                            "evidence_strength": 0.0,
                            "evidence": [],
                            "uncertainties": [
                                *match.uncertainties,
                                "Provider evidence could not be verified verbatim.",
                            ],
                        }
                    )
                )
                continue
            evidence_ratio = len(evidence) / len(match.evidence)
            grounded_matches.append(
                match.model_copy(
                    update={
                        "requirement": requirement,
                        "evidence": evidence,
                        "evidence_strength": min(
                            match.evidence_strength, evidence_ratio
                        ),
                    }
                )
            )
        warnings = list(analysis.warnings)
        if excluded_evidence:
            warnings.append(f"Excluded {excluded_evidence} unverified evidence statement(s).")
        if missing_matches:
            warnings.append(
                f"Treated {missing_matches} missing approved requirement match(es) as no evidence."
            )
        return analysis.model_copy(update={"matches": grounded_matches, "warnings": warnings})

    @staticmethod
    def _evidence_issue_count(
        analysis: ProviderAnalysis, job_description_text: str, resume_text: str
    ) -> int:
        issues = 0
        for match in analysis.matches:
            if not is_verbatim_excerpt(match.requirement.text, job_description_text):
                issues += 1
            issues += sum(
                not is_verbatim_excerpt(evidence.text, resume_text)
                for evidence in match.evidence
            )
        return issues

    @staticmethod
    def _discard_unverified_evidence(
        analysis: ProviderAnalysis, job_description_text: str, resume_text: str
    ) -> ProviderAnalysis:
        """Keep only source-grounded claims when the provider repair remains imperfect."""
        grounded_matches = []
        discarded_requirements = 0
        discarded_evidence = 0
        for match in analysis.matches:
            if not is_verbatim_excerpt(match.requirement.text, job_description_text):
                discarded_requirements += 1
                continue
            grounded_evidence = [
                evidence
                for evidence in match.evidence
                if is_verbatim_excerpt(evidence.text, resume_text)
            ]
            removed_from_match = len(match.evidence) - len(grounded_evidence)
            discarded_evidence += removed_from_match
            if removed_from_match == 0:
                grounded_matches.append(match)
                continue
            uncertainty = (
                "One or more provider-generated evidence statements could not be verified "
                "verbatim and were excluded."
            )
            uncertainties = [*match.uncertainties, uncertainty]
            if grounded_evidence:
                evidence_ratio = len(grounded_evidence) / len(match.evidence)
                grounded_matches.append(
                    match.model_copy(
                        update={
                            "evidence": grounded_evidence,
                            "evidence_strength": min(
                                match.evidence_strength, evidence_ratio
                            ),
                            "uncertainties": uncertainties,
                        }
                    )
                )
            else:
                grounded_matches.append(
                    match.model_copy(
                        update={
                            "match_type": MatchType.NO_EVIDENCE,
                            "match_strength": 0.0,
                            "evidence_strength": 0.0,
                            "evidence": [],
                            "uncertainties": uncertainties,
                        }
                    )
                )
        if not grounded_matches:
            raise ProviderRequestError(
                "PROVIDER_INVALID_REQUIREMENTS",
                "The provider did not return any requirements copied from the job description.",
                502,
                {"discarded_requirement_count": discarded_requirements},
            )
        warnings = list(analysis.warnings)
        if discarded_requirements:
            warnings.append(
                f"Excluded {discarded_requirements} unverified job requirement(s)."
            )
        if discarded_evidence:
            warnings.append(
                f"Excluded {discarded_evidence} non-verbatim resume evidence statement(s)."
            )
        return analysis.model_copy(
            update={"matches": grounded_matches, "warnings": warnings}
        )

    def _request(self, prompt: str, validate_only: bool = False) -> str:
        last_error: Exception | None = None
        for attempt in range(self.session.max_retries + 1):
            try:
                with httpx.Client(
                    timeout=self.session.timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = self._send(client, prompt, validate_only)
                if response.status_code in {401, 403}:
                    raise ProviderRequestError(
                        "PROVIDER_AUTHENTICATION_FAILED",
                        "The provider rejected the API key.",
                        401,
                    )
                if response.status_code == 429:
                    raise ProviderRequestError(
                        "PROVIDER_RATE_LIMITED",
                        "The provider rate limit was reached.",
                        429,
                    )
                if response.status_code in {400, 404, 413, 422}:
                    error_details = self._safe_error_details(response)
                    provider_code = error_details.get("provider_code")
                    if response.status_code == 404:
                        message = (
                            "The selected provider model or endpoint was not found. "
                            "Review the model in Provider settings."
                        )
                    elif response.status_code == 413:
                        message = "The provider rejected the analysis because it was too large."
                    else:
                        message = (
                            "The provider rejected the analysis request"
                            f" ({provider_code})."
                            if provider_code
                            else "The provider rejected the analysis request."
                        )
                    raise ProviderRequestError(
                        "PROVIDER_REQUEST_REJECTED",
                        message,
                        502,
                        error_details,
                    )
                response.raise_for_status()
                payload = response.json()
                self.last_retry_count = attempt
                self._capture_usage(payload)
                return "{}" if validate_only else self._extract_text(payload)
            except ProviderRequestError:
                raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < self.session.max_retries:
                    time.sleep(min(0.25 * (2**attempt), 1.0))
        code = (
            "PROVIDER_TIMEOUT"
            if isinstance(last_error, httpx.TimeoutException)
            else "PROVIDER_UNAVAILABLE"
        )
        raise ProviderRequestError(
            code,
            (
                "The provider timed out while generating the analysis. "
                "Save the provider session again to use the longer analysis timeout."
                if code == "PROVIDER_TIMEOUT"
                else "The provider service is temporarily unavailable."
            ),
            504 if code == "PROVIDER_TIMEOUT" else 502,
        ) from None

    @staticmethod
    def _safe_error_details(response: httpx.Response) -> dict[str, str | int]:
        """Return provider metadata without reflecting prompts, keys, or response text."""
        details: dict[str, str | int] = {"provider_status": response.status_code}
        try:
            payload = response.json()
        except ValueError:
            return details
        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            return details
        for source, target in (
            ("code", "provider_code"),
            ("type", "provider_error_type"),
            ("param", "provider_parameter"),
        ):
            value = error.get(source)
            if isinstance(value, (str, int)):
                details[target] = value
        return details

    def _send(self, client: httpx.Client, prompt: str, validate_only: bool) -> httpx.Response:
        raise NotImplementedError

    def _extract_text(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError

    def _capture_usage(self, payload: dict[str, Any]) -> None:
        usage = payload.get("usage") or payload.get("usageMetadata")
        if isinstance(usage, dict):
            self.last_usage = usage
        elif any(key in payload for key in ("prompt_eval_count", "eval_count")):
            self.last_usage = {
                key: payload[key] for key in ("prompt_eval_count", "eval_count") if key in payload
            }


class OpenAICompatibleProvider(HTTPProvider):
    id = ProviderId.OPENAI.value
    known_models: tuple[str, ...] = ("gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini")

    def _send(self, client: httpx.Client, prompt: str, validate_only: bool) -> httpx.Response:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        if validate_only:
            body["max_tokens"] = 1
        return client.post(
            f"{self.session.base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.session.api_key}"},
            json=body,
        )

    def _extract_text(self, payload: dict[str, Any]) -> str:
        try:
            message = payload["choices"][0]["message"]
            if message.get("refusal"):
                raise ProviderRequestError(
                    "PROVIDER_REFUSED",
                    "The provider declined to process the request.",
                    422,
                )
            return str(message["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderRequestError(
                "PROVIDER_INVALID_RESPONSE", "The provider response was incomplete.", 502
            ) from exc


class GroqProvider(OpenAICompatibleProvider):
    id = ProviderId.GROQ.value
    known_models = ("llama-3.3-70b-versatile", "openai/gpt-oss-20b")


class CompatibleProvider(OpenAICompatibleProvider):
    id = ProviderId.COMPATIBLE.value
    known_models = ()


class AnthropicProvider(HTTPProvider):
    id = ProviderId.ANTHROPIC.value
    known_models = ("claude-sonnet-4-5", "claude-haiku-4-5")

    def _send(self, client: httpx.Client, prompt: str, validate_only: bool) -> httpx.Response:
        return client.post(
            f"{self.session.base_url}/v1/messages",
            headers={
                "x-api-key": self.session.api_key or "",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1 if validate_only else 4096,
                "temperature": 0,
            },
        )

    def _extract_text(self, payload: dict[str, Any]) -> str:
        try:
            if payload.get("stop_reason") == "refusal":
                raise ProviderRequestError(
                    "PROVIDER_REFUSED",
                    "The provider declined to process the request.",
                    422,
                )
            return str(payload["content"][0]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderRequestError(
                "PROVIDER_INVALID_RESPONSE", "The provider response was incomplete.", 502
            ) from exc


class GoogleProvider(HTTPProvider):
    id = ProviderId.GOOGLE.value
    known_models = ("gemini-2.5-flash", "gemini-2.5-pro")

    def _send(self, client: httpx.Client, prompt: str, validate_only: bool) -> httpx.Response:
        return client.post(
            f"{self.session.base_url}/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.session.api_key or ""},
            json={
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": 1 if validate_only else 4096,
                    "responseMimeType": "application/json",
                },
            },
        )

    def _extract_text(self, payload: dict[str, Any]) -> str:
        try:
            if payload.get("promptFeedback", {}).get("blockReason"):
                raise ProviderRequestError(
                    "PROVIDER_REFUSED",
                    "The provider declined to process the request.",
                    422,
                )
            return str(payload["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderRequestError(
                "PROVIDER_INVALID_RESPONSE", "The provider response was incomplete.", 502
            ) from exc


class OllamaProvider(HTTPProvider):
    id = ProviderId.OLLAMA.value
    known_models = ("llama3.2", "qwen2.5")

    def _send(self, client: httpx.Client, prompt: str, validate_only: bool) -> httpx.Response:
        return client.post(
            f"{self.session.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0, "num_predict": 1 if validate_only else 4096},
            },
        )

    def _extract_text(self, payload: dict[str, Any]) -> str:
        try:
            return str(payload["message"]["content"])
        except (KeyError, TypeError) as exc:
            raise ProviderRequestError(
                "PROVIDER_INVALID_RESPONSE", "The provider response was incomplete.", 502
            ) from exc
