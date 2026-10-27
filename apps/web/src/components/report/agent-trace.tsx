import type { AgentStep, Report } from "@/lib/report-types";
import { IconCheck } from "../icons";
import { cx } from "../ui";

const KIND: Record<AgentStep["kind"], { label: string; cls: string }> = {
  privacy: { label: "Privacy guard", cls: "border-trace-fg text-trace-fg" },
  plan: { label: "Plan", cls: "border-trace-fg/60 text-trace-fg" },
  tool_call: { label: "Tool call", cls: "border-trace-muted text-trace-muted" },
  tool_result: { label: "Result", cls: "border-trace-muted text-trace-muted" },
  verify: { label: "Verify", cls: "border-trace-fg text-trace-fg" },
  output: { label: "Output", cls: "border-trace-fg/60 text-trace-fg" },
  illustrate: { label: "Illustrate", cls: "border-trace-fg/60 text-trace-fg" },
  note: { label: "Note", cls: "border-trace-line text-trace-muted" },
};

function DetailValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span className="text-trace-muted">—</span>;
  if (typeof value === "string") return <span>“{value}”</span>;
  if (typeof value === "number" || typeof value === "boolean") return <span>{String(value)}</span>;
  return <span>{JSON.stringify(value)}</span>;
}

/** "How EmberScan got here": the Muse Spark agent's plan, tool calls and verification, as stored with the report. */
export function AgentTrace({ report }: { report: Report }) {
  const steps = report.agent_trace ?? [];
  const toolCalls = steps.filter((s) => s.kind === "tool_call").length;
  const cost = report.cost as { spent_usd?: number; calls?: number };
  const planner = report.agent_model;
  const open = planner?.provider === "baseten";
  const privacy = report.privacy;
  const verifies = steps.filter((s) => s.kind === "verify").length;
  const pictures = report.fixes.filter((f) => f.illustration).length;
  // The loop in order. Guardrails (privacy before, verifier after) are code the agent can't skip.
  const loop = [
    privacy && { label: "Privacy guard", note: privacy.people || privacy.plates ? `${privacy.people + privacy.plates} blurred` : "none seen", guard: true },
    { label: "Plan", note: open ? "Muse Spark Open" : planner ? "Muse Spark" : "rules", guard: false },
    { label: "Tool calls", note: String(toolCalls), guard: false },
    { label: "Verify", note: verifies ? `${verifies}×` : "—", guard: true },
    pictures > 0 && { label: "Picture", note: `${pictures} after`, guard: false },
  ].filter(Boolean) as { label: string; note: string; guard: boolean }[];
  return (
    <details id="how" open data-report-section className="group scroll-mt-28 overflow-hidden rounded-2xl bg-trace text-trace-fg">
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 border-b border-trace-line px-4 py-3 sm:px-5 [&::-webkit-details-marker]:hidden">
        <div>
        <p className="font-mono text-[11px] tracking-widest text-trace-muted uppercase">
          Agent trace · {open ? "Muse Spark Open" : planner ? "Muse Spark" : "Rule-based plan"}
        </p>
        <h2 id="agent-trace" className="text-lg font-bold">
          How EmberScan got here
        </h2>
        <p className="mt-1 text-sm text-trace-muted">
          The agent plans, calls tools over the measured hazards and rule results, then a checker verifies every claim. It can explain
          and prioritize results but can&apos;t change them.
        </p>
        {planner && (
          <p className="mt-2 inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg bg-white/10 px-2.5 py-1 text-xs">
            <span className="font-semibold">
              Planned by {open ? "Muse Spark Open, Meta's open-weight model, on Baseten" : "Muse Spark on the Meta Model API"}
            </span>
            {typeof planner.seconds === "number" && <span className="text-trace-muted">in {Math.round(planner.seconds)} s</span>}
            <span className="font-mono text-[11px] text-trace-muted">{planner.model}</span>
          </p>
        )}
        <ol className="mt-3 flex flex-wrap items-center gap-1.5 text-xs" aria-label="The agent loop">
          {loop.map((s, i) => (
            <li key={s.label} className="flex items-center gap-1.5">
              {i > 0 && (
                <span aria-hidden className="text-trace-muted">
                  →
                </span>
              )}
              <span
                className={cx(
                  "rounded-full border px-2 py-0.5",
                  s.guard ? "border-trace-fg font-semibold" : "border-trace-line",
                )}
              >
                {s.label} <span className="font-normal text-trace-muted">· {s.note}</span>
              </span>
            </li>
          ))}
        </ol>
        <p className="mt-1.5 text-[11px] text-trace-muted">Outlined steps are guardrails written in code: the agent can&apos;t skip or change them.</p>
        </div>
        <span aria-hidden className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/10 transition-transform group-open:rotate-180">
          <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M4 6l4 4 4-4" />
          </svg>
        </span>
      </summary>
      {steps.length === 0 ? (
        <p className="px-5 py-4 text-sm text-trace-muted">No agent trace in this report.</p>
      ) : (
        <ol className="relative px-4 py-4 sm:px-5">
          {steps.map((s, i) => {
            const k = KIND[s.kind] ?? KIND.note;
            const isCall = s.kind === "tool_call";
            return (
              <li key={i} className="relative flex gap-3 pb-4 last:pb-0">
                {i < steps.length - 1 && <span className="absolute top-6 bottom-0 left-[11px] w-px bg-trace-line" aria-hidden />}
                <span
                  className={cx(
                    "relative z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-[10px]",
                    s.kind === "verify" ? "border-trace-fg bg-trace-fg text-trace" : "border-trace-line bg-trace text-trace-muted",
                  )}
                  aria-hidden
                >
                  {s.kind === "verify" ? <IconCheck size={14} /> : i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <span className={cx("inline-block rounded border px-1.5 py-px font-mono text-[10px] tracking-wider uppercase", k.cls)}>
                    {k.label}
                  </span>
                  <p className={cx("mt-1 break-words", isCall ? "font-mono text-[13px] text-trace-fg" : "text-sm")}>
                    {isCall && <span className="text-trace-muted">→ </span>}
                    {s.summary}
                  </p>
                  {s.detail && Object.keys(s.detail).length > 0 && (
                    <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 rounded-lg bg-black/25 px-2.5 py-1.5 font-mono text-xs">
                      {Object.entries(s.detail).map(([key, v]) => (
                        <div key={key} className="contents">
                          <dt className="text-trace-muted">{key}</dt>
                          <dd className="m-0 break-words">
                            <DetailValue value={v} />
                          </dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
      <p className="border-t border-trace-line px-4 py-2 font-mono text-[11px] text-trace-muted sm:px-5">
        {steps.length} steps · {toolCalls} tool calls
        {typeof cost?.calls === "number" && ` · ${cost.calls} model calls`}
        {typeof cost?.spent_usd === "number" && ` · $${cost.spent_usd.toFixed(2)} spent`}
      </p>
    </details>
  );
}
