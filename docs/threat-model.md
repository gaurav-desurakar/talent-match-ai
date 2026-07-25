# Threat model

## Protected assets

- Candidate and job-description content.
- Candidate identity and contact data.
- Provider API keys and authentication metadata.
- Analysis integrity, source citations, scores, and audit records.
- Local host and provider accounts.

## Primary threats and controls

| Threat                                                 | Initial and planned controls                                                                                                                                                                                                                                                              |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Prompt injection in documents                          | Treat content as inert data; fixed delimiters; detect instruction-like phrases; validated structured output; never execute links, code, or commands.                                                                                                                                      |
| Secret disclosure                                      | Keys stay server-side; responses use boolean configuration state; structured log redaction; no raw headers; no plaintext database field.                                                                                                                                                  |
| Sensitive-data leakage                                 | No full-document logging; explicit provider/privacy confirmation; local mock default; retention and deletion controls.                                                                                                                                                                    |
| Malicious or oversized files                           | Extension and signature matching, streaming size limits, PDF page limits, DOCX entry/expansion/path checks, macro rejection, and no external URL fetching.                                                                                                                                |
| Batch resource exhaustion                              | Ten-megabyte per-file upload limit, bounded text/reference fields, sequential per-job candidate processing, bounded background workers, cooperative cancellation, and independent validated workflows. Shared deployments must add request, queue, rate, and provider-cost limits.          |
| Model hallucination                                    | Required source references, schema validation, quality review, visible uncertainty, failure rather than invented repair.                                                                                                                                                                  |
| Score manipulation                                     | Deterministic scoring, validated weights, mandatory separation, immutable configuration snapshot.                                                                                                                                                                                         |
| Bias or proxy discrimination                           | Protected requirements are excluded from scorecards, providers are instructed not to infer protected traits, deterministic scoring does not use protected traits, and optional blind review redacts direct identifiers and explicitly labelled protected fields before provider analysis. |
| Accusatory credibility output                          | Constrained labels and report validation; no fraud, fake, lying, or dishonest classifications.                                                                                                                                                                                            |
| Credential-session misuse                              | Expiring opaque session IDs, API-process memory, browser `sessionStorage`, provider/session matching, and explicit key removal. The session ID is not authentication; shared deployments require authenticated, user-bound server sessions.                                               |
| Server-side request abuse through compatible endpoints | User must explicitly configure the endpoint; URL schema validation; no URLs are read from documents. Shared deployments must add an outbound allowlist.                                                                                                                                   |
| Unauthorized local data access                         | Single-user trust boundary, local database permissions, deletion and retention controls; authentication and encryption at rest required before shared deployment.                                                                                                                         |

## Prompt-injection indicators

The API flags document phrases such as instructions to ignore rules, reveal prompts, alter scores, execute commands, or contact URLs. A flag is a diagnostic warning only. Content containing a flag remains data and is never followed.

## Known MVP limitations

- PDF text extraction does not perform OCR; scanned pages produce explicit warnings.
- DOCX tables are extracted after paragraphs, so exact interleaved layout order is not preserved.
- Background job state and credential sessions are process-local; restart loses active jobs and keys, while completed database records remain.
- Browser `sessionStorage` can retain a stale credential-session ID after an API restart or expiry; the user must save a new provider session.
- A saved retention period has no built-in scheduler; operators must invoke the retention endpoint on an appropriate schedule.
- Cancellation is cooperative between validated workflow nodes and candidates, not a hard interruption of an in-flight provider HTTP request.
- Candidate batches have no application-level count cap; shared deployments must enforce request-size, queue, provider rate, and cost limits appropriate to their capacity.
- External provider adapters require live account-specific contract testing before production use.
- Rich OCR and visual-layout interpretation are not implemented.
- Mock extraction is heuristic and must not be used for employment decisions.
- The local MVP has no authentication and is for a trusted single-user environment only.
