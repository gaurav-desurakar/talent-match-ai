# Product requirements

## Product statement

TalentMatch AI is evidence-based decision support for recruiters. It compares job requirements with resume claims, calculates an explainable fit score, highlights uncertainty, and creates targeted interview questions. It never makes a hiring or rejection decision.

## Primary workflow

1. Create a saved job from its title, company job ID, and job description.
2. Generate, review, and approve the role scorecard.
3. Configure the provider and scoring defaults when the organisation needs values other than the local defaults.
4. Add resumes from the job workspace or reuse a saved candidate from the Candidates workspace.
5. Explicitly approve document transmission and start analysis.
6. Follow concise workflow progress.
7. Review scores, mandatory status, evidence, gaps, clarification flags, and interview questions.
8. Record a recruiter-controlled next action and, when needed, export selected records.

## Product constraints

- Important conclusions require source evidence.
- Fit and evidence-confidence are separate scores.
- Mandatory requirements are separate from the numerical score.
- Missing information is not treated as proof of absence.
- Protected characteristics cannot be approved as job criteria or used by deterministic scoring; providers are instructed not to infer them.
- Candidate claims are never described as fraudulent or dishonest.
- Uploaded content is data, never an instruction source.
- Provider keys are never returned, logged, or stored in plaintext.
- Triage suggestions never change recruiter-controlled HR status automatically.
- Results remain in submission or chronological order and are not an automatic ranking.

## MVP scope

The MVP includes local single-user operation, pasted job descriptions, pasted or uploaded resumes, a provider abstraction with mock and supported BYOK adapters, an observable structured workflow, deterministic scoring, evidence mapping, blind review, comparison, exports, SQLite, Docker Compose, tests, and public-release documentation.

ATS integrations, billing, SSO, automated rejection, scraping, personality inference, facial analysis, emotion detection, and video-interview analysis are out of scope.

## Completed vertical slices

The local MVP supports a job-centred hiring workflow, safe transient PDF/DOCX/TXT extraction, and multi-candidate analysis. It includes the deterministic mock plus configurable external providers, schema-validated analysis, deterministic scoring, background progress, persisted analysis records, recruiter dispositions, deletion, and contextual exports. Candidate summaries preserve input order and intentionally avoid automatic ranking. The standalone New Comparison and Analysis History pages were removed because Jobs and Candidates provide analysis, evidence review, and export capability with the relevant saved-job or candidate context. Comparison history APIs remain available for future reporting and audit workflows.

## Success measures

- Recruiters can trace each scored requirement to resume evidence.
- Scoring results are repeatable for the same structured inputs and weights.
- Users understand mandatory concerns and uncertainty without interpreting the score as a decision.
- No secret is logged, and no protected attribute influences deterministic scoring.
