export type MatchType =
  "exact" | "equivalent" | "transferable" | "adjacent" | "no_evidence";

export interface DocumentSourceReference {
  id: string;
  text: string;
  location_type: "line" | "paragraph" | "table_row";
  page: number | null;
  paragraph: number | null;
  line: number | null;
  table: number | null;
  row: number | null;
}

export interface DocumentExtraction {
  document_id: string;
  document_type: "resume" | "job_description";
  filename: string;
  media_type: string;
  sha256: string;
  raw_text: string;
  sections: Array<{
    title: string;
    text: string;
    source_reference_ids: string[];
  }>;
  source_references: DocumentSourceReference[];
  warnings: string[];
  extraction_confidence: number;
  character_count: number;
}

export interface SourceEvidence {
  text: string;
  source_reference: string;
  section: string;
}

export interface RequirementMatch {
  requirement: {
    id: string;
    text: string;
    canonical_concept: string | null;
    classification: string;
    category: string;
    importance: number;
    source_reference: string;
  };
  match_type: MatchType;
  score: number;
  confidence: number;
  evidence: SourceEvidence[];
  explanation: string;
  uncertainties: string[];
  clarification_required: boolean;
}

export interface ComparisonResult {
  comparison_id: string;
  status: string;
  provider: string;
  model: string;
  scorecard_version: number | null;
  job_title: string;
  candidate_display_name: string;
  fit_score: number;
  evidence_confidence_score: number;
  mandatory_status: string;
  recommendation: string;
  score_breakdown: Array<{
    category: string;
    weight: number;
    score: number;
    evidence_count: number;
    explanation: string;
  }>;
  requirement_matches: RequirementMatch[];
  workflow_events: Array<{
    sequence: number;
    node: string;
    label: string;
    status: string;
  }>;
  clarification_flags: Array<{
    id: string;
    status: string;
    title: string;
    explanation: string;
    source_references: string[];
  }>;
  interview_questions: Array<{
    id: string;
    category: string;
    question: string;
    rationale: string;
    source_requirement_id: string | null;
    selected: boolean;
  }>;
  quality_checks: string[];
  warnings: string[];
  methodology_note: string;
  disclaimer: string;
}

export interface BatchCandidateResult {
  candidate_id: string;
  display_name: string;
  comparison: ComparisonResult;
}

export interface BatchComparisonResult {
  batch_id: string;
  status: string;
  candidate_count: number;
  comparisons: BatchCandidateResult[];
}

export interface ProviderSession {
  session_id: string;
  provider: string;
  model: string;
  base_url: string;
  masked_key: string | null;
  expires_at: string;
  storage_mode: string;
  sends_documents_externally: boolean;
}

export interface AnalysisJob {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  candidate_count: number;
  completed_count: number;
  comparison_ids: string[];
  events_url: string;
  latest_event: {
    sequence: number;
    timestamp: string;
    node: string;
    label: string;
    status: string;
    candidate_id: string | null;
  } | null;
  error: { code: string; message: string } | null;
  created_at: string;
  completed_at: string | null;
}

export interface ComparisonHistoryItem {
  id: string;
  job_description_id: string;
  candidate_id: string;
  job_title: string;
  candidate_display_name: string;
  provider: string;
  model: string;
  scorecard_version: number | null;
  status: string;
  fit_score: number | null;
  evidence_confidence_score: number | null;
  mandatory_status: string | null;
  recommendation: string | null;
  recruiter_status: RecruiterStatus;
  triage_suggestion: TriageSuggestion;
  disposition_updated_at: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface DashboardData {
  total_comparisons: number;
  active_jobs: number;
  candidates_analyzed: number;
  average_fit_score: number;
  requiring_clarification: number;
  provider_status: string;
  retention_days: number;
  recent_comparisons: ComparisonHistoryItem[];
}

export interface StoredJob {
  id: string;
  title: string;
  external_job_id: string | null;
  raw_text: string;
  parsed_content: Record<string, unknown>;
  requirements: Array<Record<string, unknown>>;
  source_file: string | null;
  triage_policy: TriagePolicy;
  triage_policy_version: number;
  comparison_count: number;
  candidate_count: number;
  last_analysis_at: string | null;
  scorecard_status: "empty" | "draft" | "reviewed";
  scorecard_version: number;
  scorecard_requirement_count: number;
  created_at: string;
  updated_at: string;
}

export interface JobOverview {
  job: StoredJob;
  comparisons: ComparisonHistoryItem[];
}

export type RequirementClassification =
  | "mandatory"
  | "strongly_preferred"
  | "preferred"
  | "contextual"
  | "informational";

export type ScoreCategory =
  | "core_technical_skills"
  | "responsibility_alignment"
  | "relevant_experience"
  | "project_similarity"
  | "seniority_and_ownership"
  | "measurable_achievements"
  | "domain_experience"
  | "stakeholder_and_customer_experience"
  | "education_and_certifications"
  | "career_progression";

export interface JobScorecardRequirement {
  id: string;
  text: string;
  canonical_concept: string | null;
  classification: RequirementClassification;
  category: ScoreCategory;
  importance: number;
  source_reference: string;
  included: boolean;
}

export interface JobScorecard {
  job_id: string;
  status: "empty" | "draft" | "reviewed";
  version: number;
  reviewed_at: string | null;
  requirements: JobScorecardRequirement[];
  warnings: string[];
}

export interface StoredCandidate {
  id: string;
  display_name: string;
  anonymized_name: string;
  resume_count: number;
  comparison_count: number;
  job_count: number;
  latest_resume_at: string | null;
  last_analysis_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResumeVersion {
  id: string;
  candidate_id: string;
  raw_text: string;
  parsed_content: Record<string, unknown>;
  source_file: string | null;
  sha256: string | null;
  extraction_warnings: string[];
  created_at: string;
}

export interface CandidateRecord {
  id: string;
  display_name: string;
  anonymized_name: string;
  metadata: Record<string, unknown>;
  resumes: ResumeVersion[];
  created_at: string;
  updated_at: string;
}

export interface CandidateOverview {
  candidate: CandidateRecord;
  summary: StoredCandidate;
  comparisons: ComparisonHistoryItem[];
}

export interface AppSettings {
  id: string;
  provider: string;
  selected_model: string;
  retention_policy_days: number;
  scoring_configuration: Record<string, number>;
  default_triage_policy: TriagePolicy;
  skill_taxonomy: Array<Record<string, unknown>>;
  blind_review_enabled: boolean;
  credential_configured: boolean;
  created_at: string;
  updated_at: string;
}

export interface TriagePolicy {
  shortlist_fit_threshold: number;
  shortlist_evidence_threshold: number;
  require_mandatory_met: boolean;
  require_no_clarification_flags: boolean;
}

export type TriageSuggestion =
  | "meets_shortlist_threshold"
  | "needs_clarification"
  | "mandatory_concern"
  | "below_threshold"
  | "insufficient_information";

export type RecruiterStatus =
  | "new"
  | "under_review"
  | "needs_clarification"
  | "shortlisted"
  | "interview_planned"
  | "interview_completed"
  | "on_hold"
  | "talent_pool"
  | "not_progressing"
  | "withdrawn"
  | "offer"
  | "hired";

export type RecruiterReasonCode =
  | "mandatory_requirement_not_evidenced"
  | "insufficient_relevant_experience"
  | "role_alignment_gap"
  | "application_incomplete"
  | "candidate_withdrew"
  | "duplicate_application"
  | "position_closed"
  | "other";

export interface JobTriagePolicy {
  job_id: string;
  policy: TriagePolicy;
  version: number;
  updated_at: string;
}

export interface RecruiterDispositionEvent {
  id: string;
  previous_status: RecruiterStatus | null;
  status: RecruiterStatus;
  reason_code: RecruiterReasonCode | null;
  note: string | null;
  assigned_recruiter: string | null;
  triage_suggestion: TriageSuggestion;
  triage_policy: TriagePolicy;
  triage_policy_version: number;
  created_at: string;
}

export interface RecruiterDisposition {
  comparison_id: string;
  status: RecruiterStatus;
  reason_code: RecruiterReasonCode | null;
  note: string | null;
  assigned_recruiter: string | null;
  triage_suggestion: TriageSuggestion;
  triage_policy: TriagePolicy;
  triage_policy_version: number;
  updated_at: string | null;
  events: RecruiterDispositionEvent[];
}
