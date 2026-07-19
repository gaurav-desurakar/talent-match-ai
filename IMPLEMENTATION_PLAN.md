# TalentMatch AI implementation plan

## Delivery principles

- Ship working vertical slices instead of disconnected placeholders.
- Keep extraction and semantic classification behind a provider boundary.
- Keep score calculation, mandatory handling, and recommendation mapping in deterministic code.
- Treat resumes and job descriptions as untrusted data, never as model instructions.
- Store no user-supplied API key in the database in the default local mode.
- Never use protected or inferred demographic attributes as requirements or scoring factors.

## Assumptions

1. The first release is a single-user, self-hosted application with no authentication boundary.
2. The mock provider is the default and makes no network calls.
3. Real provider keys will be held in an expiring server-side session store; encrypted persistence is deferred until a deployment supplies a key-management service.
4. SQLite is the development database default. Uploaded bytes remain transient; PostgreSQL validation and optional object storage for original files are later work.
5. A missing resume statement means "no evidence found," not that the candidate lacks the capability.

## Milestones

### M1 — Paste-to-result vertical slice

Status: complete.

- FastAPI service with typed schemas and a deterministic mock provider.
- Explicit comparison workflow with safe document boundaries.
- Deterministic, configurable scoring and mandatory-status calculation.
- Next.js HR interface for pasted job descriptions and resumes.
- Requirement-to-evidence result matrix and fairness disclaimer.
- Unit/API tests, Docker Compose, and CI.

### M2 — Safe document ingestion and persistence

Status: complete for the local MVP.

Completed ingestion vertical slice:

- PDF, DOCX, and TXT validation and transient extraction.
- Page, paragraph, table-row, and line source references with quality warnings.
- Upload-to-comparison evidence-reference preservation.
- Same-file fingerprint detection within a comparison.

Completed persistence sub-milestone:

- SQLAlchemy models, Alembic migrations, SQLite repositories, and retention jobs.
- Durable normalized document storage and duplicate fingerprints; original uploaded bytes remain transient by design.

### M3 — BYOK provider layer

Status: complete for the local MVP.

- In-memory session credentials, key masking/removal, and connection testing.
- OpenAI, Anthropic, Gemini, Groq, compatible-endpoint, and Ollama adapters.
- Normalized structured output, timeout, retry, usage, cost, refusal, and rate-limit handling.
- Credential and secret-redaction tests.

### M4 — Full observable workflow

Status: complete for the local MVP.

- Job and resume analysis, skill normalization, evidence matching, clarification review, interview questions, and quality review nodes.
- Background-job abstraction, cancellation, retry with another provider, and SSE progress.
- Versioned prompts and structured node outputs.

### M5 — Complete HR experience

Status: complete for the local MVP.

Completed MVP experience:

- Guided document, candidate, scoring, provider, and privacy review sections.
- Candidate evidence results, contextual history, jobs, candidates, and settings.
- Editable taxonomy and scoring weights.
- Dashboard metrics backed by persisted records.
- Dashboard-first navigation with direct New Job and Candidates actions.
- A single job-centred analysis entry path; the overlapping New Comparison page has been removed.
- Persisted analyses remain available from their Job and Candidate workspaces; the redundant standalone Analysis History page has been removed.
- Jobs and Candidates provide contextual CSV/JSON export for up to five explicitly selected analyses, while each analysis retains its PDF report.

Completed comparison sub-milestone:

- Select and transiently extract up to five resumes in one upload action.
- Edit candidate labels and extracted text before analysis.
- Reject duplicate resume fingerprints and job/resume collisions.
- Compare candidates in input order with no automatic ranking.
- Review a batch summary and open each candidate's evidence report.
- Apply neutral labels consistently when blind-review display is enabled.

Completed saved-jobs workspace foundation:

- Search persisted jobs and open a recruiter-focused job detail workspace.
- Show candidate and comparison counts, last-analysis activity, and linked results.
- Reuse a saved job when comparing more candidates without creating duplicate job records.
- Update a job title, export linked reports, and delete a job through explicit confirmation.
- Keep comparisons chronological and avoid automatic candidate ranking.

Completed reviewed-scorecard vertical slice:

- Extract source-grounded job requirements independently of candidate resumes.
- Let recruiters include, exclude, classify, categorize, weight, save, and approve criteria.
- Exclude protected-characteristic requirements before they can reach scoring.
- Version reviewed scorecards and retain the version snapshot on comparison results.
- Constrain saved-job comparisons to the included recruiter-approved requirements.
- Treat missing or unverifiable provider matches as evidence gaps instead of fabricating data.

Completed job-centred hiring workflow:

- Create a saved job from a title and pasted job description without starting candidate analysis.
- Guide recruiters through job setup, scorecard generation, approval, resume intake, and results.
- Edit saved job descriptions and invalidate prior approval when assessment criteria may have changed.
- Upload or paste one to five resumes and run Find Talent without leaving the job workspace.
- Require an approved scorecard at both the UI and API boundaries for saved-job analysis.
- Show completed candidate summaries in upload order and append them to the job history.
- Open persisted candidate evidence from the job history using the shared detailed evidence report.
- Collapse and expand job details, requirements and scoring, talent intake, and candidate analyses without losing form state.

Completed candidate-centred workspace:

- Search, filter, and sort a compact saved-candidate list using activity summaries.
- Open a candidate workspace with resume-version, role, and comparison counts.
- Upload and retain new resume versions while rejecting duplicate normalized content.
- Reuse a selected saved resume against any recruiter-approved job scorecard.
- Preserve candidate identity across repeated analyses instead of creating duplicate records.
- Review chronological role history, evidence, gaps, interview questions, and PDF reports.
- Delete candidate data, resume versions, and linked comparisons through explicit confirmation while retaining jobs.

Completed recruiter next-action workflow:

- Configure global triage defaults and versioned per-job fit/evidence thresholds.
- Calculate provider-independent triage suggestions from persisted scores, mandatory status, and clarification flags.
- Keep triage suggestions separate from recruiter-controlled HR statuses; never shortlist or reject automatically.
- Record job-related Not progressing reasons, recruiter notes, ownership, timestamps, and immutable status history.
- Filter job analyses by HR status and show status/suggestion badges in job and candidate workspaces.
- Snapshot the active triage policy with every recruiter action for later review.

### M6 — Security, fairness, exports, and release readiness

Status: complete for the local MVP.

- Blind review, prompt-injection defenses, deletion workflows, audit events, and diagnostics controls.
- PDF, JSON, CSV, and interview-guide export.
- Accessible semantics, keyboard interaction, and frontend interaction coverage.
- Release documentation, HR operating guidance, examples, templates, and deployment limitations.

## Remaining post-MVP enhancements

- Authentication and authorization for shared or internet-facing deployments.
- PostgreSQL deployment testing and object-storage adapters for original files.
- Scheduled retention execution; the MVP exposes an explicit retention-run endpoint.
- Live contract tests against provider accounts, which require operator-owned credentials.
- Rich side-by-side PDF/DOCX document highlighting and OCR for scanned PDFs.
- Distributed job queues and cross-process SSE state for horizontally scaled deployments.
- Browser-driven Playwright coverage in CI; current frontend interaction tests run in jsdom.
- Encrypted opt-in persistent key storage backed by an operator-managed KMS.
- Historical job-description snapshots and job-specific scoring overrides.
- Job interview kits, job archive workflows, templates, and evidence-coverage matrices.
- Recruiter-reviewed merging for ambiguous candidate duplicates created before content fingerprints were introduced.

## Definition of done per milestone

Code, tests, lint/type checks, threat-model changes, user documentation, and a list of remaining limitations must be updated together. A milestone is not complete with broken checks.
