# Scoring methodology

## Principles

The language model does not choose the final score. It may extract requirements and classify evidence into a schema; application code then validates weights, maps match types to fixed values, calculates category totals, and handles mandatory requirements.

The score represents resume-to-job evidence alignment. It is neither a hiring recommendation nor proof that a candidate has or lacks a capability.

## Default category weights

| Category                            | Points |
| ----------------------------------- | -----: |
| Core technical skills               |     20 |
| Responsibility alignment            |     18 |
| Relevant experience                 |     15 |
| Project similarity                  |     10 |
| Seniority and ownership             |     10 |
| Measurable achievements             |     10 |
| Domain experience                   |      6 |
| Stakeholder and customer experience |      5 |
| Education and certifications        |      3 |
| Career progression                  |      3 |

Weights must be non-negative and total exactly 100.

## Requirement score

Each structured requirement has provider-supplied `match_strength` and `evidence_strength` values between zero and one. The deterministic application formula is:

```text
requirement score = match strength × evidence strength × 100
```

The requirement's recruiter-reviewed importance does not change this individual score; it controls that requirement's contribution to its category. Repeated keywords do not create additional requirements or additional credit.

For saved jobs with a recruiter-reviewed scorecard, the included scorecard requirements are the authoritative scoring criteria. Providers cannot add criteria, change classifications, or omit a requirement for scoring credit. Missing or unverifiable evidence is deterministically scored as no evidence. Historical results retain the scorecard version used when they were created.

## Category and overall score

The category score is the importance-weighted mean of its requirements. The overall fit score is the weighted mean of categories that contain extracted requirements. Active weights are normalized to 100 for incomplete job descriptions; the result explicitly lists which categories were assessed.

## Mandatory requirements

Mandatory status is calculated independently as met, partially met, not met, unclear, or not applicable. A high fit score never hides an unresolved mandatory concern.

## Evidence confidence

Evidence confidence measures source linkage, not truthfulness. The current deterministic calculation gives up to 70 points based on the proportion of requirements with at least one evidence excerpt and adds source-reference coverage worth 10 points per referenced excerpt per requirement, capped at 100.

This remains a preliminary confidence score. It does not verify that a resume claim is true, and it must not be described as a credibility, honesty, or fraud score. A richer evidence-quality model requires calibration against representative fictional evaluation sets before adoption.

## Triage thresholds and recruiter actions

The fit score, evidence-confidence score, mandatory status, and clarification flags feed a deterministic job-specific triage suggestion. The default shortlist thresholds are fit 80 and evidence confidence 80, with mandatory requirements met and no clarification flags required. Global defaults are copied into newly created jobs; changing them does not rewrite existing job policies.

The suggestion is non-binding. It never changes HR status. A recruiter must review the evidence and explicitly save any Shortlisted, Needs clarification, On hold, Not progressing, or later workflow status.
