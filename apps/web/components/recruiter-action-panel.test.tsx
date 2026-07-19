import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, expect, it, vi } from "vitest";

import { RecruiterActionPanel } from "./recruiter-action-panel";

const policy = {
  shortlist_fit_threshold: 80,
  shortlist_evidence_threshold: 80,
  require_mandatory_met: true,
  require_no_clarification_flags: true,
};

function response(value: unknown) {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RecruiterActionPanel comparisonId="comparison-1" jobId="job-1" />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("keeps the triage suggestion separate from the recruiter status", async () => {
  let saved: Record<string, unknown> | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "PUT") {
        saved = JSON.parse(String(init.body)) as Record<string, unknown>;
        return Promise.resolve(
          response({
            comparison_id: "comparison-1",
            status: "shortlisted",
            reason_code: null,
            note: "Evidence reviewed.",
            assigned_recruiter: "Recruiting Team A",
            triage_suggestion: "below_threshold",
            triage_policy: policy,
            triage_policy_version: 1,
            updated_at: "2026-07-19T08:00:00Z",
            events: [],
          }),
        );
      }
      return Promise.resolve(
        response({
          comparison_id: "comparison-1",
          status: "new",
          reason_code: null,
          note: null,
          assigned_recruiter: null,
          triage_suggestion: "below_threshold",
          triage_policy: policy,
          triage_policy_version: 1,
          updated_at: null,
          events: [],
        }),
      );
    }),
  );

  renderPanel();
  expect(await screen.findByText(/system triage suggestion: below threshold/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Shortlist" }));
  fireEvent.change(screen.getByLabelText("Assigned recruiter"), {
    target: { value: "Recruiting Team A" },
  });
  fireEvent.change(screen.getByLabelText("Recruiter note"), {
    target: { value: "Evidence reviewed." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save recruiter action" }));

  await waitFor(() => expect(saved).toBeDefined());
  expect(saved).toEqual({
    status: "shortlisted",
    note: "Evidence reviewed.",
    assigned_recruiter: "Recruiting Team A",
  });
});

it("requires a reason before saving Not progressing", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      response({
        comparison_id: "comparison-1",
        status: "new",
        reason_code: null,
        note: null,
        assigned_recruiter: null,
        triage_suggestion: "needs_clarification",
        triage_policy: policy,
        triage_policy_version: 1,
        updated_at: null,
        events: [],
      }),
    ),
  );

  renderPanel();
  await screen.findByText(/system triage suggestion: needs clarification/i);
  fireEvent.click(screen.getByRole("button", { name: "Not progressing" }));

  expect(screen.getByText("Select a job-related reason.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Save recruiter action" })).toBeDisabled();
});
