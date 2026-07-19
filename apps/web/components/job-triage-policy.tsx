"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getJobTriagePolicy, updateJobTriagePolicy } from "@/lib/api";
import type { TriagePolicy } from "@/types/comparison";
import { CollapsibleSection } from "./collapsible-section";

const DEFAULT_POLICY: TriagePolicy = {
  shortlist_fit_threshold: 80,
  shortlist_evidence_threshold: 80,
  require_mandatory_met: true,
  require_no_clarification_flags: true,
};

export function JobTriagePolicyEditor({ jobId }: { jobId: string }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["job-triage-policy", jobId],
    queryFn: () => getJobTriagePolicy(jobId),
  });
  const [policy, setPolicy] = useState<TriagePolicy>(DEFAULT_POLICY);

  useEffect(() => {
    if (query.data?.policy) setPolicy(query.data.policy);
  }, [query.data]);

  const save = useMutation({
    mutationFn: () => updateJobTriagePolicy(jobId, policy),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["job-triage-policy", jobId] }),
        queryClient.invalidateQueries({ queryKey: ["job-overview", jobId] }),
        queryClient.invalidateQueries({ queryKey: ["recruiter-disposition"] }),
        queryClient.invalidateQueries({ queryKey: ["candidate-overview"] }),
      ]);
    },
  });

  return (
    <CollapsibleSection
      title="Recruiter Triage Policy"
      description="Set transparent thresholds for suggestions. Recruiters still make every status decision."
      status={
        <span className="rounded-full border border-line px-2.5 py-1 text-[11px] font-semibold text-muted">
          Policy v{query.data?.version ?? 1}
        </span>
      }
      defaultOpen={false}
    >
      <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6">
        <label className="text-xs font-semibold text-muted">
          Shortlist fit threshold
          <input
            aria-label="Shortlist fit threshold"
            type="number"
            min={0}
            max={100}
            value={policy.shortlist_fit_threshold}
            onChange={(event) =>
              setPolicy((current) => ({
                ...current,
                shortlist_fit_threshold: Number(event.target.value),
              }))
            }
            className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm text-ink"
          />
        </label>
        <label className="text-xs font-semibold text-muted">
          Evidence confidence threshold
          <input
            aria-label="Evidence confidence threshold"
            type="number"
            min={0}
            max={100}
            value={policy.shortlist_evidence_threshold}
            onChange={(event) =>
              setPolicy((current) => ({
                ...current,
                shortlist_evidence_threshold: Number(event.target.value),
              }))
            }
            className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm text-ink"
          />
        </label>
        <PolicyCheckbox
          checked={policy.require_mandatory_met}
          onChange={(checked) =>
            setPolicy((current) => ({ ...current, require_mandatory_met: checked }))
          }
          title="Require mandatory requirements to be met"
          description="Not applicable is accepted; partial, unclear, and not met trigger a concern."
        />
        <PolicyCheckbox
          checked={policy.require_no_clarification_flags}
          onChange={(checked) =>
            setPolicy((current) => ({
              ...current,
              require_no_clarification_flags: checked,
            }))
          }
          title="Require no clarification flags"
          description="Evidence gaps remain visible and should be checked with the candidate."
        />
      </div>
      <div className="flex flex-col justify-between gap-3 border-t border-line bg-canvas/40 p-5 sm:flex-row sm:items-center sm:p-6">
        <p className="text-xs leading-5 text-muted">
          A threshold match is a triage suggestion, never an automatic shortlist or rejection.
        </p>
        <button
          type="button"
          disabled={save.isPending || query.isLoading}
          onClick={() => save.mutate()}
          className="self-start rounded-md bg-brand-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50 sm:self-auto"
        >
          {save.isPending ? "Saving…" : "Save triage policy"}
        </button>
      </div>
      {(query.isError || save.isError) && (
        <p role="alert" className="px-5 pb-5 text-xs text-red-700 sm:px-6">
          {query.error?.message ?? save.error?.message}
        </p>
      )}
    </CollapsibleSection>
  );
}

function PolicyCheckbox({
  checked,
  onChange,
  title,
  description,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  title: string;
  description: string;
}) {
  return (
    <label className="flex items-start gap-3 rounded-xl border border-line p-4 text-sm text-ink">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>
        <span className="font-semibold">{title}</span>
        <span className="mt-1 block text-xs leading-5 text-muted">{description}</span>
      </span>
    </label>
  );
}
