"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import {
  configureProvider,
  deleteAllData,
  getDashboard,
  getSettings,
  removeProviderSession,
  updateSettings,
  validateProvider,
} from "@/lib/api";
import type { ProviderSession, TriagePolicy } from "@/types/comparison";
import { CandidatesWorkspace } from "./candidates-workspace";
import { Icon } from "./icons";
import { JobsWorkspace } from "./jobs-workspace";

const navigation = [
  ["Dashboard", "dashboard"],
  ["Candidates", "people"],
  ["Jobs", "briefcase"],
  ["Scoring configuration", "sliders"],
  ["Provider settings", "key"],
  ["Privacy settings", "shield"],
  ["Documentation", "docs"],
] as const;

type View = (typeof navigation)[number][0];

function Panel({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border border-line bg-white shadow-card sm:rounded-2xl">
      <div className="border-b border-line px-5 py-5 sm:px-7">
        <h2 className="text-lg font-semibold text-ink">{title}</h2>
        <p className="mt-1 text-sm text-muted">{description}</p>
      </div>
      <div className="p-5 sm:p-7">{children}</div>
    </section>
  );
}

function DashboardView({
  onNewJob,
  onCandidates,
}: {
  onNewJob: () => void;
  onCandidates: () => void;
}) {
  const query = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });
  if (query.isLoading) return <p aria-live="polite">Loading dashboard…</p>;
  if (!query.data)
    return (
      <p role="alert" className="text-red-700">
        Dashboard data is unavailable.
      </p>
    );
  const data = query.data;
  const metrics = [
    ["Total analyses", data.total_comparisons],
    ["Active jobs", data.active_jobs],
    ["Candidates analysed", data.candidates_analyzed],
    ["Average fit score", data.average_fit_score],
    ["Need clarification", data.requiring_clarification],
    ["Retention days", data.retention_days],
  ];
  return (
    <div className="space-y-5">
      <section className="flex flex-col justify-between gap-4 rounded-2xl border border-brand-100 bg-brand-50 p-5 shadow-card sm:flex-row sm:items-center sm:p-6">
        <div>
          <h2 className="text-lg font-semibold text-ink">
            Start recruiting work
          </h2>
          <p className="mt-1 text-sm text-muted">
            Create a job workspace or continue with a saved candidate.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onNewJob}
            className="rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white"
          >
            + New Job
          </button>
          <button
            type="button"
            onClick={onCandidates}
            className="rounded-lg border border-line bg-white px-4 py-2.5 text-sm font-semibold text-ink"
          >
            Open Candidates
          </button>
        </div>
      </section>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map(([name, value]) => (
          <div
            key={name}
            className="rounded-xl border border-line bg-white p-5 shadow-card"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              {name}
            </p>
            <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
          </div>
        ))}
      </div>
      <Panel
        title="Recent analyses"
        description={`Provider status: ${data.provider_status}`}
      >
        {data.recent_comparisons.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase text-muted">
                <tr>
                  <th className="pb-3">Candidate</th>
                  <th className="pb-3">Job</th>
                  <th className="pb-3">Fit</th>
                  <th className="pb-3">Mandatory</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.recent_comparisons.map((item) => (
                  <tr key={item.id}>
                    <td className="py-3 font-semibold">
                      {item.candidate_display_name}
                    </td>
                    <td>{item.job_title}</td>
                    <td>{item.fit_score ?? "-"}</td>
                    <td>
                      {item.mandatory_status?.replaceAll("_", " ") ?? "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted">
            Create a job and analyse candidates to populate the dashboard.
          </p>
        )}
      </Panel>
    </div>
  );
}

function ProviderSettings({
  session,
  onSession,
}: {
  session?: ProviderSession;
  onSession: (value?: ProviderSession) => void;
}) {
  const [provider, setProvider] = useState(session?.provider ?? "mock");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(session?.model ?? "mock-evidence-v1");
  const [baseUrl, setBaseUrl] = useState(session?.base_url ?? "");
  const [message, setMessage] = useState<string>();
  const configure = useMutation({
    mutationFn: configureProvider,
    onSuccess: (value) => {
      onSession(value);
      setApiKey("");
      setMessage("Provider stored in expiring server memory.");
    },
  });
  const test = useMutation({
    mutationFn: validateProvider,
    onSuccess: (value) => setMessage(value.message),
  });
  const defaults: Record<string, string> = {
    mock: "mock-evidence-v1",
    openai: "gpt-4.1-mini",
    anthropic: "claude-sonnet-4-5",
    google: "gemini-2.5-flash",
    groq: "llama-3.3-70b-versatile",
    compatible: "default",
    ollama: "llama3.2",
  };
  return (
    <Panel
      title="Provider settings"
      description="Bring your own key. Secrets are never returned or stored in the database."
    >
      <form
        className="grid max-w-2xl gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          configure.mutate({
            provider,
            api_key: apiKey || undefined,
            model,
            base_url: baseUrl || undefined,
          });
        }}
      >
        <label className="text-sm font-medium text-ink">
          Provider
          <select
            value={provider}
            onChange={(event) => {
              const value = event.target.value;
              setProvider(value);
              setModel(defaults[value]);
            }}
            className="mt-1 w-full rounded-md border border-line px-3 py-2"
          >
            <option value="mock">Local mock</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="google">Google Gemini</option>
            <option value="groq">Groq</option>
            <option value="compatible">OpenAI-compatible</option>
            <option value="ollama">Ollama</option>
          </select>
        </label>
        <label className="text-sm font-medium text-ink">
          Model
          <input
            value={model}
            onChange={(event) => setModel(event.target.value)}
            className="mt-1 w-full rounded-md border border-line px-3 py-2"
          />
        </label>
        {!["mock", "ollama"].includes(provider) && (
          <label className="text-sm font-medium text-ink">
            API key
            <input
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              className="mt-1 w-full rounded-md border border-line px-3 py-2"
            />
          </label>
        )}
        {["compatible", "ollama"].includes(provider) && (
          <label className="text-sm font-medium text-ink">
            Base URL
            <input
              type="url"
              value={baseUrl}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder={
                provider === "ollama"
                  ? "http://localhost:11434"
                  : "https://provider.example.com"
              }
              className="mt-1 w-full rounded-md border border-line px-3 py-2"
            />
          </label>
        )}
        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white"
          >
            Save session
          </button>
          {session && (
            <button
              type="button"
              onClick={() => test.mutate(session.session_id)}
              className="rounded-md border border-line px-4 py-2 text-sm font-semibold"
            >
              Test connection
            </button>
          )}
          {session && (
            <button
              type="button"
              onClick={() =>
                void removeProviderSession(session.session_id).then(() => {
                  onSession(undefined);
                  setMessage("Provider session removed.");
                })
              }
              className="rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700"
            >
              Remove key
            </button>
          )}
        </div>
        {session && (
          <p className="text-xs text-muted">
            Configured: {session.provider} / {session.model} · key{" "}
            {session.masked_key ?? "not required"} · expires{" "}
            {new Date(session.expires_at).toLocaleTimeString()}
          </p>
        )}
        {(message || configure.error?.message || test.error?.message) && (
          <p
            role={configure.isError || test.isError ? "alert" : undefined}
            className="text-sm text-muted"
          >
            {configure.error?.message ?? test.error?.message ?? message}
          </p>
        )}
      </form>
    </Panel>
  );
}

function PrivacySettings() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const [retention, setRetention] = useState(30);
  useEffect(() => {
    if (query.data) setRetention(query.data.retention_policy_days);
  }, [query.data]);
  const save = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => void client.invalidateQueries({ queryKey: ["settings"] }),
  });
  const deletion = useMutation({
    mutationFn: deleteAllData,
    onSuccess: () => void client.invalidateQueries(),
  });
  if (!query.data) return <p>Loading settings…</p>;
  return (
    <Panel
      title="Privacy and retention"
      description="Control local retention and erase all persisted candidate data."
    >
      <div className="max-w-xl space-y-5">
        <label className="block text-sm font-medium">
          Retention period (days)
          <input
            type="number"
            min={0}
            max={3650}
            value={retention}
            onChange={(event) => setRetention(Number(event.target.value))}
            className="mt-1 w-full rounded-md border border-line px-3 py-2"
          />
        </label>
        <button
          type="button"
          onClick={() =>
            save.mutate({ ...query.data, retention_policy_days: retention })
          }
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white"
        >
          Save retention
        </button>
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <h3 className="font-semibold text-red-900">
            Delete all application data
          </h3>
          <p className="mt-1 text-xs leading-5 text-red-800">
            Permanently removes saved jobs, candidates, resumes, comparisons,
            analysis runs, and audit events. Provider keys already live only in
            memory.
          </p>
          <button
            type="button"
            onClick={() => {
              if (
                window.confirm("Permanently delete all saved TalentMatch data?")
              )
                deletion.mutate();
            }}
            className="mt-3 rounded-md bg-red-700 px-4 py-2 text-sm font-semibold text-white"
          >
            Delete all data
          </button>
        </div>
        {(save.isSuccess || deletion.isSuccess) && (
          <p aria-live="polite" className="text-sm text-brand-700">
            Privacy settings updated.
          </p>
        )}
      </div>
    </Panel>
  );
}

function ScoringSettings() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [taxonomy, setTaxonomy] = useState("[]");
  const [triagePolicy, setTriagePolicy] = useState<TriagePolicy>({
    shortlist_fit_threshold: 80,
    shortlist_evidence_threshold: 80,
    require_mandatory_met: true,
    require_no_clarification_flags: true,
  });
  const [error, setError] = useState<string>();
  useEffect(() => {
    if (query.data) {
      setWeights(query.data.scoring_configuration);
      setTaxonomy(JSON.stringify(query.data.skill_taxonomy, null, 2));
      setTriagePolicy(query.data.default_triage_policy);
    }
  }, [query.data]);
  const save = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => void client.invalidateQueries({ queryKey: ["settings"] }),
  });
  if (!query.data) return <p>Loading scoring settings…</p>;
  const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
  return (
    <Panel
      title="Scoring configuration"
      description="Edit deterministic weights, global triage defaults, and the provider-independent skill taxonomy."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(weights).map(([key, value]) => (
            <label key={key} className="text-xs font-medium text-muted">
              {key.replaceAll("_", " ")}
              <input
                type="number"
                min={0}
                max={100}
                value={value}
                onChange={(event) =>
                  setWeights((current) => ({
                    ...current,
                    [key]: Number(event.target.value),
                  }))
                }
                className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm text-ink"
              />
            </label>
          ))}
          <p
            className={`text-sm font-semibold sm:col-span-2 ${total === 100 ? "text-brand-700" : "text-red-700"}`}
          >
            Total: {total} / 100
          </p>
        </div>
        <label className="text-sm font-medium text-ink">
          Skill taxonomy JSON
          <textarea
            value={taxonomy}
            onChange={(event) => setTaxonomy(event.target.value)}
            rows={15}
            spellCheck={false}
            className="mt-1 w-full rounded-md border border-line p-3 font-mono text-xs"
          />
          <span className="mt-1 block text-xs font-normal text-muted">
            Example:{" "}
            {`[{"canonical":"RAG","aliases":["retrieval augmented generation"]}]`}
          </span>
        </label>
      </div>
      <section className="mt-6 rounded-xl border border-line p-4">
        <h3 className="text-sm font-semibold text-ink">
          Default recruiter triage policy
        </h3>
        <p className="mt-1 text-xs leading-5 text-muted">
          These defaults are copied into newly created jobs. Existing jobs keep
          their versioned policy.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-xs font-medium text-muted">
            Shortlist fit threshold
            <input
              type="number"
              min={0}
              max={100}
              value={triagePolicy.shortlist_fit_threshold}
              onChange={(event) =>
                setTriagePolicy((current) => ({
                  ...current,
                  shortlist_fit_threshold: Number(event.target.value),
                }))
              }
              className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm text-ink"
            />
          </label>
          <label className="text-xs font-medium text-muted">
            Evidence confidence threshold
            <input
              type="number"
              min={0}
              max={100}
              value={triagePolicy.shortlist_evidence_threshold}
              onChange={(event) =>
                setTriagePolicy((current) => ({
                  ...current,
                  shortlist_evidence_threshold: Number(event.target.value),
                }))
              }
              className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm text-ink"
            />
          </label>
          <label className="flex items-center gap-2 text-xs font-medium text-ink">
            <input
              type="checkbox"
              checked={triagePolicy.require_mandatory_met}
              onChange={(event) =>
                setTriagePolicy((current) => ({
                  ...current,
                  require_mandatory_met: event.target.checked,
                }))
              }
            />
            Require mandatory requirements to be met
          </label>
          <label className="flex items-center gap-2 text-xs font-medium text-ink">
            <input
              type="checkbox"
              checked={triagePolicy.require_no_clarification_flags}
              onChange={(event) =>
                setTriagePolicy((current) => ({
                  ...current,
                  require_no_clarification_flags: event.target.checked,
                }))
              }
            />
            Require no clarification flags
          </label>
        </div>
      </section>
      <button
        type="button"
        disabled={total !== 100 || save.isPending}
        onClick={() => {
          try {
            const parsed = JSON.parse(taxonomy) as Array<
              Record<string, unknown>
            >;
            if (!Array.isArray(parsed))
              throw new Error("Taxonomy must be a JSON array.");
            setError(undefined);
            save.mutate({
              ...query.data,
              scoring_configuration: weights,
              default_triage_policy: triagePolicy,
              skill_taxonomy: parsed,
            });
          } catch (value) {
            setError(
              value instanceof Error ? value.message : "Invalid taxonomy JSON.",
            );
          }
        }}
        className="mt-5 rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
      >
        Save scoring configuration
      </button>
      {(error || save.error?.message) && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error ?? save.error?.message}
        </p>
      )}
      {save.isSuccess && (
        <p aria-live="polite" className="mt-2 text-sm text-brand-700">
          Scoring configuration saved.
        </p>
      )}
    </Panel>
  );
}

function DocumentationView() {
  return (
    <Panel
      title="Documentation"
      description="Architecture, security, privacy, scoring, and API references."
    >
      <ul className="grid gap-3 sm:grid-cols-2">
        <li>
          <a
            className="text-brand-700 underline"
            href="http://localhost:8000/docs"
          >
            Interactive API documentation
          </a>
        </li>
        <li>
          <span className="font-medium">Scoring:</span> deterministic category
          weights and mandatory status are separate.
        </li>
        <li>
          <span className="font-medium">Privacy:</span> local mock sends no
          documents externally.
        </li>
        <li>
          <span className="font-medium">Fairness:</span> protected attributes
          never enter scoring.
        </li>
      </ul>
    </Panel>
  );
}

export function WorkspaceShell() {
  const [view, setView] = useState<View>("Dashboard");
  const [startWithNewJob, setStartWithNewJob] = useState(false);
  const [providerSession, setProviderSession] = useState<ProviderSession>();
  useEffect(() => {
    const saved = sessionStorage.getItem("talentmatch-provider-session");
    if (saved) {
      try {
        setProviderSession(JSON.parse(saved) as ProviderSession);
      } catch {
        sessionStorage.removeItem("talentmatch-provider-session");
      }
    }
  }, []);
  function updateProvider(value?: ProviderSession) {
    setProviderSession(value);
    if (value)
      sessionStorage.setItem(
        "talentmatch-provider-session",
        JSON.stringify(value),
      );
    else sessionStorage.removeItem("talentmatch-provider-session");
  }
  function navigate(nextView: View) {
    setStartWithNewJob(false);
    setView(nextView);
  }
  function createNewJob() {
    setStartWithNewJob(true);
    setView("Jobs");
  }
  const content =
    view === "Dashboard" ? (
      <DashboardView
        onNewJob={createNewJob}
        onCandidates={() => navigate("Candidates")}
      />
    ) : view === "Candidates" ? (
      <CandidatesWorkspace providerSession={providerSession} />
    ) : view === "Jobs" ? (
      <JobsWorkspace
        providerSession={providerSession}
        startWithNewJob={startWithNewJob}
      />
    ) : view === "Provider settings" ? (
      <ProviderSettings session={providerSession} onSession={updateProvider} />
    ) : view === "Privacy settings" ? (
      <PrivacySettings />
    ) : view === "Scoring configuration" ? (
      <ScoringSettings />
    ) : view === "Documentation" ? (
      <DocumentationView />
    ) : (
      <DashboardView
        onNewJob={createNewJob}
        onCandidates={() => navigate("Candidates")}
      />
    );
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[252px_1fr]">
      <aside className="hidden min-h-screen border-r border-white/10 bg-navy text-white lg:sticky lg:top-0 lg:block lg:h-screen">
        <div className="flex h-20 items-center gap-3 border-b border-white/10 px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500 text-sm font-bold">
            TM
          </div>
          <div>
            <p className="text-sm font-semibold">TalentMatch AI</p>
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-400">
              Recruiting intelligence
            </p>
          </div>
        </div>
        <nav aria-label="Primary navigation" className="px-3 py-5">
          <ul className="space-y-1">
            {navigation.map(([item, icon]) => (
              <li key={item}>
                <button
                  type="button"
                  onClick={() => {
                    navigate(item);
                  }}
                  aria-current={view === item ? "page" : undefined}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs font-medium ${view === item ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}
                >
                  <Icon name={icon} className="h-4 w-4" />
                  {item}
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <div className="absolute bottom-5 left-4 right-4 rounded-xl border border-white/10 bg-white/5 p-4">
          <p className="text-xs font-semibold">
            {providerSession
              ? `${providerSession.provider} configured`
              : "Local mock ready"}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">
            No autonomous hiring decisions.
          </p>
        </div>
      </aside>
      <main className="min-w-0">
        <header className="border-b border-line bg-white">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
            <select
              aria-label="Current workspace view"
              value={view}
              onChange={(event) => {
                const nextView = event.target.value as View;
                navigate(nextView);
              }}
              className="rounded-md border border-line px-3 py-2 text-sm lg:hidden"
            >
              {navigation.map(([item]) => (
                <option key={item}>{item}</option>
              ))}
            </select>
            <div className="hidden text-xs text-muted lg:block">
              Workspace / <span className="font-semibold text-ink">{view}</span>
            </div>
            <span className="rounded-full border border-brand-100 bg-brand-50 px-3 py-1.5 text-[11px] font-semibold text-brand-700">
              {providerSession?.provider ?? "Mock provider"} ready
            </span>
          </div>
        </header>
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-7">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-600">
              Evidence-led assessment
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">
              {view}
            </h1>
            <p className="mt-2 text-sm text-muted">
              Explainable recruiting decision support with evidence,
              uncertainty, and human review.
            </p>
          </div>
          {content}
        </div>
      </main>
    </div>
  );
}
