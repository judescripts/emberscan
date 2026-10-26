"use client";

import { useState } from "react";
import { rulePackStatusWords, zoneWords } from "@/lib/format";
import type { Hazard, RuleResult } from "@/lib/report-types";
import { compareStatus } from "@/lib/score";
import { Citation, cx, StatusPill } from "../ui";

const FILTERS = [
  { id: "open", label: "Open items", test: (r: RuleResult) => r.status !== "pass" },
  { id: "fail", label: "Fails", test: (r: RuleResult) => r.status === "fail" },
  { id: "review", label: "Needs review", test: (r: RuleResult) => r.status === "needs-review" },
  { id: "pass", label: "Passes", test: (r: RuleResult) => r.status === "pass" },
] as const;

export function Findings({
  results,
  hazards,
  plain,
}: {
  results: RuleResult[];
  hazards: Hazard[];
  plain: Record<string, string>;
}) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("open");
  const active = FILTERS.find((f) => f.id === filter)!;
  const shown = results.filter(active.test).sort((a, b) => compareStatus(a.status, b.status));
  const number = new Map(hazards.map((h, i) => [h.id, { n: i + 1, label: h.label }]));

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Filter findings">
        {FILTERS.map((f) => {
          const count = results.filter(f.test).length;
          const on = f.id === filter;
          return (
            <button
              key={f.id}
              type="button"
              aria-pressed={on}
              onClick={() => setFilter(f.id)}
              className={cx(
                "rounded-full border px-3 py-1 text-sm font-semibold",
                on ? "border-brand bg-brand text-brand-fg" : "border-line bg-surface text-ink hover:bg-soft",
              )}
            >
              {f.label} <span className="tabular-nums opacity-75">{count}</span>
            </button>
          );
        })}
      </div>
      {shown.length === 0 ? (
        <p className="text-sm text-muted">Nothing in this group.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {shown.map((r) => (
            <li key={r.rule_id} id={`rule-${r.rule_id}`} className="target-ring scroll-mt-20 rounded-xl border border-line bg-surface p-3">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill status={r.status} />
                <span className="font-mono text-xs text-muted">{r.rule_id}</span>
                <span className="text-xs text-muted">
                  {zoneWords(r.zone)} · {rulePackStatusWords(r.rule_status)}
                </span>
              </div>
              <h3 className="mt-1 font-semibold text-ink">{r.title}</h3>
              <p className="text-sm text-ink">{r.reason}</p>
              {plain[r.rule_id] && <p className="mt-1 text-xs text-muted">The rule in plain words: {plain[r.rule_id]}</p>}
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                <Citation href={r.citation_url} label={r.citation_label} />
                {r.hazard_ids.map((id) => {
                  const h = number.get(id);
                  return (
                    <a key={id} href={`#${id}`} className="text-xs text-brand underline underline-offset-2">
                      Evidence {h ? `${h.n}. ${h.label}` : id}
                    </a>
                  );
                })}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
