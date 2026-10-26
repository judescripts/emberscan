"use client";

import { useState, useTransition } from "react";
import { updateTask } from "@/app/actions";
import type { FixStatus } from "@/lib/db/schema";
import { STATUS_LABEL, USER_STATUSES } from "@/lib/tasks";
import { buttonClass, cx, inputClass } from "../ui";

export interface TaskView {
  id: string;
  status: FixStatus;
  owner: string;
  notes: { text: string; at: string; by: string }[];
}

function noteDate(iso: string) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
}

/** Status chips, owner and dated notes for one fix. "Verified" is shown but only a rescan can set it. */
export function FixTracker({ task, readOnly }: { task: TaskView | null; readOnly?: boolean }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [owner, setOwner] = useState(task?.owner ?? "");
  const [note, setNote] = useState("");
  const [wontfixOpen, setWontfixOpen] = useState(false);
  const [reason, setReason] = useState("");

  if (!task) return <p className="text-xs text-muted">Tracking starts once this scan is attached to a building.</p>;

  const run = (u: Parameters<typeof updateTask>[1], after?: () => void) => {
    setError(null);
    start(async () => {
      const res = await updateTask(task.id, u);
      if (!res.ok) setError(res.error ?? "Couldn't save.");
      else after?.();
    });
  };

  const idBase = `task-${task.id}`;
  return (
    <div className="flex flex-col gap-3 border-t border-line pt-3">
      <fieldset disabled={pending || readOnly}>
        <legend className="mb-1.5 text-xs font-semibold text-muted">Status</legend>
        <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Fix status">
          {USER_STATUSES.map((s) => {
            const active = task.status === s;
            return (
              <button
                key={s}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => {
                  if (active) return;
                  if (s === "wontfix") setWontfixOpen(true);
                  else run({ status: s });
                }}
                className={cx(
                  "rounded-full border px-2.5 py-1 text-xs font-semibold",
                  active ? "border-brand bg-brand text-brand-fg" : "border-line bg-surface text-ink hover:bg-soft",
                )}
              >
                {STATUS_LABEL[s]}
              </button>
            );
          })}
          <span
            role="radio"
            aria-checked={task.status === "verified"}
            aria-disabled
            title="Only a rescan can verify a fix"
            className={cx(
              "rounded-full border px-2.5 py-1 text-xs font-semibold",
              task.status === "verified" ? "border-pass bg-pass-soft text-pass" : "border-dashed border-line text-muted",
            )}
          >
            {STATUS_LABEL.verified}
          </span>
        </div>
        {task.status !== "verified" && <p className="mt-1 text-[11px] text-muted">Verified is set by a rescan, not by hand.</p>}
      </fieldset>

      {wontfixOpen && (
        <div className="rounded-xl border border-line bg-soft p-3">
          <label htmlFor={`${idBase}-reason`} className="text-xs font-semibold text-ink">
            Why won&apos;t this be fixed? (required)
          </label>
          <textarea
            id={`${idBase}-reason`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            className={cx(inputClass, "mt-1")}
            placeholder="e.g. Plant is in the neighbor's yard; HOA will raise it with them"
          />
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              className={buttonClass("primary")}
              disabled={!reason.trim() || pending}
              onClick={() =>
                run({ status: "wontfix", note: reason }, () => {
                  setWontfixOpen(false);
                  setReason("");
                })
              }
            >
              Save as Won&apos;t fix
            </button>
            <button type="button" className={buttonClass("ghost")} onClick={() => setWontfixOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor={`${idBase}-owner`} className="text-xs font-semibold text-muted">
            Owner
          </label>
          <div className="mt-1 flex gap-2">
            <input
              id={`${idBase}-owner`}
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              className={inputClass}
              placeholder="Who's on it?"
              disabled={readOnly}
            />
            <button
              type="button"
              className={buttonClass("secondary")}
              disabled={pending || owner === task.owner || readOnly}
              onClick={() => run({ owner })}
            >
              Save
            </button>
          </div>
        </div>
        <div>
          <label htmlFor={`${idBase}-note`} className="text-xs font-semibold text-muted">
            Add a note
          </label>
          <div className="mt-1 flex gap-2">
            <input
              id={`${idBase}-note`}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className={inputClass}
              placeholder="e.g. Landscaper booked for Nov 2"
              disabled={readOnly}
            />
            <button
              type="button"
              className={buttonClass("secondary")}
              disabled={pending || !note.trim() || readOnly}
              onClick={() => run({ note }, () => setNote(""))}
            >
              Add
            </button>
          </div>
        </div>
      </div>

      {error && (
        <p role="alert" className="text-sm font-semibold text-fail">
          {error}
        </p>
      )}

      {task.notes.length > 0 && (
        <ol className="flex flex-col gap-1 text-xs">
          {[...task.notes].reverse().map((n, i) => (
            <li key={i} className="flex gap-2">
              <time dateTime={n.at} className="shrink-0 text-muted tabular-nums">
                {noteDate(n.at)}
              </time>
              <span className="text-ink">
                {n.text} <span className="text-muted">· {n.by}</span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
