"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { researchBuilding } from "@/app/actions";
import type { BuildingNote } from "@/lib/report-types";
import { buttonClass, cx } from "./ui";

const ZONE_TONE: Record<string, string> = {
  "Very High": "bg-fail-soft text-fail",
  High: "bg-review-soft text-review",
  Moderate: "bg-soft text-ink",
};

/** Small zone chip for building cards. */
export function ZoneChip({ note }: { note: BuildingNote | null }) {
  if (!note?.hazard_class) return null;
  return (
    <span className={cx("rounded-full px-2 py-0.5 text-xs font-semibold", ZONE_TONE[note.hazard_class] ?? "bg-soft")}>
      {note.hazard_class} fire hazard{note.responsibility ? ` · ${note.responsibility}` : ""}
    </span>
  );
}

/**
 * The address research note: summary, cited facts, what to confirm, sources and the agent's steps.
 * Runs the research once on its own when the building has an address but no note yet.
 */
export function BuildingNotePanel({
  buildingId,
  address,
  note,
  compact = false,
}: {
  buildingId: string;
  address: string;
  note: BuildingNote | null;
  compact?: boolean;
}) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  const run = () =>
    start(async () => {
      setError(null);
      const res = await researchBuilding(buildingId);
      if (!res.ok) setError(res.error ?? "Research failed.");
    });

  useEffect(() => {
    if (address && !note && !started.current) {
      started.current = true;
      run();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [address, note]);

  if (!address) return null;

  if (pending && !note) {
    return (
      <div className="rounded-xl bg-soft p-3 text-sm" role="status">
        <p className="font-semibold text-ink">
          <span className="es-pulse">Researching {address}…</span>
        </p>
        <p className="text-xs text-muted">Looking up the fire hazard zone, which law applies and recent fires nearby.</p>
      </div>
    );
  }
  if (!note) {
    return (
      <div className="rounded-xl bg-soft p-3 text-sm">
        <p className="text-muted">{error ?? "No research note yet."}</p>
        <button type="button" className={cx(buttonClass("secondary"), "mt-2")} onClick={run} disabled={pending}>
          Research this address
        </button>
      </div>
    );
  }

  const sourceName = (id: string) => note.sources.find((s) => s.id === id)?.name ?? id;
  return (
    <section className="rounded-xl border border-line bg-surface p-3 text-sm" aria-label={`Research note for ${address}`}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">About this address</h3>
        <ZoneChip note={note} />
      </div>
      {note.summary && <p className="mt-1.5 text-ink">{note.summary}</p>}
      {!compact && note.facts.length > 0 && (
        <dl className="mt-2 grid gap-1.5">
          {note.facts.map((f) => (
            <div key={f.label + f.value} className="grid gap-0.5 sm:grid-cols-[10rem_1fr] sm:gap-3">
              <dt className="font-semibold text-ink">{f.label}</dt>
              <dd className="text-muted">
                {f.value} <span className="text-xs">({sourceName(f.source_id)})</span>
              </dd>
            </div>
          ))}
        </dl>
      )}
      {!compact && note.to_check.length > 0 && (
        <div className="mt-2">
          <p className="font-semibold text-ink">Worth confirming</p>
          <ul className="ml-4 list-disc text-muted">
            {note.to_check.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      )}
      {!compact && (
        <details className="mt-2 text-xs text-muted">
          <summary className="cursor-pointer font-semibold">Sources and how EmberScan got here</summary>
          <ul className="mt-1 flex flex-col gap-0.5">
            {note.sources.map((s) => (
              <li key={s.id}>
                <a href={s.url} target="_blank" rel="noreferrer" className="underline underline-offset-2">
                  {s.name}
                </a>
              </li>
            ))}
          </ul>
          <ol className="mt-2 ml-4 list-decimal">
            {note.trace.map((t, i) => (
              <li key={i}>{t.summary}</li>
            ))}
          </ol>
          <p className="mt-1">
            {note.model ? `Written by ${note.model}` : "Built from the lookups (agent unavailable)"} ·{" "}
            {new Date(note.generated_at).toLocaleDateString()} · ${note.cost_usd.toFixed(4)}
          </p>
        </details>
      )}
      <p className="mt-2 text-xs text-muted">{note.disclaimer}</p>
      {!compact && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <button type="button" className={buttonClass("ghost")} onClick={run} disabled={pending}>
            {pending ? "Refreshing…" : "Refresh research"}
          </button>
          {error && <span className="text-xs text-fail">{error}</span>}
        </div>
      )}
    </section>
  );
}
