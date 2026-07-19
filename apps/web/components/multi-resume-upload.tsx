"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { uploadDocument } from "@/lib/api";
import type { DocumentExtraction } from "@/types/comparison";
import { Icon } from "./icons";

const MAX_FILE_BYTES = 10 * 1024 * 1024;

interface BatchUploadResult {
  extracted: DocumentExtraction[];
  errors: string[];
}

export function MultiResumeUpload({
  availableSlots,
  existingHashes,
  onUploaded,
}: {
  availableSlots: number;
  existingHashes: Set<string>;
  onUploaded: (documents: DocumentExtraction[]) => void;
}) {
  const [message, setMessage] = useState<string>();
  const upload = useMutation({
    mutationFn: async (files: File[]): Promise<BatchUploadResult> => {
      const errors: string[] = [];
      const validFiles = files.filter((file) => {
        if (file.size > MAX_FILE_BYTES) {
          errors.push(`${file.name}: exceeds the 10 MB limit.`);
          return false;
        }
        return true;
      });
      const settled = await Promise.allSettled(
        validFiles.map((file) => uploadDocument(file, "resume")),
      );
      const extracted: DocumentExtraction[] = [];
      settled.forEach((result, index) => {
        if (result.status === "fulfilled") extracted.push(result.value);
        else {
          const reason =
            result.reason instanceof Error
              ? result.reason.message
              : "The document could not be extracted.";
          errors.push(`${validFiles[index].name}: ${reason}`);
        }
      });
      return { extracted, errors };
    },
    onSuccess: ({ extracted, errors }) => {
      const seen = new Set(existingHashes);
      const unique: DocumentExtraction[] = [];
      const duplicateNames: string[] = [];
      for (const document of extracted) {
        if (seen.has(document.sha256)) duplicateNames.push(document.filename);
        else {
          seen.add(document.sha256);
          unique.push(document);
        }
      }
      onUploaded(unique);
      const messages = [...errors];
      if (duplicateNames.length) {
        messages.push(`Duplicate files skipped: ${duplicateNames.join(", ")}.`);
      }
      setMessage(messages.join(" ") || `${unique.length} resume(s) extracted.`);
    },
  });

  return (
    <div>
      <label
        htmlFor="multi-resume-upload"
        className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-xs font-semibold transition ${
          availableSlots > 0 && !upload.isPending
            ? "cursor-pointer border-brand-100 bg-brand-50 text-brand-700 hover:border-brand-500"
            : "cursor-not-allowed border-line bg-slate-100 text-slate-400"
        }`}
      >
        <Icon name="upload" className="h-3.5 w-3.5" />
        {upload.isPending ? "Extracting resumes…" : "Upload multiple resumes"}
      </label>
      <input
        id="multi-resume-upload"
        type="file"
        multiple
        accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
        className="sr-only"
        disabled={availableSlots === 0 || upload.isPending}
        onChange={(event) => {
          const selected = Array.from(event.target.files ?? []);
          if (selected.length > availableSlots) {
            setMessage(
              `Select no more than ${availableSlots} additional resume(s).`,
            );
          } else if (selected.length) {
            setMessage(undefined);
            upload.mutate(selected);
          }
          event.target.value = "";
        }}
      />
      {message && (
        <p
          aria-live="polite"
          className="mt-1.5 max-w-sm text-[11px] leading-4 text-muted"
        >
          {message}
        </p>
      )}
      {upload.isError && (
        <p role="alert" className="mt-1.5 text-[11px] font-medium text-red-700">
          The selected resumes could not be processed.
        </p>
      )}
    </div>
  );
}
