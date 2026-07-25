# Architecture

## Current design

TalentMatch AI is a TypeScript Next.js web application backed by a Python FastAPI service. The API owns transient document extraction, workflow orchestration, provider credentials, normalized analysis, deterministic scoring, persistence, and exports. The browser owns guided data entry and presentation; it never receives an unmasked provider secret.

```text
Browser (Next.js Jobs and Candidates workspaces)
  -> typed REST / SSE progress
FastAPI boundary
  -> bounded background-job manager
  -> explicit workflow state machine
     -> document ingestion
     -> provider abstraction -> mock or BYOK provider
     -> validated Pydantic outputs
     -> deterministic scoring
     -> quality review
  -> SQLAlchemy repositories -> SQLite/PostgreSQL
  -> generated exports -> response bytes
```

## Repository tree

```text
apps/
  api/
    app/{api,core,db,providers,schemas,scoring,services,workflows}/
    migrations/
    tests/
    pyproject.toml
  web/
    app/
    components/
    lib/
    types/
    package.json
docs/
examples/{job-descriptions,fictional-resumes}/
.github/workflows/
docker-compose.yml
Makefile
```

SQLAlchemy models cover settings, jobs, candidates, resume text versions, comparisons, requirement matches, recruiter dispositions, analysis runs, and audit events. Alembic owns schema upgrades. SQLite is the tested default; the SQLAlchemy boundary supports a PostgreSQL URL, though production PostgreSQL deployment remains an operator validation task. Original uploaded files are not stored.

## Trust boundaries

1. Browser input is untrusted and size-limited.
2. Uploaded documents are inert data inside explicit delimiters.
3. Provider responses are untrusted until schema validation succeeds.
4. Only normalized structured outputs cross into scoring.
5. Deterministic scoring cannot access provider credentials and does not use protected attributes as criteria or score factors.
6. API responses expose evidence excerpts but no internal prompts, chain-of-thought, secrets, or raw provider headers.

## Provider boundary

All providers implement credential validation, model listing, job-requirement generation, candidate-evidence generation, and health checking. HTTP adapters normalize retries, timeouts, rate limits, refusals, usage metadata, and structured-output validation. Provider-specific response types do not escape the adapter.

The mock provider follows the same structured contract and makes no network calls. It is intentionally heuristic, suitable for tests and product demonstration—not real hiring support.

## Workflow

The workflow is an explicit sequence of validated steps. Node outputs use Pydantic schemas. User-facing events describe phases and validated outcomes, never private reasoning. A provider result that cannot be validated or grounded fails visibly; the application does not invent a replacement result.

Uploads pass through bounded, format-specific parsers before normalized text reaches the workflow. The batch workflow runs one isolated comparison per candidate, processes candidates sequentially within a job, preserves input order, and never sorts candidates into an automatic ranking. The background manager runs bounded worker threads, persists completed results, exposes cancellation between validated nodes and candidates, and streams public progress events using SSE. It intentionally does not expose private reasoning. A production multi-process deployment should replace the in-memory job registry with a distributed queue and enforce deployment-appropriate request, queue, rate, and provider-cost limits.

## Data and retention

Uploaded bytes are parsed in memory and discarded. Saved jobs, resume text versions, completed analyses, evidence, and recruiter actions persist in the database for contextual history and exports. Raw candidate text is not written to application logs. Saving a retention period does not run cleanup automatically; the explicit retention endpoint or an operator scheduler performs deletion. Delete-all removes persisted application records. BYOK credentials remain in process memory with expiration and explicit removal; encrypted persistence requires a future operator-configured key-management service.

## Product boundaries

- Jobs is the primary analysis workflow: create the role, approve its scorecard, add candidates, review evidence, and record recruiter actions.
- Candidates is the reusable profile workflow: manage resume versions, compare against approved jobs, and review chronological role history.
- Dashboard provides aggregate and recent activity only.
- Comparison-history APIs remain available, but there is no standalone Analysis History page.
