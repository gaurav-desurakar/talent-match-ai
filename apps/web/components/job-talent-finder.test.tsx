import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, expect, it, vi } from "vitest";

import type { ComparisonResult, StoredJob } from "@/types/comparison";
import { JobTalentFinder } from "./job-talent-finder";

const job: StoredJob = {
  id: "job-1",
  title: "AI Engineer",
  external_job_id: "AI-1042",
  raw_text: "AI Engineer\nProduction Python experience is required.",
  parsed_content: {},
  requirements: [],
  source_file: null,
  triage_policy: {
    shortlist_fit_threshold: 80,
    shortlist_evidence_threshold: 80,
    require_mandatory_met: true,
    require_no_clarification_flags: true,
  },
  triage_policy_version: 1,
  comparison_count: 0,
  candidate_count: 0,
  last_analysis_at: null,
  scorecard_status: "reviewed",
  scorecard_version: 1,
  scorecard_requirement_count: 1,
  created_at: "2026-07-19T03:00:00Z",
  updated_at: "2026-07-19T03:00:00Z",
};

function renderFinder(
  scorecardStatus: StoredJob["scorecard_status"] = "reviewed",
  onViewEvidence?: (result: ComparisonResult) => void,
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <JobTalentFinder
        job={job}
        scorecardStatus={scorecardStatus}
        onViewEvidence={onViewEvidence}
      />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

it("requires an approved scorecard before finding talent", async () => {
  renderFinder("draft");

  expect(
    await screen.findByText(/approve the scorecard above before running/i),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /find talent — compare/i }),
  ).toBeDisabled();
});

it("submits one candidate against the approved saved-job scorecard", async () => {
  let analysisPayload: Record<string, unknown> | undefined;
  const onViewEvidence = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/analysis-jobs") && init?.method === "POST") {
        analysisPayload = JSON.parse(String(init.body)) as Record<string, unknown>;
        return Promise.resolve(
          new Response(
            JSON.stringify({
              job_id: "analysis-1",
              status: "completed",
              candidate_count: 1,
              completed_count: 1,
              comparison_ids: ["comparison-1"],
              events_url: "/api/analysis-jobs/analysis-1/events",
              latest_event: null,
              error: null,
              created_at: "2026-07-19T04:00:00Z",
              completed_at: "2026-07-19T04:00:01Z",
            }),
            { status: 202, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      if (url.endsWith("/api/comparisons/comparison-1")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              comparison_id: "comparison-1",
              candidate_display_name: "Candidate 1",
              fit_score: 84,
              mandatory_status: "met",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }),
  );
  renderFinder("reviewed", onViewEvidence);
  await screen.findByRole("button", { name: /find talent — compare/i });

  fireEvent.change(screen.getByLabelText("Candidate 1 resume"), {
    target: {
      value: "Candidate One\nBuilt and operated Python production services for users.",
    },
  });
  fireEvent.click(screen.getByRole("checkbox", { name: /approve this analysis/i }));
  fireEvent.click(
    screen.getByRole("button", { name: /find talent — compare 1 candidate/i }),
  );

  expect(await screen.findByText("Talent comparison complete")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "View evidence" }));
  expect(onViewEvidence).toHaveBeenCalledWith(
    expect.objectContaining({ comparison_id: "comparison-1" }),
  );
  await waitFor(() => expect(analysisPayload).toBeDefined());
  expect(analysisPayload?.job_id).toBe(job.id);
  expect(analysisPayload?.job_description_text).toBe(job.raw_text);
  expect(analysisPayload?.provider).toBe("mock");
  expect(analysisPayload?.candidates).toEqual([
    {
      candidate_id: "candidate-1",
      display_name: "Candidate 1",
      resume_text:
        "Candidate One\nBuilt and operated Python production services for users.",
    },
  ]);
});
