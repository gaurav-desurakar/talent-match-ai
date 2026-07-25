# API

FastAPI generates interactive OpenAPI documentation at `/docs` and a machine-readable schema at `/openapi.json`.

The local API has no authentication. Bind it only to a trusted environment unless an authenticated gateway and the controls described in [SECURITY.md](../SECURITY.md) are added.

## Current endpoints

- `GET /api/health` — process health.
- `GET /api/providers` — safe provider metadata with no credentials.
- `POST /api/comparisons` — run the synchronous first-slice comparison.
- `POST /api/comparisons/batch` — compare an ordered candidate batch against one job description.
- `POST /api/job-descriptions/upload` — validate and transiently extract a PDF, DOCX, or TXT job description.
- `POST /api/resumes/upload` — validate and transiently extract a PDF, DOCX, or TXT resume.
- `POST /api/analysis-jobs` — start a process-local background comparison workflow whose completed records are persisted.
- `GET /api/analysis-jobs/{id}` — get validated status and comparison IDs.
- `GET /api/analysis-jobs/{id}/events` — stream progress using SSE.
- `DELETE /api/analysis-jobs/{id}` — request cancellation.
- `POST /api/analysis-jobs/retry/{comparison_id}` — rerun persisted inputs with another configured provider/model.
- `POST/GET/PUT/DELETE /api/jobs...` — create, list, retrieve, update, and delete saved jobs.
- `GET /api/jobs/{id}/overview` — job summary plus its chronological comparison history.
- `GET /api/jobs/{id}/scorecard` — current draft or reviewed job scorecard.
- `POST /api/jobs/{id}/scorecard/extract` — source-grounded requirement extraction.
- `PUT /api/jobs/{id}/scorecard` — save or approve recruiter-reviewed requirements.
- `GET/PUT /api/jobs/{id}/triage-policy` — retrieve or version deterministic, job-specific triage thresholds.
- `POST/GET/DELETE /api/candidates...` — create, list, retrieve, and delete saved candidates with pagination and activity summaries.
- `GET /api/candidates/{candidate_id}/overview` — candidate profile, resume versions, and chronological comparison history.
- `POST /api/candidates/{candidate_id}/resumes` — add a non-duplicate resume version to a saved candidate.
- `GET/DELETE /api/comparisons...` — comparison history, result retrieval, and deletion.
- `GET/PUT /api/comparisons/{id}/disposition` — retrieve or record recruiter-controlled HR status, job-related reason, note, owner, and audit timeline.
- `GET/PUT /api/settings` — retention, provider metadata, scoring weights, global triage defaults, and taxonomy.
- `POST/DELETE /api/providers/session...` — create/remove expiring credential sessions.
- `POST /api/providers/validate` — connection test without candidate documents.
- `GET /api/providers/{provider_id}/models` — configured default model name for a supported provider.
- `GET/PUT /api/scoring-config` — compatibility access to the persisted scoring configuration.
- `POST /api/export/{report|json|csv|interview-guide}` — safe persisted exports.
- `DELETE /api/privacy/all-data` — delete all persisted application data.
- `POST /api/privacy/retention/run` — apply the configured retention policy.
- `GET /api/diagnostics` — non-sensitive counts and runtime state when explicitly enabled.

## Comparison behavior

`POST /api/comparisons` accepts job-description text, resume text, provider selection, blind-review state, and optional scoring weights. External providers require a matching `credential_session_id`. Invalid requests use the standard error envelope with a code, safe message, details, and request ID. Document text is never echoed in validation errors.

`POST /api/comparisons/batch` accepts shared job-description text and a non-empty ordered `candidates` list. Each candidate has a unique caller-defined ID, display name, resume text, and optional source references. The response preserves the submitted order and contains an independent evidence report for every candidate; it does not create a ranking. Blind review replaces display names with neutral `Candidate N` labels.

Upload responses include normalized text, sections, source references, a SHA-256 fingerprint, extraction confidence, and warnings. The original file bytes are discarded after the request. Comparison requests may include the returned references; the API rejects reference lists that do not exactly match the submitted text.

The synchronous comparison endpoints remain supported for API diagnostics and integrations. The browser uses background analysis jobs so provider work does not block the initiating request and completed results are persisted for contextual history and exports.

`POST /api/analysis-jobs` accepts an optional `job_id`. When supplied, the submitted job text must exactly match the persisted job description, the saved scorecard must be approved, and completed comparisons are linked to that existing job. An unapproved scorecard returns `JOB_SCORECARD_NOT_APPROVED` with HTTP 409.

Saved-job background analysis uses only included requirements from the reviewed scorecard. Provider output is aligned to the approved requirement identifiers and exact text; missing or unverifiable matches receive zero evidence rather than inferred candidate information. Each result records the scorecard version used. Updating the saved job-description text clears its requirements, creates the next draft scorecard version, and requires regeneration and approval before another saved-job analysis.

Recruiter triage is deterministic application logic, not provider output. The active job policy evaluates fit score, evidence confidence, mandatory status, and clarification flags to produce a non-binding suggestion. Recruiter dispositions are separate manual records. The API never converts a suggestion into an automatic shortlist or rejection, and each saved action retains the policy version and suggestion snapshot used at that time.

## Export constraints

- PDF report export requires exactly one comparison ID.
- CSV and JSON exports accept one to five comparison IDs.
- Interview-guide export accepts one comparison ID, up to 100 selected generated-question IDs, and up to 50 custom questions.
- Exports load persisted, schema-validated comparison results; unknown IDs return a safe not-found error.

## Retention

Updating `retention_policy_days` stores a policy value only. `POST /api/privacy/retention/run` applies that policy when called: it deletes comparisons older than the cutoff and removes job and candidate records with no remaining comparisons. The MVP does not include a scheduler.
