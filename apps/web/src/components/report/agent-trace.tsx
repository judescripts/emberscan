import type { AgentStep, Report } from "@/lib/report-types";
import { IconCheck } from "../icons";
import { cx } from "../ui";

const KIND: Record<AgentStep["kind"], { label: string; cls: string }> = {
  plan: { label: "Plan", cls: "border-trace-fg/60 text-trace-fg" },
  tool_call: { label: "Tool call", cls: "border-trace-muted text-trace-muted" },
  tool_result: { label: "Result", cls: "border-trace-muted text-trace-muted" },
  verify: { label: "Verify", cls: "border-trace-fg text-trace-fg" },
  output: { label: "Output", cls: "border-trace-fg/60 text-trace-fg" },
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
  return (
    <div className="overflow-hidden rounded-2xl bg-trace text-trace-fg">
      <div className="border-b border-trace-line px-4 py-3 sm:px-5">
        <p className="font-mono text-[11px] tracking-widest text-trace-muted uppercase">Agent trace · Muse Spark</p>
        <h2 id="agent-trace" className="text-lg font-bold">
          How EmberScan got here
        </h2>
        <p className="mt-1 text-sm text-trace-muted">
          The agent plans, calls tools over the measured hazards and rule results, then a checker verifies every claim. It can explain
          and prioritize results but can&apos;t change them.
        </p>
      </div>
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
    </div>
  );
}
