# Changelog

All notable changes will be documented here.

## Unreleased

- Removed the overlapping New Comparison and Analysis History pages in favour of contextual workflows in Jobs and Candidates.
- Added contextual selection and CSV/JSON export for up to five job or candidate analyses while retaining individual PDF reports.
- Added deterministic recruiter triage thresholds, non-binding suggestions, manual HR statuses, job-related disposition reasons, notes, ownership, and status history.
- Added an HR user guide and refreshed setup, workflow, API, architecture, scoring, privacy, security, and contributor documentation.
- Added a candidate-centred workspace with search, activity summaries, resume versions, saved-job reuse, evidence history, reports, deletion, and normalized-content duplicate prevention.
- Added company job IDs, title/ID search, created/last-activity sorting, and a compact list layout to Saved Jobs.
- Added a guided Jobs workflow from New Job through scorecard approval, one-to-five resume intake, and Find Talent results.
- Added in-place View evidence actions for current and historical candidates in the Jobs workspace.
- Added accessible expand and collapse controls for the four primary Jobs workspace sections.
- Added saved-job scorecard approval enforcement and automatic scorecard invalidation when a job description changes.
- Added recruiter-reviewed, versioned job scorecards with source-grounded requirement extraction.
- Linked approved scorecards to saved-job analysis without changing historical result snapshots.
- Added Jobs workspace controls for requirement inclusion, classification, category, and importance.
- Added architecture, scoring, privacy, threat-model, and milestone documentation.
- Added the initial paste-to-result comparison vertical slice with a local mock provider.
- Migrated Python dependency management, local commands, CI, and Docker builds from pip to uv with a committed lockfile.
- Added safe transient PDF, DOCX, and TXT uploads with source references, extraction review, fingerprint checks, and upload-to-comparison evidence preservation.
- Added multi-resume selection for up to five candidates, duplicate prevention, ordered batch comparisons, blind-review labels, and per-candidate evidence reports.
- Added SQLAlchemy persistence, Alembic migration, CRUD/history/dashboard APIs, retention, and complete data deletion.
- Added expiring in-memory BYOK sessions and normalized OpenAI, Anthropic, Gemini, Groq, compatible-endpoint, and Ollama adapters.
- Added background analysis jobs, SSE progress, cancellation, clarification flags, targeted interview questions, and quality checks.
- Added functional dashboard, jobs, candidates, provider, scoring, privacy, and documentation screens, with contextual analysis history in Jobs and Candidates.
- Added PDF, JSON, CSV, and interview-guide exports with evidence and fairness disclosures.
