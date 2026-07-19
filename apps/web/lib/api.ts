import type {
  BatchComparisonResult,
  AnalysisJob,
  ComparisonResult,
  DashboardData,
  DocumentExtraction,
  DocumentSourceReference,
  ProviderSession,
  AppSettings,
  StoredCandidate,
  CandidateOverview,
  ResumeVersion,
  StoredJob,
  JobOverview,
  JobScorecard,
  JobScorecardRequirement,
  JobTriagePolicy,
  RecruiterDisposition,
  RecruiterReasonCode,
  RecruiterStatus,
  TriagePolicy,
} from "@/types/comparison";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    message: string,
    public readonly code = "UNKNOWN_ERROR",
  ) {
    super(message);
  }
}

export async function uploadDocument(
  file: File,
  documentType: "resume" | "job_description",
): Promise<DocumentExtraction> {
  const formData = new FormData();
  formData.append("file", file);
  const path = documentType === "resume" ? "resumes" : "job-descriptions";
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/${path}/upload`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new ApiError(
      "The API is unavailable. Confirm the FastAPI service is running.",
      "NETWORK_ERROR",
    );
  }
  const payload = (await response.json()) as
    | DocumentExtraction
    | {
        error?: { code?: string; message?: string };
      };
  if (!response.ok) {
    const error = "error" in payload ? payload.error : undefined;
    throw new ApiError(
      error?.message ?? "The document could not be extracted.",
      error?.code,
    );
  }
  return payload as DocumentExtraction;
}

async function errorFromResponse(
  response: Response,
  fallback: string,
): Promise<never> {
  const payload = (await response.json().catch(() => ({}))) as {
    error?: { code?: string; message?: string };
  };
  throw new ApiError(
    payload.error?.message ?? fallback,
    payload.error?.code ?? "UNKNOWN_ERROR",
  );
}

export async function createBackgroundComparison(
  input: {
    job_description_text: string;
    job_id?: string;
    job_title?: string;
    provider: string;
    credential_session_id?: string;
    blind_review: boolean;
    scoring_weights?: Record<string, number>;
    job_source_references?: DocumentSourceReference[];
    candidates: Array<{
      candidate_id: string;
      display_name: string;
      stored_candidate_id?: string;
      resume_id?: string;
      resume_text: string;
      resume_source_references?: DocumentSourceReference[];
    }>;
  },
  onProgress?: (job: AnalysisJob) => void,
): Promise<BatchComparisonResult> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/analysis-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  } catch {
    throw new ApiError(
      "The API is unavailable. Confirm the FastAPI service is running.",
      "NETWORK_ERROR",
    );
  }
  if (!response.ok)
    return errorFromResponse(response, "The analysis could not start.");
  let job = (await response.json()) as AnalysisJob;
  onProgress?.(job);
  for (let attempt = 0; attempt < 2400; attempt += 1) {
    if (["completed", "failed", "cancelled"].includes(job.status)) break;
    await new Promise((resolve) => setTimeout(resolve, 250));
    const statusResponse = await fetch(
      `${API_URL}/api/analysis-jobs/${job.job_id}`,
    );
    if (!statusResponse.ok)
      return errorFromResponse(
        statusResponse,
        "Analysis status is unavailable.",
      );
    job = (await statusResponse.json()) as AnalysisJob;
    onProgress?.(job);
  }
  if (job.status !== "completed") {
    throw new ApiError(
      job.error?.message ?? `The analysis ${job.status}.`,
      job.error?.code ?? `ANALYSIS_${job.status.toUpperCase()}`,
    );
  }
  const comparisons = await Promise.all(
    job.comparison_ids.map(async (id) => {
      const result = await fetch(`${API_URL}/api/comparisons/${id}`);
      if (!result.ok)
        return errorFromResponse(result, "A comparison result is unavailable.");
      return (await result.json()) as ComparisonResult;
    }),
  );
  return {
    batch_id: job.job_id,
    status: "completed",
    candidate_count: comparisons.length,
    comparisons: comparisons.map((comparison, index) => ({
      candidate_id: input.candidates[index].candidate_id,
      display_name: comparison.candidate_display_name,
      comparison,
    })),
  };
}

export async function configureProvider(input: {
  provider: string;
  api_key?: string;
  model?: string;
  base_url?: string;
  timeout_seconds?: number;
  max_retries?: number;
}): Promise<ProviderSession> {
  const response = await fetch(`${API_URL}/api/providers/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok)
    return errorFromResponse(response, "The provider could not be configured.");
  return (await response.json()) as ProviderSession;
}

export async function validateProvider(sessionId: string) {
  const response = await fetch(`${API_URL}/api/providers/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential_session_id: sessionId }),
  });
  if (!response.ok)
    return errorFromResponse(response, "The provider connection failed.");
  return (await response.json()) as {
    status: string;
    message: string;
    models: string[];
  };
}

export async function removeProviderSession(sessionId: string) {
  const response = await fetch(
    `${API_URL}/api/providers/session/${sessionId}`,
    {
      method: "DELETE",
    },
  );
  if (!response.ok)
    return errorFromResponse(
      response,
      "The provider session could not be removed.",
    );
}

export async function getDashboard(): Promise<DashboardData> {
  const response = await fetch(`${API_URL}/api/dashboard`);
  if (!response.ok)
    return errorFromResponse(response, "Dashboard data is unavailable.");
  return (await response.json()) as DashboardData;
}

export async function getComparison(
  comparisonId: string,
): Promise<ComparisonResult> {
  const response = await fetch(`${API_URL}/api/comparisons/${comparisonId}`);
  if (!response.ok)
    return errorFromResponse(
      response,
      "The comparison evidence is unavailable.",
    );
  return (await response.json()) as ComparisonResult;
}

export async function getJobs(): Promise<StoredJob[]> {
  const response = await fetch(`${API_URL}/api/jobs`);
  if (!response.ok)
    return errorFromResponse(response, "Saved jobs are unavailable.");
  return (await response.json()) as StoredJob[];
}

export async function createJob(input: {
  title: string;
  external_job_id?: string;
  raw_text: string;
}): Promise<{ id: string }> {
  const response = await fetch(`${API_URL}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok)
    return errorFromResponse(response, "The job could not be created.");
  return (await response.json()) as { id: string };
}

export async function getJobOverview(jobId: string): Promise<JobOverview> {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}/overview`);
  if (!response.ok)
    return errorFromResponse(response, "The saved job is unavailable.");
  return (await response.json()) as JobOverview;
}

export async function updateJob(
  jobId: string,
  input: { title?: string; external_job_id?: string | null; raw_text?: string },
): Promise<void> {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok)
    return errorFromResponse(response, "The saved job could not be updated.");
  await response.json();
}

export async function getJobTriagePolicy(
  jobId: string,
): Promise<JobTriagePolicy> {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}/triage-policy`);
  if (!response.ok)
    return errorFromResponse(response, "The job triage policy is unavailable.");
  return (await response.json()) as JobTriagePolicy;
}

export async function updateJobTriagePolicy(
  jobId: string,
  policy: TriagePolicy,
): Promise<JobTriagePolicy> {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}/triage-policy`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(policy),
  });
  if (!response.ok)
    return errorFromResponse(
      response,
      "The job triage policy could not be saved.",
    );
  return (await response.json()) as JobTriagePolicy;
}

export async function getRecruiterDisposition(
  comparisonId: string,
): Promise<RecruiterDisposition> {
  const response = await fetch(
    `${API_URL}/api/comparisons/${comparisonId}/disposition`,
  );
  if (!response.ok)
    return errorFromResponse(
      response,
      "The recruiter action record is unavailable.",
    );
  return (await response.json()) as RecruiterDisposition;
}

export async function updateRecruiterDisposition(
  comparisonId: string,
  input: {
    status: RecruiterStatus;
    reason_code?: RecruiterReasonCode;
    note?: string;
    assigned_recruiter?: string;
  },
): Promise<RecruiterDisposition> {
  const response = await fetch(
    `${API_URL}/api/comparisons/${comparisonId}/disposition`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok)
    return errorFromResponse(
      response,
      "The recruiter action could not be saved.",
    );
  return (await response.json()) as RecruiterDisposition;
}

export async function deleteJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}`, {
    method: "DELETE",
  });
  if (!response.ok)
    return errorFromResponse(response, "The saved job could not be deleted.");
}

export async function getJobScorecard(jobId: string): Promise<JobScorecard> {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}/scorecard`);
  if (!response.ok)
    return errorFromResponse(response, "The job scorecard is unavailable.");
  return (await response.json()) as JobScorecard;
}

export async function extractJobScorecard(
  jobId: string,
  input: { provider: string; credential_session_id?: string },
): Promise<JobScorecard> {
  const response = await fetch(
    `${API_URL}/api/jobs/${jobId}/scorecard/extract`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok)
    return errorFromResponse(
      response,
      "Job requirements could not be extracted.",
    );
  return (await response.json()) as JobScorecard;
}

export async function updateJobScorecard(
  jobId: string,
  input: { requirements: JobScorecardRequirement[]; approve: boolean },
): Promise<JobScorecard> {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}/scorecard`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok)
    return errorFromResponse(response, "The job scorecard could not be saved.");
  return (await response.json()) as JobScorecard;
}

export async function getCandidates(): Promise<StoredCandidate[]> {
  const response = await fetch(`${API_URL}/api/candidates?limit=100`);
  if (!response.ok)
    return errorFromResponse(response, "Saved candidates are unavailable.");
  return (await response.json()) as StoredCandidate[];
}

export async function getCandidateOverview(
  candidateId: string,
): Promise<CandidateOverview> {
  const response = await fetch(
    `${API_URL}/api/candidates/${candidateId}/overview`,
  );
  if (!response.ok)
    return errorFromResponse(
      response,
      "The candidate workspace is unavailable.",
    );
  return (await response.json()) as CandidateOverview;
}

export async function addCandidateResume(
  candidateId: string,
  input: {
    raw_text: string;
    parsed_content?: Record<string, unknown>;
    source_file?: string;
    sha256?: string;
    extraction_warnings?: string[];
  },
): Promise<ResumeVersion> {
  const response = await fetch(
    `${API_URL}/api/candidates/${candidateId}/resumes`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok)
    return errorFromResponse(
      response,
      "The resume version could not be saved.",
    );
  return (await response.json()) as ResumeVersion;
}

export async function deleteCandidate(candidateId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/candidates/${candidateId}`, {
    method: "DELETE",
  });
  if (!response.ok)
    return errorFromResponse(response, "The candidate could not be deleted.");
}

export async function getSettings(): Promise<AppSettings> {
  const response = await fetch(`${API_URL}/api/settings`);
  if (!response.ok)
    return errorFromResponse(response, "Settings are unavailable.");
  return (await response.json()) as AppSettings;
}

export async function updateSettings(input: {
  provider: string;
  selected_model: string;
  retention_policy_days: number;
  scoring_configuration: Record<string, number>;
  default_triage_policy: TriagePolicy;
  skill_taxonomy: Array<Record<string, unknown>>;
  blind_review_enabled: boolean;
}): Promise<AppSettings> {
  const response = await fetch(`${API_URL}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok)
    return errorFromResponse(response, "Settings could not be saved.");
  return (await response.json()) as AppSettings;
}

export async function deleteAllData(): Promise<void> {
  const response = await fetch(`${API_URL}/api/privacy/all-data`, {
    method: "DELETE",
  });
  if (!response.ok)
    return errorFromResponse(response, "Saved data could not be deleted.");
}

export async function exportComparisons(
  format: "report" | "json" | "csv" | "interview-guide",
  comparisonIds: string[],
): Promise<Blob> {
  const body =
    format === "interview-guide"
      ? { comparison_id: comparisonIds[0] }
      : { comparison_ids: comparisonIds };
  const response = await fetch(`${API_URL}/api/export/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok)
    return errorFromResponse(response, "The export could not be generated.");
  return response.blob();
}
