"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  addCandidateResume,
  createBackgroundComparison,
  deleteCandidate,
  exportComparisons,
  getCandidateOverview,
  getCandidates,
  getComparison,
  getJobs,
  uploadDocument,
} from "@/lib/api";
import type {
  AnalysisJob,
  ComparisonHistoryItem,
  DocumentSourceReference,
  ProviderSession,
  ResumeVersion,
  StoredCandidate,
} from "@/types/comparison";
import { AnalysisExportControls } from "./analysis-export-controls";
import { CollapsibleSection } from "./collapsible-section";
import { ComparisonEvidence } from "./comparison-evidence";

type CandidateSort = "activity_desc" | "added_desc" | "name_asc";
type CandidateFilter = "all" | "analysed" | "not_analysed";

function formatDate(value: string | null, fallback = "Not available") {
  return value ? new Date(value).toLocaleString() : fallback;
}

function candidateActivity(candidate: StoredCandidate) {
  return Math.max(
    new Date(candidate.updated_at).getTime(),
    candidate.latest_resume_at
      ? new Date(candidate.latest_resume_at).getTime()
      : 0,
    candidate.last_analysis_at
      ? new Date(candidate.last_analysis_at).getTime()
      : 0,
  );
}

function storedSourceReferences(
  resume: ResumeVersion,
): DocumentSourceReference[] {
  const references = resume.parsed_content.source_references;
  if (!Array.isArray(references)) return [];
  return references.filter(
    (reference): reference is DocumentSourceReference =>
      typeof reference === "object" &&
      reference !== null &&
      typeof (reference as { id?: unknown }).id === "string" &&
      typeof (reference as { text?: unknown }).text === "string",
  );
}

function CandidateList({ onOpen }: { onOpen: (candidateId: string) => void }) {
  const candidates = useQuery({
    queryKey: ["candidates"],
    queryFn: getCandidates,
  });
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<CandidateFilter>("all");
  const [sort, setSort] = useState<CandidateSort>("activity_desc");
  const visibleCandidates = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return [...(candidates.data ?? [])]
      .filter((candidate) =>
        query
          ? candidate.display_name.toLocaleLowerCase().includes(query)
          : true,
      )
      .filter((candidate) => {
        if (filter === "analysed") return candidate.comparison_count > 0;
        if (filter === "not_analysed") return candidate.comparison_count === 0;
        return true;
      })
      .sort((left, right) => {
        if (sort === "name_asc")
          return left.display_name.localeCompare(right.display_name);
        if (sort === "added_desc")
          return (
            new Date(right.created_at).getTime() -
            new Date(left.created_at).getTime()
          );
        return candidateActivity(right) - candidateActivity(left);
      });
  }, [candidates.data, filter, search, sort]);

  return (
    <section className="rounded-2xl border border-line bg-white shadow-card">
      <div className="grid gap-4 border-b border-line p-5 sm:grid-cols-2 sm:p-6 lg:grid-cols-[minmax(18rem,1fr)_minmax(14rem,22rem)_14rem_16rem] lg:items-end">
        <div className="sm:col-span-2 lg:col-span-1 lg:pb-0.5">
          <h2 className="text-lg font-semibold text-ink">Candidate pool</h2>
          <p className="mt-1 text-sm text-muted">
            Reuse resumes and review each candidate across roles.
          </p>
        </div>
        <label className="block text-xs font-semibold text-muted">
          Search
          <input
            aria-label="Search candidates"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Candidate name"
            className="mt-1 block w-full rounded-md border border-line px-3 py-2 text-sm font-normal text-ink"
          />
        </label>
        <label className="block text-xs font-semibold text-muted">
          Filter
          <select
            aria-label="Filter candidates"
            value={filter}
            onChange={(event) =>
              setFilter(event.target.value as CandidateFilter)
            }
            className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal text-ink"
          >
            <option value="all">All candidates</option>
            <option value="analysed">Previously analysed</option>
            <option value="not_analysed">Not yet analysed</option>
          </select>
        </label>
        <label className="block text-xs font-semibold text-muted">
          Sort by
          <select
            aria-label="Sort candidates"
            value={sort}
            onChange={(event) => setSort(event.target.value as CandidateSort)}
            className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal text-ink"
          >
            <option value="activity_desc">Last activity</option>
            <option value="added_desc">Recently added</option>
            <option value="name_asc">Candidate name</option>
          </select>
        </label>
      </div>
      <div className="p-5 sm:p-6">
        {candidates.isLoading ? (
          <p aria-live="polite">Loading candidates…</p>
        ) : candidates.isError ? (
          <p role="alert" className="text-sm text-red-700">
            {candidates.error.message}
          </p>
        ) : visibleCandidates.length ? (
          <ul
            aria-label="Saved candidates"
            className="divide-y divide-line overflow-hidden rounded-xl border border-line"
          >
            {visibleCandidates.map((candidate) => (
              <li
                key={candidate.id}
                className="flex flex-col gap-4 p-4 lg:flex-row lg:items-center"
              >
                <div className="min-w-0 flex-1">
                  <h3 className="truncate font-semibold text-ink">
                    {candidate.display_name}
                  </h3>
                  <p className="mt-1 text-xs text-muted">
                    Added {formatDate(candidate.created_at)}
                  </p>
                </div>
                <div className="text-xs leading-5 text-muted lg:w-44">
                  <p>{candidate.resume_count} resume version(s)</p>
                  <p>{candidate.job_count} role(s)</p>
                </div>
                <div className="text-xs leading-5 text-muted lg:w-52">
                  <p>{candidate.comparison_count} comparison(s)</p>
                  <p>
                    Last analysis:{" "}
                    {formatDate(candidate.last_analysis_at, "None")}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onOpen(candidate.id)}
                  className="self-start rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink lg:self-auto"
                >
                  Open candidate
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">
            {search || filter !== "all"
              ? "No candidates match the current search and filter."
              : "No saved candidates yet."}
          </p>
        )}
      </div>
    </section>
  );
}

function CandidateHistoryRow({
  item,
  selected,
  selectedForExport,
  exportSelectionFull,
  onView,
  onToggleExport,
}: {
  item: ComparisonHistoryItem;
  selected: boolean;
  selectedForExport: boolean;
  exportSelectionFull: boolean;
  onView: () => void;
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
      anchor.download = "talentmatch-candidate-report.pdf";
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
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h4 className="font-semibold text-ink">{item.job_title}</h4>
          <p className="mt-1 text-xs text-muted">
            Analysed {formatDate(item.created_at)} · {item.provider} /{" "}
            {item.model}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-line px-3 py-2 font-semibold text-ink">
            <input
              type="checkbox"
              aria-label={`Select ${item.job_title} analysis for export`}
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
          <span className="rounded-full border border-brand-100 bg-brand-50 px-2.5 py-1 capitalize text-brand-700">
            HR: {item.recruiter_status.replaceAll("_", " ")}
          </span>
          <span className="rounded-full border border-line px-2.5 py-1 capitalize text-muted">
            Triage: {item.triage_suggestion.replaceAll("_", " ")}
          </span>
          <button
            type="button"
            aria-pressed={selected}
            onClick={onView}
            className="rounded-md border border-line px-3 py-2 font-semibold"
          >
            {selected ? "Viewing evidence" : "View evidence"}
          </button>
          <button
            type="button"
            onClick={() => void downloadReport()}
            className="rounded-md border border-line px-3 py-2 font-semibold"
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

function CandidateDetail({
  candidateId,
  providerSession,
  onBack,
}: {
  candidateId: string;
  providerSession?: ProviderSession;
  onBack: () => void;
}) {
  const queryClient = useQueryClient();
  const overview = useQuery({
    queryKey: ["candidate-overview", candidateId],
    queryFn: () => getCandidateOverview(candidateId),
  });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: getJobs });
  const [selectedResumeId, setSelectedResumeId] = useState("");
  const [selectedJobId, setSelectedJobId] = useState("");
  const [privacyConfirmed, setPrivacyConfirmed] = useState(false);
  const [blindReview, setBlindReview] = useState(false);
  const [progress, setProgress] = useState<AnalysisJob>();
  const [selectedComparisonId, setSelectedComparisonId] = useState<string>();
  const [exportComparisonIds, setExportComparisonIds] = useState<string[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const selectedComparison = useQuery({
    queryKey: ["comparison", selectedComparisonId],
    queryFn: () => {
      if (!selectedComparisonId) throw new Error("Select a comparison first.");
      return getComparison(selectedComparisonId);
    },
    enabled: Boolean(selectedComparisonId),
  });
  const approvedJobs = (jobs.data ?? []).filter(
    (job) => job.scorecard_status === "reviewed",
  );
  const candidate = overview.data?.candidate;
  const resumes = useMemo(
    () =>
      [...(candidate?.resumes ?? [])].sort(
        (left, right) =>
          new Date(right.created_at).getTime() -
          new Date(left.created_at).getTime(),
      ),
    [candidate?.resumes],
  );

  useEffect(() => {
    if (!selectedResumeId && resumes[0]) setSelectedResumeId(resumes[0].id);
  }, [resumes, selectedResumeId]);
  useEffect(() => {
    if (!selectedJobId && approvedJobs[0]) setSelectedJobId(approvedJobs[0].id);
  }, [approvedJobs, selectedJobId]);
  useEffect(() => {
    const availableIds = new Set(
      (overview.data?.comparisons ?? []).map((comparison) => comparison.id),
    );
    setExportComparisonIds((current) =>
      current.filter((comparisonId) => availableIds.has(comparisonId)),
    );
  }, [overview.data?.comparisons]);

  const uploadResume = useMutation({
    mutationFn: async (file: File) => {
      const extraction = await uploadDocument(file, "resume");
      return addCandidateResume(candidateId, {
        raw_text: extraction.raw_text,
        parsed_content: {
          source_references: extraction.source_references,
          sections: extraction.sections,
          extraction_confidence: extraction.extraction_confidence,
        },
        source_file: extraction.filename,
        sha256: extraction.sha256,
        extraction_warnings: extraction.warnings,
      });
    },
    onSuccess: async (resume) => {
      setSelectedResumeId(resume.id);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["candidates"] }),
        queryClient.invalidateQueries({
          queryKey: ["candidate-overview", candidateId],
        }),
      ]);
    },
  });
  const analysis = useMutation({
    mutationFn: async () => {
      if (!candidate) throw new Error("The candidate is unavailable.");
      const resume = resumes.find((item) => item.id === selectedResumeId);
      const job = approvedJobs.find((item) => item.id === selectedJobId);
      if (!resume) throw new Error("Select a resume version.");
      if (!job) throw new Error("Select a job with an approved scorecard.");
      return createBackgroundComparison(
        {
          job_id: job.id,
          job_title: job.title,
          job_description_text: job.raw_text,
          provider: providerSession?.provider ?? "mock",
          credential_session_id: providerSession?.session_id,
          blind_review: blindReview,
          candidates: [
            {
              candidate_id: candidate.id,
              display_name: candidate.display_name,
              stored_candidate_id: candidate.id,
              resume_id: resume.id,
              resume_text: resume.raw_text,
              resume_source_references: storedSourceReferences(resume),
            },
          ],
        },
        setProgress,
      );
    },
    onSuccess: async (batch) => {
      const result = batch.comparisons[0]?.comparison;
      if (result) {
        queryClient.setQueryData(["comparison", result.comparison_id], result);
        setSelectedComparisonId(result.comparison_id);
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["candidates"] }),
        queryClient.invalidateQueries({
          queryKey: ["candidate-overview", candidateId],
        }),
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["comparisons"] }),
      ]);
    },
  });
  const remove = useMutation({
    mutationFn: () => deleteCandidate(candidateId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["candidates"] }),
        queryClient.invalidateQueries({ queryKey: ["comparisons"] }),
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
      ]);
      onBack();
    },
  });

  if (overview.isLoading) return <p aria-live="polite">Loading candidate…</p>;
  if (overview.isError || !overview.data)
    return (
      <p
        role="alert"
        className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700"
      >
        {overview.error?.message ?? "The candidate could not be loaded."}
      </p>
    );

  const { candidate: loadedCandidate, summary, comparisons } = overview.data;

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <button
          type="button"
          onClick={onBack}
          className="self-start rounded-md border border-line px-3 py-2 text-xs font-semibold"
        >
          ← All candidates
        </button>
        <span className="text-xs font-semibold text-muted">
          Candidate workspace
        </span>
      </div>

      <section className="rounded-2xl border border-line bg-white p-5 shadow-card sm:p-6">
        <h2 className="text-xl font-semibold text-ink">
          {loadedCandidate.display_name}
        </h2>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs text-muted">Resume versions</dt>
            <dd className="mt-1 text-xl font-semibold">
              {summary.resume_count}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Roles reviewed</dt>
            <dd className="mt-1 text-xl font-semibold">{summary.job_count}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Comparisons</dt>
            <dd className="mt-1 text-xl font-semibold">
              {summary.comparison_count}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Last analysis</dt>
            <dd className="mt-1 font-semibold">
              {formatDate(summary.last_analysis_at, "None")}
            </dd>
          </div>
        </dl>
      </section>

      <CollapsibleSection
        title="Resume Versions"
        description="Retain prior resume text while adding updated versions."
        status={
          <span className="text-xs font-semibold text-muted">
            {resumes.length} version(s)
          </span>
        }
      >
        <div className="border-b border-line p-5 sm:p-6">
          <label className="inline-flex cursor-pointer rounded-md border border-line px-3 py-2 text-xs font-semibold">
            {uploadResume.isPending
              ? "Extracting and saving…"
              : "+ Upload resume version"}
            <input
              aria-label="Upload new resume version"
              type="file"
              accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              className="sr-only"
              disabled={uploadResume.isPending}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) uploadResume.mutate(file);
                event.target.value = "";
              }}
            />
          </label>
          {uploadResume.isError && (
            <p role="alert" className="mt-2 text-xs text-red-700">
              {uploadResume.error.message}
            </p>
          )}
        </div>
        <div className="space-y-3 p-5 sm:p-6">
          {resumes.map((resume, index) => (
            <article
              key={resume.id}
              className="rounded-xl border border-line p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h4 className="font-semibold text-ink">
                    {resume.source_file ??
                      `Resume version ${resumes.length - index}`}
                  </h4>
                  <p className="mt-1 text-xs text-muted">
                    Saved {formatDate(resume.created_at)}
                  </p>
                </div>
                {index === 0 && (
                  <span className="rounded-full border border-brand-100 bg-brand-50 px-2.5 py-1 text-[11px] font-semibold text-brand-700">
                    Latest
                  </span>
                )}
              </div>
              <details className="mt-3">
                <summary className="cursor-pointer text-xs font-semibold text-brand-700">
                  Preview extracted text
                </summary>
                <p className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap rounded-lg bg-canvas/60 p-3 text-xs leading-5 text-ink">
                  {resume.raw_text}
                </p>
              </details>
              {resume.extraction_warnings.map((warning, warningIndex) => (
                <p
                  key={`${resume.id}-warning-${warningIndex}`}
                  className="mt-2 text-xs text-amber"
                >
                  {warning}
                </p>
              ))}
            </article>
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="Compare With a Job"
        description="Reuse a saved resume against a recruiter-approved scorecard."
      >
        <div className="grid gap-4 p-5 sm:p-6 lg:grid-cols-2">
          <label className="text-xs font-semibold text-muted">
            Resume version
            <select
              value={selectedResumeId}
              onChange={(event) => setSelectedResumeId(event.target.value)}
              className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal text-ink"
            >
              {resumes.map((resume, index) => (
                <option key={resume.id} value={resume.id}>
                  {resume.source_file ??
                    `Resume version ${resumes.length - index}`}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-muted">
            Approved job
            <select
              value={selectedJobId}
              onChange={(event) => setSelectedJobId(event.target.value)}
              className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-normal text-ink"
            >
              {!approvedJobs.length && (
                <option value="">No approved jobs available</option>
              )}
              {approvedJobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                  {job.external_job_id ? ` (${job.external_job_id})` : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line p-4 text-sm">
            <input
              type="checkbox"
              checked={blindReview}
              onChange={(event) => setBlindReview(event.target.checked)}
              className="mt-0.5 h-4 w-4 accent-brand-600"
            />
            <span>
              <strong className="block text-ink">Blind-review display</strong>
              <span className="text-xs text-muted">
                Use a neutral candidate label in the new result.
              </span>
            </span>
          </label>
          <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line p-4 text-sm">
            <input
              type="checkbox"
              checked={privacyConfirmed}
              onChange={(event) => setPrivacyConfirmed(event.target.checked)}
              className="mt-0.5 h-4 w-4 accent-brand-600"
            />
            <span>
              <strong className="block text-ink">Approve this analysis</strong>
              <span className="text-xs text-muted">
                The selected job and resume will be sent to{" "}
                {providerSession?.provider ?? "mock"}.
              </span>
            </span>
          </label>
        </div>
        <div className="flex flex-col items-end gap-2 border-t border-line p-5 sm:p-6">
          {progress && (
            <p aria-live="polite" className="text-xs text-muted">
              {progress.latest_event?.label ?? `Analysis ${progress.status}`}
            </p>
          )}
          <button
            type="button"
            disabled={
              !selectedResumeId ||
              !selectedJobId ||
              !privacyConfirmed ||
              analysis.isPending
            }
            onClick={() => analysis.mutate()}
            className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {analysis.isPending ? "Comparing…" : "Compare candidate"}
          </button>
          {analysis.isError && (
            <p role="alert" className="text-xs text-red-700">
              {analysis.error.message}
            </p>
          )}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="Role History and Evidence"
        description="Review chronological comparisons without turning them into an automatic ranking."
        status={
          <span className="text-xs font-semibold text-muted">
            {comparisons.length} result(s)
          </span>
        }
      >
        <div className="flex flex-col justify-between gap-3 border-b border-line p-5 sm:flex-row sm:items-end sm:p-6">
          <p className="max-w-xl text-xs leading-5 text-muted">
            Select up to five role analyses to create a candidate history
            export.
          </p>
          <AnalysisExportControls
            comparisonIds={exportComparisonIds}
            filenamePrefix={`talentmatch-candidate-${loadedCandidate.display_name}`}
          />
        </div>
        <div className="space-y-3 p-5 sm:p-6">
          {comparisons.length ? (
            comparisons.map((item) => (
              <CandidateHistoryRow
                key={item.id}
                item={item}
                selected={selectedComparisonId === item.id}
                selectedForExport={exportComparisonIds.includes(item.id)}
                exportSelectionFull={exportComparisonIds.length >= 5}
                onView={() => setSelectedComparisonId(item.id)}
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
              This candidate has not been compared with a role yet.
            </p>
          )}
        </div>
        <div className="px-5 pb-5 sm:px-6 sm:pb-6">
          {selectedComparison.isLoading && (
            <p aria-live="polite" className="text-sm text-muted">
              Loading evidence…
            </p>
          )}
          {selectedComparison.isError && (
            <p role="alert" className="text-sm text-red-700">
              {selectedComparison.error.message}
            </p>
          )}
          {selectedComparison.data && (
            <ComparisonEvidence result={selectedComparison.data} />
          )}
        </div>
      </CollapsibleSection>

      <section className="rounded-2xl border border-red-200 bg-white p-5 sm:p-6">
        <h3 className="font-semibold text-red-700">Delete candidate data</h3>
        <p className="mt-1 text-xs leading-5 text-muted">
          Deletes this candidate, all saved resume versions, and linked
          comparison results. Saved jobs are retained.
        </p>
        {!confirmDelete ? (
          <button
            type="button"
            onClick={() => setConfirmDelete(true)}
            className="mt-3 rounded-md border border-red-200 px-3 py-2 text-xs font-semibold text-red-700"
          >
            Delete candidate…
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

export function CandidatesWorkspace({
  providerSession,
}: {
  providerSession?: ProviderSession;
}) {
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>();
  return selectedCandidateId ? (
    <CandidateDetail
      candidateId={selectedCandidateId}
      providerSession={providerSession}
      onBack={() => setSelectedCandidateId(undefined)}
    />
  ) : (
    <CandidateList onOpen={setSelectedCandidateId} />
  );
}
