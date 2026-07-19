"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  createJob,
  deleteJob,
  exportComparisons,
  getComparison,
  getJobOverview,
  getJobs,
  updateJob,
} from "@/lib/api";
import type {
  ComparisonHistoryItem,
  ProviderSession,
  RecruiterStatus,
  StoredJob,
} from "@/types/comparison";
import { AnalysisExportControls } from "./analysis-export-controls";
import { CollapsibleSection } from "./collapsible-section";
import { ComparisonEvidence } from "./comparison-evidence";
import { JobScorecardEditor } from "./job-scorecard";
import { JobTalentFinder } from "./job-talent-finder";
import { JobTriagePolicyEditor } from "./job-triage-policy";
import { RecruiterActionPanel } from "./recruiter-action-panel";

function formatDate(value: string | null) {
  if (!value) return "No analysis yet";
  return new Date(value).toLocaleString();
}

type JobSortOption =
  "last_activity_desc" | "last_activity_asc" | "created_desc" | "created_asc";

function lastActivityTimestamp(job: StoredJob) {
  return Math.max(
    new Date(job.updated_at).getTime(),
    job.last_analysis_at ? new Date(job.last_analysis_at).getTime() : 0,
  );
}

function lastActivityDate(job: StoredJob) {
  return new Date(lastActivityTimestamp(job)).toISOString();
}

function compareJobs(left: StoredJob, right: StoredJob, sort: JobSortOption) {
  const leftTimestamp = sort.startsWith("created")
    ? new Date(left.created_at).getTime()
    : lastActivityTimestamp(left);
  const rightTimestamp = sort.startsWith("created")
    ? new Date(right.created_at).getTime()
    : lastActivityTimestamp(right);
  return sort.endsWith("desc")
    ? rightTimestamp - leftTimestamp
    : leftTimestamp - rightTimestamp;
}

function label(value: string | null) {
  return value?.replaceAll("_", " ") ?? "Not available";
}

function ComparisonRow({
  item,
  selected,
  selectedForExport,
  exportSelectionFull,
  onViewEvidence,
  onToggleExport,
}: {
  item: ComparisonHistoryItem;
  selected: boolean;
  selectedForExport: boolean;
  exportSelectionFull: boolean;
  onViewEvidence: () => void;
  onToggleExport: () => void;
}) {
  const [exportError, setExportError] = useState<string>();

  async function downloadReport() {
    setExportError(undefined);
    try {
      const blob = await exportComparisons("report", [item.id]);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "talentmatch-report.pdf";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(
        error instanceof Error
          ? error.message
          : "The report could not be exported.",
      );
    }
  }

  return (
    <article
      className={`rounded-xl border p-4 ${selected ? "border-brand-500 bg-brand-50/40" : "border-line"}`}
    >
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h4 className="font-semibold text-ink">
            {item.candidate_display_name}
          </h4>
          <p className="mt-1 text-xs text-muted">
            Analysed {new Date(item.created_at).toLocaleString()} ·{" "}
            {item.provider} / {item.model}
            {item.scorecard_version
              ? ` · Scorecard v${item.scorecard_version}`
              : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-line px-3 py-2 font-semibold text-ink">
            <input
              type="checkbox"
              aria-label={`Select ${item.candidate_display_name} analysis for export`}
              checked={selectedForExport}
              disabled={!selectedForExport && exportSelectionFull}
              onChange={onToggleExport}
              className="h-4 w-4 accent-brand-600"
            />
            Export
          </label>
          <span className="rounded-full border border-line px-2.5 py-1">
            Fit {item.fit_score ?? "–"}
          </span>
          <span className="rounded-full border border-line px-2.5 py-1">
            Evidence {item.evidence_confidence_score ?? "–"}
          </span>
          <span className="rounded-full border border-line px-2.5 py-1 capitalize">
            Mandatory: {label(item.mandatory_status)}
          </span>
          <span className="rounded-full border border-brand-100 bg-brand-50 px-2.5 py-1 capitalize text-brand-700">
            HR: {label(item.recruiter_status)}
          </span>
          <span className="rounded-full border border-line px-2.5 py-1 capitalize text-muted">
            Triage: {label(item.triage_suggestion)}
          </span>
          <button
            type="button"
            aria-pressed={selected}
            onClick={onViewEvidence}
            className={`rounded-md border px-3 py-2 font-semibold ${selected ? "border-brand-500 bg-brand-600 text-white" : "border-line text-ink"}`}
          >
            {selected ? "Viewing evidence" : "View evidence"}
          </button>
          <button
            type="button"
            onClick={() => void downloadReport()}
            className="rounded-md border border-line px-3 py-2 font-semibold text-ink"
          >
            PDF report
          </button>
        </div>
      </div>
      {exportError && (
        <p role="alert" className="mt-2 text-xs text-red-700">
          {exportError}
        </p>
      )}
    </article>
  );
}

function JobDetail({
  jobId,
  onBack,
  providerSession,
}: {
  jobId: string;
  onBack: () => void;
  providerSession?: ProviderSession;
}) {
  const queryClient = useQueryClient();
  const overview = useQuery({
    queryKey: ["job-overview", jobId],
    queryFn: () => getJobOverview(jobId),
  });
  const [title, setTitle] = useState("");
  const [externalJobId, setExternalJobId] = useState("");
  const [description, setDescription] = useState("");
  const [scorecardStatus, setScorecardStatus] =
    useState<StoredJob["scorecard_status"]>("empty");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [selectedComparisonId, setSelectedComparisonId] = useState<string>();
  const [exportComparisonIds, setExportComparisonIds] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<"all" | RecruiterStatus>(
    "all",
  );
  const selectedComparison = useQuery({
    queryKey: ["comparison", selectedComparisonId],
    queryFn: () => {
      if (!selectedComparisonId) {
        throw new Error("Select a candidate before loading evidence.");
      }
      return getComparison(selectedComparisonId);
    },
    enabled: Boolean(selectedComparisonId),
  });

  useEffect(() => {
    if (overview.data) {
      setTitle(overview.data.job.title);
      setExternalJobId(overview.data.job.external_job_id ?? "");
      setDescription(overview.data.job.raw_text);
      setScorecardStatus(overview.data.job.scorecard_status);
    }
  }, [overview.data]);

  useEffect(() => {
    const availableIds = new Set(
      (overview.data?.comparisons ?? []).map((comparison) => comparison.id),
    );
    setExportComparisonIds((current) =>
      current.filter((comparisonId) => availableIds.has(comparisonId)),
    );
  }, [overview.data?.comparisons]);

  const save = useMutation({
    mutationFn: () =>
      updateJob(jobId, {
        title: title.trim(),
        external_job_id: externalJobId.trim() || null,
        raw_text: description.trim(),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["job-overview", jobId] }),
        queryClient.invalidateQueries({ queryKey: ["job-scorecard", jobId] }),
      ]);
    },
  });
  const remove = useMutation({
    mutationFn: () => deleteJob(jobId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      onBack();
    },
  });

  if (overview.isLoading) return <p aria-live="polite">Loading saved job…</p>;
  if (overview.isError || !overview.data)
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700"
      >
        {overview.error?.message ?? "The saved job could not be loaded."}
      </div>
    );

  const { job, comparisons } = overview.data;
  const visibleComparisons =
    statusFilter === "all"
      ? comparisons
      : comparisons.filter((item) => item.recruiter_status === statusFilter);
  const detailsChanged =
    Boolean(title.trim()) &&
    description.trim().length >= 30 &&
    (title.trim() !== job.title ||
      externalJobId.trim() !== (job.external_job_id ?? "") ||
      description.trim() !== job.raw_text);
  const progressSteps: Array<{
    number: number;
    label: string;
    complete: boolean;
  }> = [
    { number: 1, label: "Job description", complete: true },
    {
      number: 2,
      label: "Scorecard generated",
      complete: scorecardStatus !== "empty",
    },
    {
      number: 3,
      label: "Scorecard approved",
      complete: scorecardStatus === "reviewed",
    },
    { number: 4, label: "Find talent", complete: job.comparison_count > 0 },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <button
          type="button"
          onClick={onBack}
          className="self-start rounded-md border border-line px-3 py-2 text-xs font-semibold"
        >
          ← All jobs
        </button>
        <span className="text-xs font-semibold text-muted">
          Job workspace · Scorecard {scorecardStatus}
        </span>
      </div>

      <ol
        className="grid gap-2 text-xs sm:grid-cols-4"
        aria-label="Job setup progress"
      >
        {progressSteps.map((step) => (
          <li
            key={step.number}
            className={`rounded-lg border p-3 font-semibold ${step.complete ? "border-brand-100 bg-brand-50 text-brand-700" : "border-line bg-white text-muted"}`}
          >
            {step.number}. {step.label}
          </li>
        ))}
      </ol>

      <CollapsibleSection
        title="Job Title"
        description={
          job.external_job_id
            ? `${job.title} · Job ID ${job.external_job_id}`
            : job.title
        }
        status={
          <span className="rounded-full border border-line px-2.5 py-1 text-[11px] font-semibold text-muted">
            {job.candidate_count} candidate(s)
          </span>
        }
      >
        <div className="border-b border-line p-5 sm:p-6">
          <label className="block text-xs font-semibold uppercase tracking-wide text-muted">
            Job title
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={200}
              className="mt-2 w-full rounded-md border border-line px-3 py-2 text-base font-semibold normal-case tracking-normal text-ink"
            />
          </label>
          <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-muted">
            Job ID
            <input
              value={externalJobId}
              onChange={(event) => setExternalJobId(event.target.value)}
              maxLength={100}
              placeholder="Company requisition ID, for example ENG-1042"
              className="mt-2 w-full rounded-md border border-line px-3 py-2 text-sm font-normal normal-case tracking-normal text-ink"
            />
          </label>
          <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-muted">
            Job description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={100000}
              rows={12}
              className="mt-2 w-full resize-y rounded-xl border border-line px-4 py-3 font-sans text-sm font-normal normal-case leading-6 tracking-normal text-ink"
            />
          </label>
          <div className="mt-3 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
            <p className="text-xs leading-5 text-muted">
              Changing the description creates a draft scorecard that must be
              regenerated and approved.
            </p>
            <button
              type="button"
              disabled={!detailsChanged || save.isPending}
              onClick={() => save.mutate()}
              className="shrink-0 rounded-md border border-line px-4 py-2 text-xs font-semibold disabled:opacity-50"
            >
              {save.isPending ? "Saving…" : "Save job details"}
            </button>
          </div>
          {save.isError && (
            <p role="alert" className="mt-2 text-xs text-red-700">
              {save.error.message}
            </p>
          )}
        </div>
        <dl className="grid gap-4 p-5 text-sm sm:grid-cols-3 sm:p-6">
          <div>
            <dt className="text-xs text-muted">Candidates analysed</dt>
            <dd className="mt-1 text-2xl font-semibold text-ink">
              {job.candidate_count}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Completed comparisons</dt>
            <dd className="mt-1 text-2xl font-semibold text-ink">
              {job.comparison_count}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Last analysis</dt>
            <dd className="mt-1 font-semibold text-ink">
              {formatDate(job.last_analysis_at)}
            </dd>
          </div>
        </dl>
      </CollapsibleSection>

      <JobScorecardEditor
        jobId={jobId}
        providerSession={providerSession}
        onScorecardChange={setScorecardStatus}
      />

      <JobTriagePolicyEditor jobId={jobId} />

      <JobTalentFinder
        job={job}
        providerSession={providerSession}
        scorecardStatus={scorecardStatus}
        onViewEvidence={(result) => {
          queryClient.setQueryData(
            ["comparison", result.comparison_id],
            result,
          );
          setSelectedComparisonId(result.comparison_id);
        }}
      />

      <CollapsibleSection
        title="Candidate Analyses"
        description="Review chronological results and open each candidate’s supporting evidence."
        status={
          <span className="text-xs font-semibold text-muted">
            {comparisons.length} result(s)
          </span>
        }
      >
        <div className="flex flex-col justify-between gap-4 border-b border-line p-5 sm:flex-row sm:items-end sm:p-6">
          <label className="block w-full max-w-xs text-xs font-semibold text-muted">
            Filter by HR status
            <select
              aria-label="Filter candidate analyses by HR status"
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value as "all" | RecruiterStatus)
              }
              className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal capitalize text-ink"
            >
              <option value="all">All statuses</option>
              {[
                "new",
                "under_review",
                "needs_clarification",
                "shortlisted",
                "interview_planned",
                "interview_completed",
                "on_hold",
                "talent_pool",
                "not_progressing",
                "withdrawn",
                "offer",
                "hired",
              ].map((status) => (
                <option key={status} value={status}>
                  {label(status)}
                </option>
              ))}
            </select>
          </label>
          <AnalysisExportControls
            comparisonIds={exportComparisonIds}
            filenamePrefix={`talentmatch-job-${job.external_job_id ?? job.title}`}
          />
        </div>
        <div className="space-y-3 p-5 sm:p-6">
          {visibleComparisons.length ? (
            visibleComparisons.map((item) => (
              <ComparisonRow
                key={item.id}
                item={item}
                selected={selectedComparisonId === item.id}
                selectedForExport={exportComparisonIds.includes(item.id)}
                exportSelectionFull={exportComparisonIds.length >= 5}
                onViewEvidence={() => setSelectedComparisonId(item.id)}
                onToggleExport={() =>
                  setExportComparisonIds((current) =>
                    current.includes(item.id)
                      ? current.filter(
                          (comparisonId) => comparisonId !== item.id,
                        )
                      : [...current, item.id],
                  )
                }
              />
            ))
          ) : (
            <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted">
              {comparisons.length
                ? "No candidate analyses match the selected HR status."
                : "No candidates have been analysed for this saved job yet."}
            </p>
          )}
        </div>
        <div className="px-5 pb-5 sm:px-6 sm:pb-6">
          {selectedComparison.isLoading && (
            <p
              aria-live="polite"
              className="rounded-xl border border-line bg-white p-4 text-sm text-muted"
            >
              Loading candidate evidence…
            </p>
          )}
          {selectedComparison.isError && (
            <p
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
            >
              {selectedComparison.error.message}
            </p>
          )}
          {selectedComparison.data && (
            <>
              <RecruiterActionPanel
                comparisonId={selectedComparison.data.comparison_id}
                jobId={jobId}
              />
              <ComparisonEvidence result={selectedComparison.data} />
            </>
          )}
        </div>
      </CollapsibleSection>

      <section className="rounded-2xl border border-red-200 bg-white p-5 sm:p-6">
        <h3 className="font-semibold text-red-700">Delete saved job</h3>
        <p className="mt-1 text-xs leading-5 text-muted">
          Deleting this job also removes its saved comparison results. Candidate
          records are retained.
        </p>
        {!confirmDelete ? (
          <button
            type="button"
            onClick={() => setConfirmDelete(true)}
            className="mt-3 rounded-md border border-red-200 px-3 py-2 text-xs font-semibold text-red-700"
          >
            Delete job…
          </button>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={remove.isPending}
              onClick={() => remove.mutate()}
              className="rounded-md bg-red-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
            >
              Confirm delete
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(false)}
              className="rounded-md border border-line px-3 py-2 text-xs font-semibold"
            >
              Cancel
            </button>
          </div>
        )}
        {remove.isError && (
          <p role="alert" className="mt-2 text-xs text-red-700">
            {remove.error.message}
          </p>
        )}
      </section>
    </div>
  );
}

function NewJobForm({
  onCancel,
  onCreated,
}: {
  onCancel: () => void;
  onCreated: (jobId: string) => void;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [externalJobId, setExternalJobId] = useState("");
  const [description, setDescription] = useState("");
  const [validationError, setValidationError] = useState<string>();
  const create = useMutation({
    mutationFn: () =>
      createJob({
        title: title.trim(),
        external_job_id: externalJobId.trim() || undefined,
        raw_text: description.trim(),
      }),
    onSuccess: async (job) => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      onCreated(job.id);
    },
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!title.trim()) {
      setValidationError("Add a job title.");
      return;
    }
    if (description.trim().length < 30) {
      setValidationError("Add at least 30 characters of job-description text.");
      return;
    }
    setValidationError(undefined);
    create.mutate();
  }

  return (
    <form
      onSubmit={submit}
      noValidate
      className="rounded-2xl border border-line bg-white shadow-card"
    >
      <div className="flex flex-col justify-between gap-3 border-b border-line p-5 sm:flex-row sm:items-center sm:p-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            New job
          </p>
          <h2 className="mt-1 text-lg font-semibold text-ink">
            Create a hiring workspace
          </h2>
          <p className="mt-1 text-sm text-muted">
            Start with the role. Requirements and candidates are added after it
            is saved.
          </p>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="self-start rounded-md border border-line px-3 py-2 text-xs font-semibold"
        >
          Cancel
        </button>
      </div>
      <div className="space-y-4 p-5 sm:p-6">
        <label className="block text-xs font-semibold text-muted">
          Job title
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={200}
            placeholder="Senior AI Engineer"
            className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm font-normal text-ink"
          />
        </label>
        <label className="block text-xs font-semibold text-muted">
          Job ID <span className="font-normal">(optional)</span>
          <input
            value={externalJobId}
            onChange={(event) => setExternalJobId(event.target.value)}
            maxLength={100}
            placeholder="Company requisition ID, for example ENG-1042"
            className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm font-normal text-ink"
          />
        </label>
        <label className="block text-xs font-semibold text-muted">
          Job description
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            maxLength={100000}
            rows={14}
            placeholder="Paste the responsibilities, required experience, and preferred qualifications…"
            className="mt-1 w-full resize-y rounded-xl border border-line px-4 py-3 text-sm font-normal leading-6 text-ink"
          />
        </label>
        {(validationError || create.isError) && (
          <p role="alert" className="text-sm text-red-700">
            {validationError ?? create.error?.message}
          </p>
        )}
      </div>
      <div className="flex justify-end border-t border-line bg-canvas/40 p-5 sm:p-6">
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          {create.isPending ? "Creating job…" : "Create job and continue"}
        </button>
      </div>
    </form>
  );
}

export function JobsWorkspace({
  providerSession,
  startWithNewJob = false,
}: {
  providerSession?: ProviderSession;
  startWithNewJob?: boolean;
}) {
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: getJobs });
  const [selectedJobId, setSelectedJobId] = useState<string>();
  const [creatingJob, setCreatingJob] = useState(startWithNewJob);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<JobSortOption>("last_activity_desc");
  const visibleJobs = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    const matches = query
      ? (jobs.data ?? []).filter((job) =>
          `${job.title}\n${job.external_job_id ?? ""}`
            .toLocaleLowerCase()
            .includes(query),
        )
      : (jobs.data ?? []);
    return [...matches].sort((left, right) => compareJobs(left, right, sort));
  }, [jobs.data, search, sort]);

  if (selectedJobId)
    return (
      <JobDetail
        jobId={selectedJobId}
        onBack={() => setSelectedJobId(undefined)}
        providerSession={providerSession}
      />
    );

  if (creatingJob)
    return (
      <NewJobForm
        onCancel={() => setCreatingJob(false)}
        onCreated={(jobId) => {
          setCreatingJob(false);
          setSelectedJobId(jobId);
        }}
      />
    );

  return (
    <section className="rounded-2xl border border-line bg-white shadow-card">
      <div className="grid gap-4 border-b border-line p-5 sm:grid-cols-2 sm:p-6 lg:grid-cols-[minmax(18rem,1fr)_minmax(16rem,24rem)_18rem_auto] lg:items-end">
        <div className="sm:col-span-2 lg:col-span-1 lg:pb-0.5">
          <h2 className="text-lg font-semibold text-ink">Saved jobs</h2>
          <p className="mt-1 text-sm text-muted">
            Reopen a role, review its analyses, or compare more candidates.
          </p>
        </div>
        <label className="block text-xs font-semibold text-muted">
          Search
          <input
            aria-label="Search jobs"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Title or job ID"
            className="mt-1 block w-full rounded-md border border-line px-3 py-2 text-sm font-normal text-ink"
          />
        </label>
        <label className="block text-xs font-semibold text-muted">
          Sort by
          <select
            aria-label="Sort jobs"
            value={sort}
            onChange={(event) => setSort(event.target.value as JobSortOption)}
            className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal text-ink"
          >
            <option value="last_activity_desc">
              Last activity — newest first
            </option>
            <option value="last_activity_asc">
              Last activity — oldest first
            </option>
            <option value="created_desc">Created date — newest first</option>
            <option value="created_asc">Created date — oldest first</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => setCreatingJob(true)}
          className="justify-self-start whitespace-nowrap rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white sm:justify-self-end lg:justify-self-auto"
        >
          + New Job
        </button>
      </div>
      <div className="p-5 sm:p-6">
        {jobs.isLoading ? (
          <p aria-live="polite">Loading saved jobs…</p>
        ) : jobs.isError ? (
          <p role="alert" className="text-sm text-red-700">
            {jobs.error.message}
          </p>
        ) : visibleJobs.length ? (
          <ul
            aria-label="Saved jobs"
            className="divide-y divide-line overflow-hidden rounded-xl border border-line"
            role="list"
          >
            {visibleJobs.map((job) => (
              <li
                key={job.id}
                className="flex flex-col gap-4 p-4 lg:flex-row lg:items-center"
              >
                <div className="min-w-0 flex-1">
                  <h3 className="truncate font-semibold text-ink">
                    {job.title}
                  </h3>
                  <p className="mt-1 text-xs text-muted">
                    Job ID: {job.external_job_id ?? "Not provided"}
                  </p>
                </div>
                <div className="lg:w-40">
                  <span className="inline-flex rounded-full border border-line px-2.5 py-1 text-[11px] font-semibold capitalize text-muted">
                    Scorecard: {job.scorecard_status}
                    {job.scorecard_version ? ` v${job.scorecard_version}` : ""}
                  </span>
                </div>
                <div className="text-xs leading-5 text-muted lg:w-56">
                  <p>
                    {job.candidate_count} candidate(s) · {job.comparison_count}{" "}
                    comparison(s)
                  </p>
                  <p>
                    {job.scorecard_requirement_count} included requirement(s)
                  </p>
                </div>
                <div className="text-xs leading-5 text-muted lg:w-64">
                  <p>Created: {formatDate(job.created_at)}</p>
                  <p>Last activity: {formatDate(lastActivityDate(job))}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedJobId(job.id)}
                  className="self-start rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink lg:self-auto"
                >
                  Open job
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">
            {search ? "No saved jobs match your search." : "No saved jobs yet."}
          </p>
        )}
      </div>
    </section>
  );
}
