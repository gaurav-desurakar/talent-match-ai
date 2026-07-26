# Potential feature roadmap

This document collects potential enhancements that contributors can propose, design, and implement for TalentMatch AI. It is a community backlog, not a commitment to deliver every item or an indication that an item has been approved.

Before starting substantial work:

1. Check existing issues and pull requests for related work.
2. Open an issue describing the user problem, proposed scope, security and privacy implications, and intended tests.
3. Agree on the approach with maintainers before changing schemas, scoring, provider behavior, or product boundaries.
4. Follow the [contribution guide](../CONTRIBUTING.md) and update this roadmap when an accepted feature is completed.

## Product guardrails

Proposed features must preserve the core product boundaries:

- The product provides decision support and does not make hiring or rejection decisions.
- Candidate results must not be automatically ranked.
- Protected or inferred demographic characteristics must not influence criteria or scoring.
- Material assessments must remain traceable to source evidence.
- Missing resume evidence must not be presented as proof that a candidate lacks a capability.
- Recruiters must retain control of candidate statuses and next actions.
- Candidate information, provider credentials, and exports must receive appropriate privacy and security protections.

Features involving automatic ranking or rejection, personality inference, facial analysis, emotion detection, or protected-characteristic scoring are out of scope.

## Foundation and enterprise readiness

- [ ] Add authentication and role-based access for recruiters, hiring managers, reviewers, and administrators.
- [ ] Add SSO through Microsoft Entra ID, Google Workspace, Okta, and generic OIDC or SAML.
- [ ] Add team, department, and job-level access controls.
- [ ] Validate production PostgreSQL deployments, connection pooling, backups, and migrations.
- [ ] Replace the process-local background queue with durable distributed workers.
- [ ] Add configurable batch-size, request-size, concurrency, provider-rate, and cost limits.
- [ ] Add scheduled retention-policy execution.
- [ ] Add encryption at rest and integrations with external key-management services.
- [ ] Add secure object-storage adapters when retaining original files is explicitly enabled.
- [ ] Add backup, restore, and disaster-recovery tooling and documentation.

## Recruiting workflow

- [ ] Add collaborative scorecard review with comments, required approvers, and approval history.
- [ ] Add reusable scorecard templates by role family, department, seniority, or location.
- [ ] Show differences between scorecard versions and their approvers.
- [ ] Review job descriptions for ambiguous, unnecessary, discriminatory, or non-job-related requirements.
- [ ] Add recruiter-controlled candidate tags and talent pools.
- [ ] Add bulk candidate management with validation, progress, partial failure, and retry.
- [ ] Add assignments, mentions, comments, and pending-review queues.
- [ ] Support organisation-specific hiring stages and permitted status transitions.
- [ ] Add structured interview kits, interviewer assignments, feedback, and debriefs.
- [ ] Add side-by-side evidence comparison without creating an automatic ranking.
- [ ] Add email, Slack, or Teams notifications for completed analyses and review requests.

## Integrations and APIs

- [ ] Integrate with approved applicant tracking systems such as Workday, Greenhouse, Lever, and Ashby.
- [ ] Import jobs and candidates while preserving source-system identifiers.
- [ ] Return only recruiter-approved statuses and actions to connected systems.
- [ ] Add webhooks for recruiter-controlled events and completed background work.
- [ ] Publish a versioned integration API and client SDKs.
- [ ] Import approved documents from enterprise cloud-storage providers.

## Document processing

- [ ] Add OCR for scanned or image-only resumes with page-level confidence.
- [ ] Improve layout understanding for columns, tables, headings, and timelines.
- [ ] Support additional approved formats such as RTF, ODT, and HTML.
- [ ] Add language detection and multilingual resume and job-description processing.
- [ ] Preserve original-language evidence when controlled translation is used.
- [ ] Detect near-duplicate resumes in addition to exact normalized duplicates.
- [ ] Compare resume versions and show changed claims, roles, and dates.
- [ ] Add configurable redaction and anonymisation before provider transmission.

## Assessment quality and explainability

- [ ] Add a provider evaluation suite for grounding, schema validity, latency, and cost.
- [ ] Add organisation-specific score calibration using reviewed, appropriate evaluation data.
- [ ] Add requirement-coverage dashboards for strong, partial, conflicting, and missing evidence.
- [ ] Detect inconsistent dates, titles, durations, and claims for recruiter clarification.
- [ ] Support deterministic scoring policies by job family while retaining version history.
- [ ] Assess recruiter-defined work samples separately from resume evidence.
- [ ] Show score contributions, calculation details, evidence provenance, and policy versions more clearly.
- [ ] Add per-candidate retry with another approved provider without rerunning the whole batch.
- [ ] Add regression evaluations for prompts, schemas, models, and scoring changes.

## Governance, privacy, and compliance

- [ ] Expand the audit log for access, scorecard changes, analyses, exports, actions, and deletion.
- [ ] Add workflows for candidate data access, correction, export, and deletion requests.
- [ ] Record organisation-controlled processing notices, lawful basis, and consent where required.
- [ ] Add data-residency controls for storage and provider processing.
- [ ] Let administrators approve providers, models, and transmission destinations.
- [ ] Record the prompt, schema, model, scorecard, and policy versions used for every assessment.
- [ ] Add aggregate process-quality and review-consistency monitoring without using protected traits in candidate scoring.
- [ ] Add export permissions, auditing, watermarks, expiration, and configurable limits.
- [ ] Add configurable legal holds that are separate from ordinary retention behavior.

## Platform and operations

- [ ] Add an administrative dashboard for queue health, provider status, failures, storage, and retention runs.
- [ ] Estimate provider cost before analysis and report actual usage by team, job, and model.
- [ ] Add OpenTelemetry traces, privacy-safe metrics, structured diagnostics, and alerts.
- [ ] Add Kubernetes Helm charts and infrastructure templates for supported deployments.
- [ ] Add deployment health checks and automated migration readiness checks.
- [ ] Add internationalisation for the user interface.
- [ ] Extend automated accessibility testing and continue WCAG-focused review.

## Suggested delivery order

A strong next milestone would establish authentication and role-based access, PostgreSQL validation, durable background processing, configurable operational limits, and scheduled retention. These capabilities provide a safer multi-user foundation for later ATS integrations, collaboration, and advanced assessment features.

Priorities may change based on contributor interest, user evidence, security review, and maintainer capacity.
