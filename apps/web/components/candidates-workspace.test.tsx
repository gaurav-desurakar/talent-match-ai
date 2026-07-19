import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, expect, it, vi } from "vitest";

import { CandidatesWorkspace } from "./candidates-workspace";

const summary = {
  id: "candidate-1",
  display_name: "Alex Morgan",
  anonymized_name: "Candidate 1",
  resume_count: 1,
  comparison_count: 0,
  job_count: 0,
  latest_resume_at: "2026-07-19T04:00:00Z",
  last_analysis_at: null,
  created_at: "2026-07-19T03:00:00Z",
  updated_at: "2026-07-19T04:00:00Z",
};

const resume = {
  id: "resume-1",
  candidate_id: summary.id,
  raw_text:
    "Alex Morgan\nBuilt and operated Python production services for users.",
  parsed_content: {},
  source_file: "alex-morgan.pdf",
  sha256: "a".repeat(64),
  extraction_warnings: [],
  created_at: "2026-07-19T04:00:00Z",
};

const job = {
  id: "job-1",
  title: "AI Engineer",
  external_job_id: "AI-1042",
  raw_text: "AI Engineer\nProduction Python experience is required.",
  parsed_content: {},
  requirements: [],
  source_file: null,
  comparison_count: 0,
  candidate_count: 0,
  last_analysis_at: null,
  scorecard_status: "reviewed",
  scorecard_version: 1,
  scorecard_requirement_count: 1,
  created_at: "2026-07-19T03:00:00Z",
  updated_at: "2026-07-19T03:00:00Z",
};

function renderWorkspace() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CandidatesWorkspace />
    </QueryClientProvider>,
  );
}

function jsonResponse(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("opens a candidate workspace and reuses the selected saved resume", async () => {
  let analysisPayload: Record<string, unknown> | undefined;
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/candidates?limit=100"))
          return Promise.resolve(jsonResponse([summary]));
        if (url.endsWith(`/api/candidates/${summary.id}/overview`))
          return Promise.resolve(
            jsonResponse({
              candidate: { ...summary, metadata: {}, resumes: [resume] },
              summary,
              comparisons: [],
            }),
          );
        if (url.endsWith("/api/jobs"))
          return Promise.resolve(jsonResponse([job]));
        if (url.endsWith("/api/analysis-jobs") && init?.method === "POST") {
          analysisPayload = JSON.parse(String(init.body)) as Record<
            string,
            unknown
          >;
          return Promise.resolve(
            jsonResponse(
              {
                job_id: "analysis-1",
                status: "completed",
                candidate_count: 1,
                completed_count: 1,
                comparison_ids: ["comparison-1"],
                events_url: "/api/analysis-jobs/analysis-1/events",
                latest_event: null,
                error: null,
                created_at: "2026-07-19T05:00:00Z",
                completed_at: "2026-07-19T05:00:01Z",
              },
              202,
            ),
          );
        }
        if (url.endsWith("/api/comparisons/comparison-1"))
          return Promise.resolve(
            jsonResponse({
              comparison_id: "comparison-1",
              status: "completed",
              provider: "mock",
              model: "deterministic-mock-v1",
              scorecard_version: 1,
              job_title: job.title,
              candidate_display_name: summary.display_name,
              fit_score: 82,
              evidence_confidence_score: 90,
              mandatory_status: "met",
              recommendation: "shortlist",
              score_breakdown: [],
              requirement_matches: [],
              workflow_events: [],
              clarification_flags: [],
              interview_questions: [],
              quality_checks: [],
              warnings: [],
              methodology_note: "Evidence based.",
              disclaimer: "Decision support only.",
            }),
          );
        return Promise.resolve(jsonResponse([]));
      }),
  );
  renderWorkspace();

  expect(await screen.findByText(summary.display_name)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Open candidate" }));
  expect(
    await screen.findByRole("heading", { name: resume.source_file }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("option", { name: /AI Engineer.*AI-1042/ }),
  ).toBeInTheDocument();

  fireEvent.click(screen.getByLabelText(/Approve this analysis/));
  const compare = screen.getByRole("button", { name: "Compare candidate" });
  await waitFor(() => expect(compare).toBeEnabled());
  fireEvent.click(compare);

  await waitFor(() => expect(analysisPayload).toBeDefined());
  const candidates = analysisPayload?.candidates as Array<
    Record<string, unknown>
  >;
  expect(candidates[0]).toMatchObject({
    candidate_id: summary.id,
    stored_candidate_id: summary.id,
    resume_id: resume.id,
    resume_text: resume.raw_text,
  });
  expect(await screen.findByText(/Fit score/i)).toBeInTheDocument();
});

it("requires confirmation before deleting candidate data", async () => {
  const fetchMock = vi
    .fn()
    .mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/candidates?limit=100"))
        return Promise.resolve(jsonResponse([summary]));
      if (url.endsWith(`/api/candidates/${summary.id}/overview`))
        return Promise.resolve(
          jsonResponse({
            candidate: { ...summary, metadata: {}, resumes: [resume] },
            summary,
            comparisons: [],
          }),
        );
      if (url.endsWith("/api/jobs"))
        return Promise.resolve(jsonResponse([job]));
      if (
        url.endsWith(`/api/candidates/${summary.id}`) &&
        init?.method === "DELETE"
      )
        return Promise.resolve(new Response(null, { status: 204 }));
      return Promise.resolve(jsonResponse([]));
    });
  vi.stubGlobal("fetch", fetchMock);
  renderWorkspace();

  fireEvent.click(
    await screen.findByRole("button", { name: "Open candidate" }),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Delete candidate…" }),
  );
  expect(
    screen.getByRole("button", { name: "Confirm delete" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/api/candidates/${summary.id}`),
      expect.objectContaining({ method: "DELETE" }),
    ),
  );
});
