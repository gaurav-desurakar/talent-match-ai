"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getRecruiterDisposition, updateRecruiterDisposition } from "@/lib/api";
import type { RecruiterReasonCode, RecruiterStatus } from "@/types/comparison";

const STATUSES: RecruiterStatus[] = [
  "new", "under_review", "needs_clarification", "shortlisted",
  "interview_planned", "interview_completed", "on_hold", "talent_pool",
  "not_progressing", "withdrawn", "offer", "hired",
];

const REASONS: RecruiterReasonCode[] = [
  "mandatory_requirement_not_evidenced", "insufficient_relevant_experience",
  "role_alignment_gap", "application_incomplete", "candidate_withdrew",
  "duplicate_application", "position_closed", "other",
];

function label(value: string) {
  return value.replaceAll("_", " ");
}

export function RecruiterActionPanel({
  comparisonId,
  jobId,
}: {
  comparisonId: string;
  jobId: string;
}) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["recruiter-disposition", comparisonId],
    queryFn: () => getRecruiterDisposition(comparisonId),
  });
  const [status, setStatus] = useState<RecruiterStatus>("new");
  const [reason, setReason] = useState<RecruiterReasonCode>();
  const [note, setNote] = useState("");
  const [assignedRecruiter, setAssignedRecruiter] = useState("");

  useEffect(() => {
    if (!query.data) return;
    setStatus(query.data.status);
    setReason(query.data.reason_code ?? undefined);
    setNote(query.data.note ?? "");
    setAssignedRecruiter(query.data.assigned_recruiter ?? "");
  }, [query.data]);

  const save = useMutation({
    mutationFn: () =>
      updateRecruiterDisposition(comparisonId, {
        status,
        reason_code: status === "not_progressing" ? reason : undefined,
        note: note.trim() || undefined,
        assigned_recruiter: assignedRecruiter.trim() || undefined,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["recruiter-disposition", comparisonId],
        }),
        queryClient.invalidateQueries({ queryKey: ["job-overview", jobId] }),
        queryClient.invalidateQueries({ queryKey: ["candidate-overview"] }),
        queryClient.invalidateQueries({ queryKey: ["comparison-history"] }),
      ]);
    },
  });

  const validationError =
    status === "not_progressing" && !reason
      ? "Select a job-related reason."
      : reason === "other" && !note.trim()
        ? "Add a note for the Other reason."
        : undefined;

  function chooseStatus(value: RecruiterStatus) {
    setStatus(value);
    if (value !== "not_progressing") setReason(undefined);
  }

  return (
    <section className="mb-5 rounded-2xl border border-brand-100 bg-brand-50/40 p-5 sm:p-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            Recruiter action
          </p>
          <h4 className="mt-1 text-lg font-semibold capitalize text-ink">
            HR status: {label(query.data?.status ?? "new")}
          </h4>
          <p className="mt-1 text-xs leading-5 text-muted">
            System triage suggestion: {label(query.data?.triage_suggestion ?? "loading")}. The suggestion does not change HR status.
          </p>
        </div>
        {query.data && (
          <span className="rounded-full border border-brand-100 bg-white px-3 py-1 text-xs font-semibold text-brand-700">
            Policy v{query.data.triage_policy_version} · Fit {query.data.triage_policy.shortlist_fit_threshold}+ · Evidence {query.data.triage_policy.shortlist_evidence_threshold}+
          </span>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-2" aria-label="Quick recruiter actions">
        {([
          ["shortlisted", "Shortlist"],
          ["needs_clarification", "Needs clarification"],
          ["on_hold", "On hold"],
          ["not_progressing", "Not progressing"],
        ] as Array<[RecruiterStatus, string]>).map(([value, text]) => (
          <button
            key={value}
            type="button"
            onClick={() => chooseStatus(value)}
            className={`rounded-md border px-3 py-2 text-xs font-semibold ${status === value ? "border-brand-600 bg-brand-600 text-white" : "border-line bg-white text-ink"}`}
          >
            {text}
          </button>
        ))}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="text-xs font-semibold text-muted">
          HR status
          <select
            value={status}
            onChange={(event) => chooseStatus(event.target.value as RecruiterStatus)}
            className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal capitalize text-ink"
          >
            {STATUSES.map((value) => (
              <option key={value} value={value}>{label(value)}</option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold text-muted">
          Assigned recruiter
          <input
            value={assignedRecruiter}
            onChange={(event) => setAssignedRecruiter(event.target.value)}
            maxLength={200}
            placeholder="Name or team"
            className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal text-ink"
          />
        </label>
        {status === "not_progressing" && (
          <label className="text-xs font-semibold text-muted sm:col-span-2">
            Job-related reason
            <select
              value={reason ?? ""}
              onChange={(event) => setReason(event.target.value as RecruiterReasonCode)}
              className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal capitalize text-ink"
            >
              <option value="">Select a reason</option>
              {REASONS.map((value) => (
                <option key={value} value={value}>{label(value)}</option>
              ))}
            </select>
          </label>
        )}
        <label className="text-xs font-semibold text-muted sm:col-span-2">
          Recruiter note
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            maxLength={2000}
            rows={3}
            placeholder="Record job-related context for the next reviewer. Notes never affect scoring."
            className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal leading-6 text-ink"
          />
        </label>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-xs text-muted">No status is applied automatically.</p>
        <button
          type="button"
          disabled={Boolean(validationError) || save.isPending || query.isLoading}
          onClick={() => save.mutate()}
          className="rounded-md bg-brand-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          {save.isPending ? "Saving…" : "Save recruiter action"}
        </button>
      </div>
      {(validationError || query.isError || save.isError) && (
        <p role="alert" className="mt-2 text-xs text-red-700">
          {validationError ?? query.error?.message ?? save.error?.message}
        </p>
      )}

      {query.data?.events.length ? (
        <div className="mt-5 border-t border-brand-100 pt-4">
          <h5 className="text-sm font-semibold text-ink">Status history</h5>
          <ol className="mt-3 space-y-3">
            {query.data.events.map((event) => (
              <li key={event.id} className="rounded-lg border border-line bg-white p-3 text-xs">
                <p className="font-semibold capitalize text-ink">
                  {event.previous_status ? `${label(event.previous_status)} → ` : ""}{label(event.status)}
                </p>
                <p className="mt-1 text-muted">
                  {new Date(event.created_at).toLocaleString()} · Policy v{event.triage_policy_version} · Suggestion {label(event.triage_suggestion)}
                </p>
                {event.reason_code && <p className="mt-1 capitalize text-muted">Reason: {label(event.reason_code)}</p>}
                {event.note && <p className="mt-2 leading-5 text-ink">{event.note}</p>}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  );
}
