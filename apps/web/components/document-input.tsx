"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { uploadDocument } from "@/lib/api";
import type { DocumentExtraction } from "@/types/comparison";
import { Icon } from "./icons";

const MAX_FILE_BYTES = 10 * 1024 * 1024;

interface DocumentInputProps {
  id: string;
  label: string;
  documentType: "resume" | "job_description";
  value: string;
  error?: string;
  help: string;
  placeholder: string;
  extraction?: DocumentExtraction;
  onChange: (value: string) => void;
  onExtractionChange: (extraction?: DocumentExtraction) => void;
}

export function DocumentInput({
  id,
  label,
  documentType,
  value,
  error,
  help,
  placeholder,
  extraction,
  onChange,
  onExtractionChange,
}: DocumentInputProps) {
  const [fileError, setFileError] = useState<string>();
  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(file, documentType),
    onSuccess: (result) => {
      setFileError(undefined);
      onChange(result.raw_text);
      onExtractionChange(result);
    },
  });

  function handleFile(file?: File) {
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      upload.reset();
      onExtractionChange(undefined);
      setFileError("The selected file exceeds the 10 MB limit.");
      return;
    }
    setFileError(undefined);
    upload.mutate(file);
  }

  function handleTextChange(nextValue: string) {
    onChange(nextValue);
    if (extraction) onExtractionChange(undefined);
  }

  const statusId = `${id}-upload-status`;
  const uploadError =
    fileError ?? (upload.isError ? upload.error.message : undefined);
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <label htmlFor={id} className="text-sm font-semibold text-ink">
          {label}
        </label>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-muted">
            {value.length.toLocaleString()} characters
          </span>
          <label
            htmlFor={`${id}-file`}
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-line bg-white px-2.5 py-1.5 text-[11px] font-semibold text-ink transition hover:border-brand-500 hover:text-brand-700"
          >
            <Icon name="upload" className="h-3.5 w-3.5" />
            {upload.isPending ? "Extracting…" : "Upload file"}
          </label>
          <input
            id={`${id}-file`}
            type="file"
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            className="sr-only"
            disabled={upload.isPending}
            aria-describedby={statusId}
            onChange={(event) => {
              handleFile(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
        </div>
      </div>
      <textarea
        id={id}
        value={value}
        onChange={(event) => handleTextChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : `${id}-help`}
        className="h-64 w-full resize-y rounded-xl border border-line bg-canvas/40 px-4 py-3 text-sm leading-6 text-ink transition focus:border-brand-500 focus:bg-white focus:outline-none"
        placeholder={placeholder}
      />
      {error ? (
        <p id={`${id}-error`} className="mt-2 text-xs font-medium text-red-700">
          {error}
        </p>
      ) : (
        <p id={`${id}-help`} className="mt-2 text-xs text-muted">
          {help}
        </p>
      )}
      <div id={statusId} aria-live="polite">
        {extraction && (
          <div className="mt-3 rounded-lg border border-brand-100 bg-brand-50 px-3 py-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 font-semibold text-brand-700">
                <Icon name="check" className="h-3.5 w-3.5" />{" "}
                {extraction.filename}
              </span>
              <span className="text-brand-700">
                {Math.round(extraction.extraction_confidence * 100)}% extraction
                confidence
              </span>
            </div>
            <p className="mt-1 text-[11px] text-muted">
              {extraction.source_references.length} source references ·{" "}
              {extraction.sections.length} section(s)
            </p>
            {extraction.warnings.map((warning) => (
              <p
                key={warning}
                className="mt-1.5 flex items-start gap-1.5 text-[11px] leading-4 text-amber"
              >
                <Icon name="alert" className="mt-0.5 h-3 w-3 shrink-0" />{" "}
                {warning}
              </p>
            ))}
            <details className="mt-2 border-t border-brand-100 pt-2">
              <summary className="cursor-pointer text-[11px] font-semibold text-brand-700">
                Review extracted sections
              </summary>
              <div className="mt-2 max-h-40 space-y-2 overflow-y-auto pr-1">
                {extraction.sections.map((section) => (
                  <div
                    key={`${section.title}-${section.source_reference_ids[0]}`}
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                      {section.title}
                    </p>
                    <p className="mt-0.5 whitespace-pre-line text-[11px] leading-4 text-ink">
                      {section.text}
                    </p>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}
        {uploadError && (
          <p role="alert" className="mt-2 text-xs font-medium text-red-700">
            {uploadError}
          </p>
        )}
      </div>
    </div>
  );
}
