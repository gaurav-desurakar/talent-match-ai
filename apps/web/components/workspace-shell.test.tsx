import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorkspaceShell } from "./workspace-shell";

const emptyDashboard = {
  total_comparisons: 0,
  active_jobs: 0,
  candidates_analyzed: 0,
  average_fit_score: 0,
  requiring_clarification: 0,
  provider_status: "local mock ready",
  retention_days: 30,
  recent_comparisons: [],
};

function jsonResponse(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderShell() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <WorkspaceShell />
    </QueryClientProvider>,
  );
}

describe("WorkspaceShell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("lands on Dashboard and starts a new job without a New Comparison page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        return Promise.resolve(
          jsonResponse(url.endsWith("/api/dashboard") ? emptyDashboard : []),
        );
      }),
    );
    renderShell();

    expect(
      await screen.findByRole("heading", { name: "Dashboard", level: 1 }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "New comparison" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Analysis history" }),
    ).not.toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: "+ New Job" }));
    expect(
      screen.getByRole("heading", { name: "Jobs", level: 1 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Create a hiring workspace" }),
    ).toBeInTheDocument();
  });

  it("navigates to persisted resource screens", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        return Promise.resolve(
          jsonResponse(url.endsWith("/api/dashboard") ? emptyDashboard : []),
        );
      }),
    );
    renderShell();

    fireEvent.click(screen.getByRole("button", { name: "Candidates" }));
    expect(
      screen.getByRole("heading", { name: "Candidates", level: 1 }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/no saved candidates yet/i),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/current workspace view/i),
    ).toBeInTheDocument();
  });

  it("configures the local mock without requesting an API key", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        return Promise.resolve(
          jsonResponse(
            url.endsWith("/api/dashboard")
              ? emptyDashboard
              : {
                  session_id: "session-1",
                  provider: "mock",
                  model: "mock-evidence-v1",
                  base_url: "local://mock",
                  masked_key: null,
                  expires_at: "2026-07-17T03:00:00Z",
                  storage_mode: "server_memory",
                  sends_documents_externally: false,
                },
            url.endsWith("/api/dashboard") ? 200 : 201,
          ),
        );
      }),
    );
    renderShell();
    fireEvent.click(screen.getByRole("button", { name: "Provider settings" }));

    expect(screen.queryByLabelText(/api key/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /save session/i }));
    expect(
      await screen.findByText(/provider stored in expiring server memory/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/mock configured/i)).toBeInTheDocument();
  });

  it("opens a saved job as an end-to-end hiring workspace", async () => {
    const savedJob = {
      id: "job-1",
      title: "Principal AI Engineer",
      external_job_id: "AI-1001",
      raw_text:
        "Principal AI Engineer\nProduction Python and FastAPI experience is required.",
      parsed_content: {},
      requirements: [],
      source_file: null,
      comparison_count: 1,
      candidate_count: 1,
      last_analysis_at: "2026-07-19T03:00:00Z",
      scorecard_status: "empty",
      scorecard_version: 0,
      scorecard_requirement_count: 0,
      created_at: "2026-07-18T03:00:00Z",
      updated_at: "2026-07-19T03:00:00Z",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        const body = url.endsWith("/api/dashboard")
          ? emptyDashboard
          : url.endsWith("/api/jobs/job-1/overview")
            ? { job: savedJob, comparisons: [] }
            : url.endsWith("/api/jobs/job-1/scorecard")
              ? {
                  job_id: savedJob.id,
                  status: "empty",
                  version: 0,
                  reviewed_at: null,
                  requirements: [],
                  warnings: [],
                }
              : url.endsWith("/api/jobs")
                ? [savedJob]
                : [];
        return Promise.resolve(
          new Response(JSON.stringify(body), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }),
    );
    renderShell();

    fireEvent.click(screen.getByRole("button", { name: "Jobs" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open job" }));
    expect(
      await screen.findByRole("button", { name: "Generate with mock" }),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue(savedJob.title)).toBeInTheDocument();

    expect(screen.getByLabelText("Job description")).toHaveValue(
      savedJob.raw_text,
    );
    expect(
      screen.getByRole("button", {
        name: /Find Talent — Compare 0 Candidates/i,
      }),
    ).toBeDisabled();
    expect(
      screen.getByText(/approve the scorecard above before running/i),
    ).toBeInTheDocument();

    const jobDescription = screen.getByLabelText("Job description");
    fireEvent.click(screen.getByRole("button", { name: "Hide Job Title" }));
    expect(jobDescription).not.toBeVisible();
    expect(
      screen.getByRole("button", { name: "Show Job Title" }),
    ).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(screen.getByRole("button", { name: "Show Job Title" }));
    expect(jobDescription).toBeVisible();
    expect(jobDescription).toHaveValue(savedJob.raw_text);

    const generateScorecard = screen.getByRole("button", {
      name: "Generate with mock",
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Hide Requirements and Scoring" }),
    );
    expect(generateScorecard).not.toBeVisible();
    expect(
      screen.getByRole("button", { name: "Show Requirements and Scoring" }),
    ).toBeInTheDocument();

    const resumeInput = screen.getByLabelText("Candidate 1 resume");
    fireEvent.click(screen.getByRole("button", { name: "Hide Find Talent" }));
    expect(resumeInput).not.toBeVisible();
    expect(
      screen.getByRole("button", { name: "Show Find Talent" }),
    ).toBeInTheDocument();

    const emptyAnalyses = screen.getByText(/no candidates have been analysed/i);
    fireEvent.click(
      screen.getByRole("button", { name: "Hide Candidate Analyses" }),
    );
    expect(emptyAnalyses).not.toBeVisible();
    expect(
      screen.getByRole("button", { name: "Show Candidate Analyses" }),
    ).toBeInTheDocument();
  });

  it("creates a job and continues into scorecard setup", async () => {
    const savedJob = {
      id: "job-new",
      title: "Senior Platform Engineer",
      external_job_id: "PLAT-2042",
      raw_text:
        "Senior Platform Engineer\nProduction Python and Kubernetes experience is required.",
      parsed_content: {},
      requirements: [],
      source_file: null,
      comparison_count: 0,
      candidate_count: 0,
      last_analysis_at: null,
      scorecard_status: "empty",
      scorecard_version: 0,
      scorecard_requirement_count: 0,
      created_at: "2026-07-19T03:00:00Z",
      updated_at: "2026-07-19T03:00:00Z",
    };
    let createdPayload: Record<string, string> | undefined;
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
          const url = String(input);
          if (url.endsWith("/api/jobs") && init?.method === "POST") {
            createdPayload = JSON.parse(String(init.body)) as Record<
              string,
              string
            >;
            return Promise.resolve(
              new Response(JSON.stringify(savedJob), {
                status: 201,
                headers: { "Content-Type": "application/json" },
              }),
            );
          }
          const body = url.endsWith("/api/dashboard")
            ? emptyDashboard
            : url.endsWith("/api/jobs/job-new/overview")
              ? { job: savedJob, comparisons: [] }
              : url.endsWith("/api/jobs/job-new/scorecard")
                ? {
                    job_id: savedJob.id,
                    status: "empty",
                    version: 0,
                    reviewed_at: null,
                    requirements: [],
                    warnings: [],
                  }
                : [];
          return Promise.resolve(
            new Response(JSON.stringify(body), {
              status: 200,
              headers: { "Content-Type": "application/json" },
            }),
          );
        }),
    );
    renderShell();

    fireEvent.click(screen.getByRole("button", { name: "Jobs" }));
    fireEvent.click(await screen.findByRole("button", { name: /new job/i }));
    fireEvent.change(screen.getByLabelText("Job title"), {
      target: { value: savedJob.title },
    });
    fireEvent.change(screen.getByLabelText(/Job ID/), {
      target: { value: savedJob.external_job_id },
    });
    fireEvent.change(screen.getByLabelText("Job description"), {
      target: { value: savedJob.raw_text },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /create job and continue/i }),
    );

    expect(
      await screen.findByRole("button", { name: "Generate with mock" }),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue(savedJob.title)).toBeInTheDocument();
    expect(createdPayload).toEqual({
      title: savedJob.title,
      external_job_id: savedJob.external_job_id,
      raw_text: savedJob.raw_text,
    });
  });

  it("searches saved jobs by title or job ID and sorts list rows", async () => {
    const jobs = [
      {
        id: "job-alpha",
        title: "Principal AI Engineer",
        external_job_id: "AI-1001",
        raw_text:
          "Principal AI Engineer requiring production AI platform experience.",
        parsed_content: {},
        requirements: [],
        source_file: null,
        comparison_count: 2,
        candidate_count: 2,
        last_analysis_at: "2026-07-19T05:00:00Z",
        scorecard_status: "reviewed",
        scorecard_version: 1,
        scorecard_requirement_count: 4,
        created_at: "2026-07-18T03:00:00Z",
        updated_at: "2026-07-19T04:00:00Z",
      },
      {
        id: "job-beta",
        title: "Senior Platform Engineer",
        external_job_id: "PLAT-2042",
        raw_text:
          "Senior Platform Engineer requiring production infrastructure experience.",
        parsed_content: {},
        requirements: [],
        source_file: null,
        comparison_count: 0,
        candidate_count: 0,
        last_analysis_at: null,
        scorecard_status: "draft",
        scorecard_version: 1,
        scorecard_requirement_count: 3,
        created_at: "2026-07-17T03:00:00Z",
        updated_at: "2026-07-20T04:00:00Z",
      },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        return Promise.resolve(
          jsonResponse(url.endsWith("/api/dashboard") ? emptyDashboard : jobs),
        );
      }),
    );
    renderShell();

    fireEvent.click(screen.getByRole("button", { name: "Jobs" }));
    expect(
      (await screen.findAllByRole("heading", { level: 3 })).map(
        (heading) => heading.textContent,
      ),
    ).toEqual(["Senior Platform Engineer", "Principal AI Engineer"]);

    fireEvent.change(screen.getByLabelText("Search jobs"), {
      target: { value: "AI-1001" },
    });
    expect(screen.getByText("Principal AI Engineer")).toBeInTheDocument();
    expect(
      screen.queryByText("Senior Platform Engineer"),
    ).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Search jobs"), {
      target: { value: "platform engineer" },
    });
    expect(screen.getByText("Senior Platform Engineer")).toBeInTheDocument();
    expect(screen.queryByText("Principal AI Engineer")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Search jobs"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("Sort jobs"), {
      target: { value: "created_desc" },
    });
    expect(
      screen
        .getAllByRole("heading", { level: 3 })
        .map((heading) => heading.textContent),
    ).toEqual(["Principal AI Engineer", "Senior Platform Engineer"]);
    expect(
      screen.getByRole("list", { name: "Saved jobs" }).children,
    ).toHaveLength(2);
  });

  it("opens persisted candidate evidence without starting another analysis", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    const savedJob = {
      id: "job-evidence",
      title: "AI Engineer",
      external_job_id: "AI-2002",
      raw_text: "AI Engineer\nProduction Python experience is required.",
      parsed_content: {},
      requirements: [],
      source_file: null,
      comparison_count: 1,
      candidate_count: 1,
      last_analysis_at: "2026-07-19T05:00:00Z",
      scorecard_status: "reviewed",
      scorecard_version: 1,
      scorecard_requirement_count: 1,
      created_at: "2026-07-19T03:00:00Z",
      updated_at: "2026-07-19T05:00:00Z",
    };
    const historyItem = {
      id: "comparison-evidence",
      job_description_id: savedJob.id,
      candidate_id: "candidate-evidence",
      job_title: savedJob.title,
      candidate_display_name: "Alex Morgan",
      provider: "mock",
      model: "deterministic-mock-v1",
      scorecard_version: 1,
      status: "completed",
      fit_score: 88,
      evidence_confidence_score: 91,
      mandatory_status: "met",
      recommendation: "strong_shortlist",
      created_at: "2026-07-19T05:00:00Z",
      completed_at: "2026-07-19T05:00:01Z",
    };
    const evidenceResult = {
      comparison_id: historyItem.id,
      status: "completed",
      provider: "mock",
      model: historyItem.model,
      scorecard_version: 1,
      job_title: savedJob.title,
      candidate_display_name: historyItem.candidate_display_name,
      fit_score: 88,
      evidence_confidence_score: 91,
      mandatory_status: "met",
      recommendation: "strong_shortlist",
      score_breakdown: [
        {
          category: "core_technical_skills",
          weight: 20,
          score: 88,
          evidence_count: 1,
          explanation: "Python production evidence was found.",
        },
      ],
      requirement_matches: [
        {
          requirement: {
            id: "req-1",
            text: "Production Python experience is required.",
            canonical_concept: "Production Python",
            classification: "mandatory",
            category: "core_technical_skills",
            importance: 1,
            source_reference: "job-line-2",
          },
          match_type: "exact",
          score: 92,
          confidence: 0.95,
          evidence: [
            {
              text: "Built Python production services for 10,000 users.",
              source_reference: "Resume",
              section: "Experience",
            },
            {
              text: "Operated the Python service during production incidents.",
              source_reference: "Resume",
              section: "Experience",
            },
          ],
          explanation: "The resume contains direct production Python evidence.",
          uncertainties: [],
          clarification_required: false,
        },
      ],
      workflow_events: [],
      clarification_flags: [],
      interview_questions: [],
      quality_checks: [],
      warnings: [],
      methodology_note:
        "Deterministic scoring was applied after evidence extraction.",
      disclaimer: "Use this result as decision support only.",
    };
    let exportPayload: { comparison_ids: string[] } | undefined;
    const fetchMock = vi
      .fn()
      .mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/export/csv")) {
          exportPayload = JSON.parse(String(init?.body)) as {
            comparison_ids: string[];
          };
          return Promise.resolve(
            new Response("candidate,fit\nAlex Morgan,88", {
              status: 200,
              headers: { "Content-Type": "text/csv" },
            }),
          );
        }
        const body = url.endsWith("/api/dashboard")
          ? emptyDashboard
          : url.endsWith("/api/comparisons/comparison-evidence/disposition")
            ? {
                comparison_id: historyItem.id,
                status: "new",
                reason_code: null,
                note: null,
                assigned_recruiter: null,
                triage_suggestion: "meets_shortlist_threshold",
                triage_policy: {
                  shortlist_fit_threshold: 80,
                  shortlist_evidence_threshold: 80,
                  require_mandatory_met: true,
                  require_no_clarification_flags: true,
                },
                triage_policy_version: 1,
                updated_at: null,
                events: [],
              }
            : url.endsWith("/api/jobs/job-evidence/overview")
              ? { job: savedJob, comparisons: [historyItem] }
              : url.endsWith("/api/jobs/job-evidence/scorecard")
                ? {
                    job_id: savedJob.id,
                    status: "reviewed",
                    version: 1,
                    reviewed_at: "2026-07-19T04:00:00Z",
                    requirements: [],
                    warnings: [],
                  }
                : url.endsWith("/api/comparisons/comparison-evidence")
                  ? evidenceResult
                  : url.endsWith("/api/jobs")
                    ? [savedJob]
                    : [];
        return Promise.resolve(
          new Response(JSON.stringify(body), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      });
    vi.stubGlobal("fetch", fetchMock);
    renderShell();

    fireEvent.click(screen.getByRole("button", { name: "Jobs" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open job" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "View evidence" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Alex Morgan", level: 2 }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Built Python production services for 10,000 users\./),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Operated the Python service during production incidents\./,
      ),
    ).toBeInTheDocument();
    expect(
      consoleError.mock.calls.some(([message]) =>
        String(message).includes("two children with the same key"),
      ),
    ).toBe(false);
    expect(
      screen.getByRole("button", { name: "Viewing evidence" }),
    ).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Select Alex Morgan analysis for export",
      }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Export selected CSV" }),
    );
    await waitFor(() =>
      expect(exportPayload).toEqual({ comparison_ids: [historyItem.id] }),
    );
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith("/api/analysis-jobs") &&
          (init as RequestInit | undefined)?.method === "POST",
      ),
    ).toBe(false);
  });
});
