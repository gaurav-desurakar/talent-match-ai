import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, expect, it, vi } from "vitest";

import type { JobScorecard } from "@/types/comparison";
import { JobScorecardEditor } from "./job-scorecard";

afterEach(() => vi.unstubAllGlobals());

it("extracts, edits, and approves a recruiter scorecard", async () => {
  let stored: JobScorecard = {
    job_id: "job-1",
    status: "empty",
    version: 0,
    reviewed_at: null,
    requirements: [],
    warnings: [],
  };
  let approvedPayload: Record<string, unknown> | undefined;
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
        const method = init?.method ?? "GET";
        if (method === "POST") {
          stored = {
            ...stored,
            status: "draft",
            version: 1,
            requirements: [
              {
                id: "req-1",
                text: "Production Python experience is required.",
                canonical_concept: "Python",
                classification: "mandatory",
                category: "core_technical_skills",
                importance: 1,
                source_reference: "job-line-2",
                included: true,
              },
            ],
          };
        }
        if (method === "PUT") {
          approvedPayload = JSON.parse(String(init?.body)) as Record<
            string,
            unknown
          >;
          stored = {
            ...stored,
            status: "reviewed",
            reviewed_at: "2026-07-19T04:00:00Z",
          };
        }
        return Promise.resolve(
          new Response(JSON.stringify(stored), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <JobScorecardEditor jobId="job-1" />
    </QueryClientProvider>,
  );

  fireEvent.click(
    await screen.findByRole("button", { name: "Generate with mock" }),
  );
  expect(
    await screen.findByText("Production Python experience is required."),
  ).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Classification"), {
    target: { value: "strongly_preferred" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Approve scorecard" }));

  await waitFor(() => expect(approvedPayload).toBeDefined());
  expect(approvedPayload?.approve).toBe(true);
  expect(
    (approvedPayload?.requirements as Array<{ classification: string }>)[0]
      .classification,
  ).toBe("strongly_preferred");
  expect(await screen.findByText(/reviewed · version 1/i)).toBeInTheDocument();
});
