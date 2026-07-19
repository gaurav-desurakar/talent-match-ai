# Provider integration

Providers implement a normalized interface for credential validation, model listing, source-grounded job-requirement generation, structured candidate-evidence generation, and health checking. The application workflow depends on this interface and validated schemas, never on provider SDK response types.

The `MockProvider` is deterministic, local, keyless, and network-free. It exists for development and tests. It does not claim semantic equivalence beyond its small versioned taxonomy.

Implemented adapters cover OpenAI, Anthropic, Google Gemini, Groq, OpenAI-compatible chat-completions endpoints, and Ollama. They normalize authentication failures, timeouts, bounded retries, rate limits, refusals, incomplete responses, token-usage metadata, and Pydantic structured-output validation. One bounded repair request is allowed. Schema-invalid output after that fails the workflow; unverifiable evidence is discarded or converted to an explicit evidence gap instead of being invented. Estimated cost remains null when a provider does not supply reliable pricing metadata.

`POST /api/providers/session` places a submitted key in a locked, expiring process-memory store and returns an opaque session ID plus a mask. For OpenAI, Anthropic, Google, and Groq, the endpoint can use the corresponding server environment variable when the request does not contain a key. The key is excluded from responses, database models, audit events, exceptions, and logs. `POST /api/providers/validate` performs provider credential/model validation without sending candidate documents. `DELETE /api/providers/session/{id}` removes the in-memory session immediately.

External analysis requires the selected provider and credential session to match. The browser stores the opaque session ID in `sessionStorage`, shows whether documents leave the environment, and requires explicit approval before submitting them. API restarts, session expiry, explicit key removal, or stale browser state require the user to save a new Provider settings session. Ollama and the mock provider are marked local. Compatible endpoints are operator-supplied and must use an explicit HTTP or HTTPS URL.

Provider model names and remote APIs evolve. The listed defaults are editable, and live provider compatibility must be tested with the operator's account before processing personal data.
