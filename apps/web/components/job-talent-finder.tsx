"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { createBackgroundComparison } from "@/lib/api";
import type {
  AnalysisJob,
  BatchComparisonResult,
  ComparisonResult,
  DocumentExtraction,
  ProviderSession,
  StoredJob,
} from "@/types/comparison";
import { CollapsibleSection } from "./collapsible-section";
import { DocumentInput } from "./document-input";
import { Icon } from "./icons";
import { MultiResumeUpload } from "./multi-resume-upload";

interface CandidateDraft {
  id: string;
  displayName: string;
  resume: string;
  extraction?: DocumentExtraction;
}

const MINIMUM_DOCUMENT_LENGTH = 30;

function createBlankCandidate(number: number): CandidateDraft {
  return {
    id: `candidate-${number}`,
    displayName: `Candidate ${number}`,
    resume: "",
  };
}

function normalizedDocument(value: string) {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

function resultLabel(value: string) {
  return value.replaceAll("_", " ");
}

export function JobTalentFinder({
  job,
  providerSession,
  scorecardStatus,
  onViewEvidence,
}: {
  job: StoredJob;
  providerSession?: ProviderSession;
  scorecardStatus: StoredJob["scorecard_status"];
  onViewEvidence?: (result: ComparisonResult) => void;
}) {
  const queryClient = useQueryClient();
  const [candidates, setCandidates] = useState<CandidateDraft[]>([
    createBlankCandidate(1),
  ]);
  const [candidateErrors, setCandidateErrors] = useState<
    Record<string, string>
  >({});
  const [privacyConfirmed, setPrivacyConfirmed] = useState(false);
  const [privacyError, setPrivacyError] = useState<string>();
  const [blindReview, setBlindReview] = useState(false);
  const [progress, setProgress] = useState<AnalysisJob>();
  const nextCandidateNumber = useRef(2);
  const analysis = useMutation({
    mutationFn: () =>
      createBackgroundComparison(
        {
          job_id: job.id,
          job_title: job.title,
          job_description_text: job.raw_text,
          provider: providerSession?.provider ?? "mock",
          credential_session_id: providerSession?.session_id,
          blind_review: blindReview,
          candidates: candidates.map((candidate) => ({
            candidate_id: candidate.id,
            display_name: candidate.displayName.trim(),
            resume_text: candidate.resume.trim(),
            resume_source_references: candidate.extraction?.source_references,
          })),
        },
        setProgress,
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["job-overview", job.id] }),
        queryClient.invalidateQueries({ queryKey: ["comparisons"] }),
        queryClient.invalidateQueries({ queryKey: ["candidates"] }),
      ]);
    },
  });

  const populatedCandidates = candidates.filter(
    (candidate) => candidate.resume.trim() || candidate.extraction,
  );
  const existingHashes = new Set(
    candidates
      .map((candidate) => candidate.extraction?.sha256)
      .filter((hash): hash is string => Boolean(hash)),
  );
  const duplicateIds = duplicateCandidateIds(candidates, job.raw_text);
  const scorecardApproved = scorecardStatus === "reviewed";

  function candidateFromExtraction(
    extraction: DocumentExtraction,
    id = `candidate-${nextCandidateNumber.current++}`,
  ): CandidateDraft {
    const firstLine = extraction.raw_text.split("\n")[0]?.trim();
    const filename = extraction.filename.replace(/\.[^.]+$/, "");
    return {
      id,
      displayName: firstLine?.slice(0, 100) || filename,
      resume: extraction.raw_text,
      extraction,
    };
  }

  function updateCandidate(id: string, update: Partial<CandidateDraft>) {
    setCandidates((current) =>
      current.map((candidate) =>
        candidate.id === id ? { ...candidate, ...update } : candidate,
      ),
    );
    setCandidateErrors((current) => ({ ...current, [id]: "" }));
    analysis.reset();
  }

  function addExtractedCandidates(documents: DocumentExtraction[]) {
    setCandidates((current) => {
      const updated = [...current];
      for (const document of documents) {
        const emptyIndex = updated.findIndex(
          (candidate) => !candidate.resume.trim() && !candidate.extraction,
        );
        if (emptyIndex >= 0) {
          updated[emptyIndex] = candidateFromExtraction(
            document,
            updated[emptyIndex].id,
          );
        } else {
          updated.push(candidateFromExtraction(document));
        }
      }
      return updated;
    });
    analysis.reset();
  }

  function addBlankCandidate() {
    setCandidates((current) => [
      ...current,
      createBlankCandidate(nextCandidateNumber.current++),
    ]);
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const errors: Record<string, string> = {};
    for (const candidate of candidates) {
      if (!candidate.displayName.trim()) {
        errors[candidate.id] = "Add a candidate display name.";
      } else if (candidate.resume.trim().length < MINIMUM_DOCUMENT_LENGTH) {
        errors[candidate.id] = "Add at least 30 characters of resume text.";
      } else if (duplicateIds.has(candidate.id)) {
        errors[candidate.id] =
          "This resume duplicates another document in this job.";
      }
    }
    if (!candidates.length) {
      setPrivacyError("Upload at least one resume before finding talent.");
      return;
    }
    setCandidateErrors(errors);
    if (!privacyConfirmed) {
      setPrivacyError("Confirm the privacy notice before starting analysis.");
    } else {
      setPrivacyError(undefined);
    }
    if (!scorecardApproved || Object.keys(errors).length || !privacyConfirmed)
      return;
    analysis.mutate();
  }

  return (
    <CollapsibleSection
      title="Find Talent"
      description="Upload resumes and compare them against the approved scorecard."
      status={
        <span className="rounded-full border border-line px-2.5 py-1 text-[11px] font-semibold text-muted">
          {populatedCandidates.length} resume
          {populatedCandidates.length === 1 ? "" : "s"}
        </span>
      }
    >
      <div className="p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-end gap-2">
          <MultiResumeUpload
            existingHashes={existingHashes}
            onUploaded={addExtractedCandidates}
          />
          <button
            type="button"
            onClick={addBlankCandidate}
            className="rounded-md border border-line px-3 py-2 text-xs font-semibold"
          >
            + Add manually
          </button>
        </div>

        {!scorecardApproved && (
          <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs font-medium text-amber">
            Approve the scorecard above before running a talent comparison.
          </p>
        )}
        <form onSubmit={submit} className="mt-5" noValidate>
          <div className="grid gap-4 lg:grid-cols-2">
            {candidates.map((candidate, index) => (
              <article
                key={candidate.id}
                className="rounded-xl border border-line p-4"
              >
                <div className="mb-4 flex items-start justify-between gap-3">
                  <label className="min-w-0 flex-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Candidate {index + 1} display name
                    <input
                      value={candidate.displayName}
                      maxLength={100}
                      onChange={(event) =>
                        updateCandidate(candidate.id, {
                          displayName: event.target.value,
                        })
                      }
                      className="mt-1 w-full border-0 border-b border-line bg-transparent px-0 pb-1.5 text-sm font-semibold normal-case tracking-normal text-ink focus:border-brand-500 focus:outline-none"
                    />
                  </label>
                  <button
                    type="button"
                    aria-label={`Remove ${candidate.displayName || `candidate ${index + 1}`}`}
                    disabled={candidates.length === 1}
                    onClick={() => {
                      setCandidates((current) =>
                        current.filter((item) => item.id !== candidate.id),
                      );
                      analysis.reset();
                    }}
                    className="rounded-md border border-line px-2 py-1 text-xs text-muted disabled:opacity-40"
                  >
                    Remove
                  </button>
                </div>
                <DocumentInput
                  id={`${candidate.id}-job-resume`}
                  label={`Candidate ${index + 1} resume`}
                  documentType="resume"
                  value={candidate.resume}
                  error={candidateErrors[candidate.id] || undefined}
                  help="Paste text or upload a PDF, DOCX, or UTF-8 TXT file."
                  placeholder="Paste or upload this candidate’s resume…"
                  extraction={candidate.extraction}
                  onChange={(resume) =>
                    updateCandidate(candidate.id, { resume })
                  }
                  onExtractionChange={(extraction) => {
                    const update: Partial<CandidateDraft> = { extraction };
                    if (
                      extraction &&
                      candidate.displayName.startsWith("Candidate ")
                    ) {
                      update.displayName =
                        extraction.raw_text
                          .split("\n")[0]
                          ?.trim()
                          .slice(0, 100) || candidate.displayName;
                    }
                    updateCandidate(candidate.id, update);
                  }}
                />
                {duplicateIds.has(candidate.id) && (
                  <p
                    role="alert"
                    className="mt-2 text-xs font-medium text-amber"
                  >
                    This resume duplicates another document in this job.
                  </p>
                )}
              </article>
            ))}
          </div>

          <div className="mt-5 grid gap-4 rounded-xl border border-line bg-canvas/40 p-4 lg:grid-cols-2">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={blindReview}
                onChange={(event) => setBlindReview(event.target.checked)}
                className="mt-0.5 h-4 w-4 accent-brand-600"
              />
              <span>
                <span className="block text-xs font-semibold text-ink">
                  Blind-review display
                </span>
                <span className="mt-1 block text-[11px] leading-4 text-muted">
                  Replace candidate names with neutral labels in new results.
                </span>
              </span>
            </label>
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={privacyConfirmed}
                onChange={(event) => {
                  setPrivacyConfirmed(event.target.checked);
                  setPrivacyError(undefined);
                }}
                className="mt-0.5 h-4 w-4 accent-brand-600"
              />
              <span>
                <span className="block text-xs font-semibold text-ink">
                  Approve this analysis
                </span>
                <span className="mt-1 block text-[11px] leading-4 text-muted">
                  {providerSession?.sends_documents_externally
                    ? `The job description and resumes will be sent to ${providerSession.provider}.`
                    : "Documents remain local with the mock provider."}
                </span>
              </span>
            </label>
          </div>

          {(privacyError || analysis.isError) && (
            <p role="alert" className="mt-3 text-sm text-red-700">
              {privacyError ?? analysis.error?.message}
            </p>
          )}
          {analysis.isPending && progress && (
            <p
              aria-live="polite"
              className="mt-3 text-xs font-medium text-brand-700"
            >
              {progress.latest_event?.label ?? "Starting analysis…"} ·{" "}
              {progress.completed_count}/{progress.candidate_count} complete
            </p>
          )}

          <div className="mt-5 flex justify-end border-t border-line pt-4">
            <button
              type="submit"
              disabled={
                !scorecardApproved ||
                !populatedCandidates.length ||
                analysis.isPending ||
                duplicateIds.size > 0
              }
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {analysis.isPending
                ? `Finding talent…`
                : `Find Talent — Compare ${populatedCandidates.length} Candidate${populatedCandidates.length === 1 ? "" : "s"}`}
              {!analysis.isPending && <Icon name="arrow" className="h-4 w-4" />}
            </button>
          </div>
        </form>

        {analysis.data && (
          <TalentSearchSummary
            result={analysis.data}
            onViewEvidence={onViewEvidence}
          />
        )}
      </div>
    </CollapsibleSection>
  );
}

function duplicateCandidateIds(candidates: CandidateDraft[], jobText: string) {
  const owners = new Map<string, string>();
  const duplicates = new Set<string>();
  const normalizedJob = normalizedDocument(jobText);
  for (const candidate of candidates) {
    const text = normalizedDocument(candidate.resume);
    if (!text) continue;
    if (text === normalizedJob) duplicates.add(candidate.id);
    const owner = owners.get(text);
    if (owner) {
      duplicates.add(owner);
      duplicates.add(candidate.id);
    } else {
      owners.set(text, candidate.id);
    }
  }
  return duplicates;
}

function TalentSearchSummary({
  result,
  onViewEvidence,
}: {
  result: BatchComparisonResult;
  onViewEvidence?: (result: ComparisonResult) => void;
}) {
  return (
    <div className="mt-6 rounded-xl border border-brand-100 bg-brand-50 p-4">
      <p className="text-sm font-semibold text-brand-700">
        Talent comparison complete
      </p>
      <p className="mt-1 text-xs leading-5 text-muted">
        Results are shown in upload order and have been added to this job’s
        analysis history.
      </p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {result.comparisons.map((item) => (
          <div
            key={item.candidate_id}
            className="rounded-lg border border-brand-100 bg-white p-3"
          >
            <p className="text-sm font-semibold text-ink">
              {item.display_name}
            </p>
            <p className="mt-1 text-xs text-muted">
              Fit {Math.round(item.comparison.fit_score)} · Mandatory{" "}
              {resultLabel(item.comparison.mandatory_status)}
            </p>
            {onViewEvidence && (
              <button
                type="button"
                onClick={() => onViewEvidence(item.comparison)}
                className="mt-3 rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink"
              >
                View evidence
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
