"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import {
  extractJobScorecard,
  getJobScorecard,
  updateJobScorecard,
} from "@/lib/api";
import type {
  JobScorecardRequirement,
  ProviderSession,
  RequirementClassification,
  ScoreCategory,
} from "@/types/comparison";
import { CollapsibleSection } from "./collapsible-section";

const CLASSIFICATIONS: RequirementClassification[] = [
  "mandatory",
  "strongly_preferred",
  "preferred",
  "contextual",
  "informational",
];

const CATEGORIES: ScoreCategory[] = [
  "core_technical_skills",
  "responsibility_alignment",
  "relevant_experience",
  "project_similarity",
  "seniority_and_ownership",
  "measurable_achievements",
  "domain_experience",
  "stakeholder_and_customer_experience",
  "education_and_certifications",
  "career_progression",
];

function label(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function providerLabel(value: string) {
  if (value === "openai") return "OpenAI";
  if (value === "google") return "Google";
  if (value === "anthropic") return "Anthropic";
  if (value === "groq") return "Groq";
  return value;
}

export function JobScorecardEditor({
  jobId,
  providerSession,
  onScorecardChange,
}: {
  jobId: string;
  providerSession?: ProviderSession;
  onScorecardChange?: (status: "empty" | "draft" | "reviewed") => void;
}) {
  const queryClient = useQueryClient();
  const scorecard = useQuery({
    queryKey: ["job-scorecard", jobId],
    queryFn: () => getJobScorecard(jobId),
  });
  const [requirements, setRequirements] = useState<JobScorecardRequirement[]>([]);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    if (scorecard.data) {
      setRequirements(scorecard.data.requirements);
      setIsDirty(false);
    }
  }, [scorecard.data]);

  const extract = useMutation({
    mutationFn: () =>
      extractJobScorecard(jobId, {
        provider: providerSession?.provider ?? "mock",
        credential_session_id: providerSession?.session_id,
      }),
    onSuccess: async (result) => {
      setRequirements(result.requirements);
      setIsDirty(false);
      onScorecardChange?.(result.status);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["job-scorecard", jobId] }),
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["job-overview", jobId] }),
      ]);
    },
  });
  const save = useMutation({
    mutationFn: (approve: boolean) =>
      updateJobScorecard(jobId, { requirements, approve }),
    onSuccess: async (result) => {
      setRequirements(result.requirements);
      setIsDirty(false);
      onScorecardChange?.(result.status);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["job-scorecard", jobId] }),
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["job-overview", jobId] }),
      ]);
    },
  });

  function updateRequirement(
    id: string,
    update: Partial<JobScorecardRequirement>,
  ) {
    setIsDirty(true);
    onScorecardChange?.("draft");
    setRequirements((current) =>
      current.map((item) => (item.id === id ? { ...item, ...update } : item)),
    );
  }

  if (scorecard.isLoading) return <p aria-live="polite">Loading scorecard…</p>;
  if (scorecard.isError || !scorecard.data)
    return (
      <p role="alert" className="text-sm text-red-700">
        {scorecard.error?.message ?? "The job scorecard could not be loaded."}
      </p>
    );

  const configuredProvider = providerSession?.provider ?? "mock";
  const configuredProviderLabel = providerLabel(configuredProvider);
  const sendsExternally = providerSession?.sends_documents_externally ?? false;
  const includedCount = requirements.filter((item) => item.included).length;
  const warnings = [
    ...new Set([...scorecard.data.warnings, ...(extract.data?.warnings ?? [])]),
  ];

  return (
    <CollapsibleSection
      title="Requirements and Scoring"
      description="Review and approve the exact criteria used for candidate comparisons."
      status={
        <span className="rounded-full border border-line px-2.5 py-1 text-[11px] font-semibold capitalize text-muted">
          {isDirty ? "draft" : scorecard.data.status} · version {scorecard.data.version || "–"}
        </span>
      }
    >
      <div className="p-5 sm:p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          {scorecard.data.reviewed_at && (
            <p className="text-xs text-muted">
              Reviewed {new Date(scorecard.data.reviewed_at).toLocaleString()}
            </p>
          )}
        </div>
        <button
          type="button"
          disabled={extract.isPending}
          onClick={() => extract.mutate()}
          className="rounded-md border border-line px-3 py-2 text-xs font-semibold disabled:opacity-50"
        >
          {extract.isPending
            ? "Generating…"
            : requirements.length
              ? `Regenerate with ${configuredProviderLabel}`
              : `Generate with ${configuredProviderLabel}`}
        </button>
      </div>

      <div className="mt-4 rounded-lg border border-line bg-canvas/50 p-3 text-xs leading-5 text-muted">
        {sendsExternally
          ? `Generating sends this job description to ${configuredProviderLabel}.`
          : "Generation remains local and uses the deterministic mock provider."}
        {" "}Candidate résumés are not used during scorecard extraction.
      </div>

      {warnings.map((warning) => (
        <p key={warning} className="mt-2 text-xs text-amber">
          {warning}
        </p>
      ))}
      {(extract.isError || save.isError) && (
        <p role="alert" className="mt-3 text-sm text-red-700">
          {extract.error?.message ?? save.error?.message}
        </p>
      )}

      {requirements.length ? (
        <div className="mt-5 space-y-3">
          {requirements.map((item) => (
            <article
              key={item.id}
              className={`rounded-xl border p-4 ${item.included ? "border-line" : "border-dashed border-line bg-canvas/40"}`}
            >
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  aria-label={`Include requirement: ${item.text}`}
                  checked={item.included}
                  onChange={(event) =>
                    updateRequirement(item.id, { included: event.target.checked })
                  }
                  className="mt-1 h-4 w-4 accent-brand-600"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold leading-6 text-ink">{item.text}</p>
                  <p className="mt-1 text-[11px] text-muted">
                    Source: {item.source_reference} · {item.canonical_concept ?? "No canonical concept"}
                  </p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    <label className="text-xs font-semibold text-muted">
                      Classification
                      <select
                        value={item.classification}
                        onChange={(event) =>
                          updateRequirement(item.id, {
                            classification: event.target.value as RequirementClassification,
                          })
                        }
                        className="mt-1 w-full rounded-md border border-line bg-white px-2 py-2 font-normal text-ink"
                      >
                        {CLASSIFICATIONS.map((value) => (
                          <option key={value} value={value}>
                            {label(value)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-xs font-semibold text-muted">
                      Category
                      <select
                        value={item.category}
                        onChange={(event) =>
                          updateRequirement(item.id, {
                            category: event.target.value as ScoreCategory,
                          })
                        }
                        className="mt-1 w-full rounded-md border border-line bg-white px-2 py-2 font-normal text-ink"
                      >
                        {CATEGORIES.map((value) => (
                          <option key={value} value={value}>
                            {label(value)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-xs font-semibold text-muted">
                      Importance ({Math.round(item.importance * 100)}%)
                      <input
                        type="range"
                        min="0.1"
                        max="1"
                        step="0.05"
                        value={item.importance}
                        onChange={(event) =>
                          updateRequirement(item.id, {
                            importance: Number(event.target.value),
                          })
                        }
                        className="mt-3 w-full accent-brand-600"
                      />
                    </label>
                  </div>
                </div>
              </div>
            </article>
          ))}
          <div className="flex flex-col justify-between gap-3 border-t border-line pt-4 sm:flex-row sm:items-center">
            <p className="text-xs text-muted">
              {includedCount} of {requirements.length} requirements included
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={save.isPending}
                onClick={() => save.mutate(false)}
                className="rounded-md border border-line px-3 py-2 text-xs font-semibold disabled:opacity-50"
              >
                Save draft
              </button>
              <button
                type="button"
                disabled={!includedCount || save.isPending}
                onClick={() => save.mutate(true)}
                className="rounded-md bg-brand-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
              >
                Approve scorecard
              </button>
            </div>
          </div>
        </div>
      ) : (
        <p className="mt-5 rounded-xl border border-dashed border-line p-4 text-sm text-muted">
          Generate requirements to create the first recruiter-reviewable scorecard.
        </p>
      )}
      </div>
    </CollapsibleSection>
  );
}
