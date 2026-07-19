"use client";

import { useId, useState, type ReactNode } from "react";

export function CollapsibleSection({
  title,
  description,
  status,
  children,
  defaultOpen = true,
}: {
  title: string;
  description: string;
  status?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const contentId = useId();

  return (
    <section className="overflow-hidden rounded-2xl border border-line bg-white shadow-card">
      <div
        className={`flex flex-col justify-between gap-3 p-5 sm:flex-row sm:items-center sm:p-6 ${isOpen ? "border-b border-line" : ""}`}
      >
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-ink">{title}</h3>
            {status}
          </div>
          <p className="mt-1 text-xs leading-5 text-muted">{description}</p>
        </div>
        <button
          type="button"
          aria-expanded={isOpen}
          aria-controls={contentId}
          onClick={() => setIsOpen((current) => !current)}
          className="inline-flex shrink-0 items-center justify-center gap-2 self-start rounded-md border border-line px-3 py-2 text-xs font-semibold text-ink sm:self-auto"
        >
          {isOpen ? "Hide" : "Show"} {title}
          <span
            aria-hidden="true"
            className={`text-sm transition-transform ${isOpen ? "rotate-180" : ""}`}
          >
            ▾
          </span>
        </button>
      </div>
      <div id={contentId} hidden={!isOpen}>
        {children}
      </div>
    </section>
  );
}
