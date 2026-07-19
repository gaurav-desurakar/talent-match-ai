"use client";

import { useState } from "react";

import { exportComparisons } from "@/lib/api";
import type { ComparisonResult } from "@/types/comparison";
import { Icon } from "./icons";

function label(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
function sourceLabel(value: string) {
  const pageLine = value.match(/page-(\d+)-line-(\d+)$/);
  if (pageLine) return `Page ${pageLine[1]}, line ${pageLine[2]}`;
  const paragraph = value.match(/paragraph-(\d+)$/);
  if (paragraph) return `Paragraph ${paragraph[1]}`;
  const tableRow = value.match(/table-(\d+)-row-(\d+)$/);
  if (tableRow) return `Table ${tableRow[1]}, row ${tableRow[2]}`;
  const line = value.match(/line-(\d+)$/);
  if (line) return `Line ${line[1]}`;
  return "Source passage";
}

function matchStyle(match: string) {
  if (match === "exact" || match === "equivalent")
    return "border-brand-100 bg-brand-50 text-brand-700";
  if (match === "no_evidence")
    return "border-orange-200 bg-orange-50 text-amber";
  return "border-sky-200 bg-sky-50 text-sky-800";
}

function ScoreRing({ score, title }: { score: number; title: string }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="flex items-center gap-4">
      <div
        className="relative h-24 w-24 shrink-0"
        role="img"
        aria-label={`${title}: ${score} out of 100`}
      >
        <svg
          className="h-24 w-24 -rotate-90"
          viewBox="0 0 100 100"
          aria-hidden="true"
        >
          <circle
            cx="50"
            cy="50"
            r={radius}
            stroke="#E5EAEE"
            strokeWidth="7"
            fill="none"
          />
          <circle
            cx="50"
            cy="50"
            r={radius}
            stroke="#087F78"
            strokeWidth="7"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - score / 100)}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-2xl font-semibold tracking-tight text-ink">
          {Math.round(score)}
        </span>
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          {title}
        </p>
        <p className="mt-1 text-sm leading-5 text-muted">out of 100</p>
      </div>
    </div>
  );
}

export function ComparisonEvidence({ result }: { result: ComparisonResult }) {
  const supported = result.requirement_matches.filter(
    (item) => item.evidence.length > 0,
  ).length;
  const [exportError, setExportError] = useState<string>();

  async function download(format: "report" | "json" | "interview-guide") {
    setExportError(undefined);
    try {
      const blob = await exportComparisons(format, [result.comparison_id]);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download =
        format === "json"
          ? "talentmatch-result.json"
          : format === "interview-guide"
            ? "interview-guide.pdf"
            : "talentmatch-report.pdf";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(
        error instanceof Error ? error.message : "The evidence export failed.",
      );
    }
  }
  return (
    <section className="mt-8 space-y-5" aria-labelledby="result-heading">
      <div className="overflow-hidden border border-line bg-white shadow-card sm:rounded-2xl">
        <div className="border-b border-line bg-gradient-to-r from-white to-brand-50/60 px-5 py-5 sm:px-7">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
            <div>
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-brand-100 bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700">
                  Analysis complete
                </span>
                <span className="text-xs text-muted">{result.model}</span>
              </div>
              <h2
                id="result-heading"
                className="text-2xl font-semibold tracking-tight text-ink"
              >
                {result.candidate_display_name}
              </h2>
              <p className="mt-1 text-sm text-muted">
                Compared with {result.job_title}
              </p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded-md border border-line bg-white px-3 py-2 text-ink">
                {label(result.recommendation)}
              </span>
              <span className="rounded-md border border-line bg-white px-3 py-2 text-ink">
                Mandatory: {label(result.mandatory_status)}
              </span>
              <button
                type="button"
                onClick={() => void download("report")}
                className="rounded-md border border-line bg-white px-3 py-2 text-ink hover:border-brand-500"
              >
                Export PDF
              </button>
              <button
                type="button"
                onClick={() => void download("json")}
                className="rounded-md border border-line bg-white px-3 py-2 text-ink hover:border-brand-500"
              >
                Export JSON
              </button>
            </div>
          </div>
        </div>

        {exportError && (
          <p
            role="alert"
            className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm text-red-700 sm:px-7"
          >
            {exportError}
          </p>
        )}

        <div className="grid gap-6 px-5 py-6 sm:px-7 lg:grid-cols-[1.35fr_1fr]">
          <div className="grid gap-6 sm:grid-cols-2">
            <ScoreRing score={result.fit_score} title="Fit score" />
            <ScoreRing
              score={result.evidence_confidence_score}
              title="Evidence confidence"
            />
          </div>
          <div className="grid grid-cols-2 divide-x divide-line rounded-xl border border-line bg-canvas/60 px-4 py-4">
            <div className="pr-4">
              <p className="text-2xl font-semibold text-ink">
                {supported}/{result.requirement_matches.length}
              </p>
              <p className="mt-1 text-xs leading-4 text-muted">
                requirements with evidence
              </p>
            </div>
            <div className="pl-4">
              <p className="text-2xl font-semibold text-ink">
                {
                  result.requirement_matches.filter(
                    (item) => item.clarification_required,
                  ).length
                }
              </p>
              <p className="mt-1 text-xs leading-4 text-muted">
                need clarification
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="border border-line bg-white shadow-card sm:rounded-2xl">
        <div className="flex flex-col justify-between gap-2 border-b border-line px-5 py-5 sm:flex-row sm:items-end sm:px-7">
          <div>
            <h3 className="text-lg font-semibold text-ink">
              Requirement evidence
            </h3>
            <p className="mt-1 text-sm text-muted">
              Every assessment links back to the pasted source text.
            </p>
          </div>
          <span className="text-xs font-medium text-muted">
            {result.requirement_matches.length} extracted requirements
          </span>
        </div>
        <div className="divide-y divide-line">
          {result.requirement_matches.map((match, index) => (
            <details
              key={match.requirement.id}
              className="group px-5 py-5 sm:px-7"
              open={index < 3}
            >
              <summary className="flex cursor-pointer list-none flex-col justify-between gap-3 sm:flex-row sm:items-center">
                <div className="min-w-0">
                  <div className="mb-2 flex flex-wrap gap-2">
                    <span
                      className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${matchStyle(match.match_type)}`}
                    >
                      {label(match.match_type)}
                    </span>
                    <span className="rounded-full border border-line bg-white px-2.5 py-1 text-[11px] font-medium text-muted">
                      {label(match.requirement.classification)}
                    </span>
                    {match.clarification_required && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-orange-200 bg-orange-50 px-2.5 py-1 text-[11px] font-semibold text-amber">
                        <Icon name="alert" className="h-3 w-3" /> Clarify
                      </span>
                    )}
                  </div>
                  <p className="pr-4 text-sm font-semibold leading-6 text-ink">
                    {match.requirement.canonical_concept ??
                      match.requirement.text}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  <div className="text-right">
                    <p className="text-lg font-semibold text-ink">
                      {Math.round(match.score)}
                      <span className="text-xs font-normal text-muted">
                        /100
                      </span>
                    </p>
                    <p className="text-[11px] text-muted">evidence score</p>
                  </div>
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-canvas text-muted transition-transform group-open:rotate-90">
                    <Icon name="arrow" className="h-4 w-4" />
                  </span>
                </div>
              </summary>
              <div className="mt-4 grid gap-3 border-l-2 border-brand-100 pl-4 lg:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                    Assessment
                  </p>
                  <p className="mt-1 text-sm leading-6 text-ink">
                    {match.explanation}
                  </p>
                  {match.uncertainties.map((uncertainty) => (
                    <p
                      key={uncertainty}
                      className="mt-2 text-xs leading-5 text-amber"
                    >
                      {uncertainty}
                    </p>
                  ))}
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                    Resume evidence
                  </p>
                  {match.evidence.length ? (
                    match.evidence.map((evidence, evidenceIndex) => (
                      <blockquote
                        key={`${match.requirement.id}-${evidence.source_reference}-${evidenceIndex}`}
                        className="mt-1 border-l border-line pl-3 text-sm leading-6 text-ink"
                      >
                        “{evidence.text}”
                        <cite className="mt-1 block text-[11px] not-italic text-muted">
                          {sourceLabel(evidence.source_reference)}
                        </cite>
                      </blockquote>
                    ))
                  ) : (
                    <p className="mt-1 text-sm leading-6 text-muted">
                      No supporting statement found in the pasted resume.
                    </p>
                  )}
                </div>
              </div>
            </details>
          ))}
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="border border-line bg-white p-5 shadow-card sm:rounded-2xl sm:p-6">
          <h3 className="text-base font-semibold text-ink">Score breakdown</h3>
          <div className="mt-4 space-y-4">
            {result.score_breakdown.map((item) => (
              <div key={item.category}>
                <div className="mb-1.5 flex justify-between gap-4 text-sm">
                  <span className="font-medium text-ink">
                    {label(item.category)}
                  </span>
                  <span className="text-muted">
                    {Math.round(item.score)} · weight {item.weight}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-brand-500"
                    style={{ width: `${item.score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="border border-line bg-navy p-5 text-white shadow-card sm:rounded-2xl sm:p-6">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 text-brand-100">
              <Icon name="shield" className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-base font-semibold">
                How to use this result
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                {result.disclaimer}
              </p>
              <p className="mt-3 text-xs leading-5 text-slate-400">
                {result.methodology_note}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="border border-line bg-white p-5 shadow-card sm:rounded-2xl sm:p-6">
          <h3 className="text-base font-semibold text-ink">
            Clarification points
          </h3>
          <div className="mt-4 space-y-3">
            {result.clarification_flags.length ? (
              result.clarification_flags.map((flag) => (
                <div
                  key={flag.id}
                  className="rounded-lg border border-orange-200 bg-orange-50 p-3"
                >
                  <p className="text-sm font-semibold text-ink">{flag.title}</p>
                  <p className="mt-1 text-xs leading-5 text-muted">
                    {flag.explanation}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">
                No additional clarification flags.
              </p>
            )}
          </div>
        </div>
        <div className="border border-line bg-white p-5 shadow-card sm:rounded-2xl sm:p-6">
          <h3 className="text-base font-semibold text-ink">
            Targeted interview questions
          </h3>
          <ol className="mt-4 space-y-3">
            {result.interview_questions.map((question, index) => (
              <li key={question.id} className="text-sm leading-6 text-ink">
                <span className="mr-2 font-semibold text-brand-600">
                  {index + 1}.
                </span>
                {question.question}
                <p className="ml-6 text-xs leading-5 text-muted">
                  {question.rationale}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
