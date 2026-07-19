"use client";

import { useState } from "react";

import { exportComparisons } from "@/lib/api";

const MAX_EXPORT_ANALYSES = 5;

function safeFilename(value: string) {
  return (
    value
      .trim()
      .toLocaleLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "") || "analyses"
  );
}

export function AnalysisExportControls({
  comparisonIds,
  filenamePrefix,
}: {
  comparisonIds: string[];
  filenamePrefix: string;
}) {
  const [pendingFormat, setPendingFormat] = useState<"csv" | "json">();
  const [message, setMessage] = useState<string>();
  const [error, setError] = useState<string>();

  async function download(format: "csv" | "json") {
    setMessage(undefined);
    setError(undefined);
    if (!comparisonIds.length) {
      setError("Select at least one analysis to export.");
      return;
    }
    if (comparisonIds.length > MAX_EXPORT_ANALYSES) {
      setError(
        `Select no more than ${MAX_EXPORT_ANALYSES} analyses per export.`,
      );
      return;
    }

    setPendingFormat(format);
    try {
      const blob = await exportComparisons(format, comparisonIds);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${safeFilename(filenamePrefix)}-analyses.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage(`${format.toUpperCase()} export generated.`);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The selected analyses could not be exported.",
      );
    } finally {
      setPendingFormat(undefined);
    }
  }

  return (
    <div className="flex flex-col gap-2 sm:items-end">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={!comparisonIds.length || Boolean(pendingFormat)}
          onClick={() => void download("csv")}
          className="rounded-md bg-brand-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          {pendingFormat === "csv" ? "Exporting…" : "Export selected CSV"}
        </button>
        <button
          type="button"
          disabled={!comparisonIds.length || Boolean(pendingFormat)}
          onClick={() => void download("json")}
          className="rounded-md border border-line bg-white px-3 py-2 text-xs font-semibold text-ink disabled:opacity-50"
        >
          {pendingFormat === "json" ? "Exporting…" : "Export selected JSON"}
        </button>
      </div>
      <p className="text-xs text-muted">
        {comparisonIds.length} of {MAX_EXPORT_ANALYSES} selected for export.
      </p>
      {message && (
        <p aria-live="polite" className="text-xs text-brand-700">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="text-xs text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
