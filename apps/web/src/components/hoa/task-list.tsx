"use client";

import Link from "next/link";
import { useState } from "react";
import type { FixStatus, Responsibility } from "@/lib/db/schema";
import type { RuleStatus } from "@/lib/report-types";
import { filterTasks, STATUS_LABEL } from "@/lib/tasks";
import { formatDate } from "@/lib/format";
import { Citation, cx, inputClass, Pill, StatusPill } from "../ui";

export interface TaskRow {
  id: string;
  buildingId: string;
  buildingLabel: string;
  reportId: string | null;
  title: string;
  ruleId: string;
  citationLabel: string | null;
  citationUrl: string | null;
  ruleStatus: RuleStatus | null;
  responsibility: Responsibility;
  owner: string;
  status: FixStatus;
  required: boolean;
  lastNote: { text: string; at: string; by: string } | null;
}

const STATUSES: (FixStatus | "active")[] = ["active", "open", "progress", "fixed", "verified", "wontfix"];

export function TaskList({ tasks }: { tasks: TaskRow[] }) {
  const [resp, setResp] = useState<"all" | Responsibility>("all");
  const [status, setStatus] = useState<FixStatus | "active" | "all">("active");
  const shown = filterTasks(tasks, resp, status);
  return (
    <div>
      <div className="mb-3 grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="task-owner" className="text-xs font-semibold text-muted">
            Responsible
          </label>
          <select id="task-owner" value={resp} onChange={(e) => setResp(e.target.value as typeof resp)} className={cx(inputClass, "mt-1")}>
            <option value="all">Everyone</option>
            <option value="HOA">HOA</option>
            <option value="Owner">Homeowners</option>
            <option value="Unclear">Unclear</option>
          </select>
        </div>
        <div>
          <label htmlFor="task-status" className="text-xs font-semibold text-muted">
            Status
          </label>
          <select id="task-status" value={status} onChange={(e) => setStatus(e.target.value as typeof status)} className={cx(inputClass, "mt-1")}>
            <option value="all">Any status</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s === "active" ? "Still to do" : STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </div>
      </div>
      <p className="mb-2 text-xs text-muted" aria-live="polite">
        {shown.length} of {tasks.length} tasks
      </p>
      {shown.length === 0 ? (
        <p className="text-sm text-muted">No tasks match.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {shown.map((t) => (
            <li key={t.id} className="rounded-xl border border-line p-3">
              <div className="flex flex-wrap items-center gap-2">
                {t.ruleStatus && <StatusPill status={t.ruleStatus} />}
                <Pill tone={t.status === "verified" ? "pass" : "neutral"}>{STATUS_LABEL[t.status]}</Pill>
                <span className="text-xs text-muted">
                  {t.responsibility === "Owner" ? "Homeowner" : t.responsibility} · {t.required ? "Required" : "Recommended"}
                </span>
              </div>
              <p className="mt-1 font-semibold text-ink">
                {t.reportId ? (
                  <Link href={`/report/${t.reportId}#all-fixes`} className="underline decoration-line underline-offset-2 hover:decoration-brand">
                    {t.title}
                  </Link>
                ) : (
                  t.title
                )}
              </p>
              <p className="text-sm text-muted">
                {t.buildingLabel} · Owner: {t.owner || "not assigned"}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-3">
                <span className="font-mono text-xs text-muted">{t.ruleId}</span>
                {t.citationUrl && t.citationLabel && <Citation href={t.citationUrl} label={t.citationLabel} />}
              </div>
              {t.lastNote && (
                <p className="mt-1 text-xs text-muted">
                  Last note ({formatDate(t.lastNote.at)}, {t.lastNote.by}):{" "}
                  {t.lastNote.text}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
