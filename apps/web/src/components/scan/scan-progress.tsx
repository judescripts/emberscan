"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";
import { deleteScan, loadSampleReport } from "@/app/actions";
import { stageRows, type StageState } from "@/lib/pipeline";
import type { WorkerStage } from "@/lib/report-types";
import { IconCheck, IconX } from "../icons";
import { buttonClass, cx } from "../ui";

export interface ScanSnapshot {
  id: string;
  status: string;
  stage: string | null;
  progress: number;
  stages: WorkerStage[];
  error: string | null;
  hasReport: boolean;
  isSample: boolean;
  workerReachable?: boolean;
  workerError?: string | null;
}

interface LogLine {
  t: number;
  stage: string;
  text: string;
}

const POLL_MS = 1500;

function StateIcon({ state }: { state: StageState }) {
  const base = "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2";
  if (state === "done")
    return (
      <span className={cx(base, "border-pass bg-pass text-surface")}>
        <IconCheck size={15} />
      </span>
    );
  if (state === "failed")
    return (
      <span className={cx(base, "border-fail bg-fail text-surface")}>
        <IconX size={15} />
      </span>
    );
  if (state === "running")
    return (
      <span className={cx(base, "border-brand")}>
        <span className="es-pulse h-2.5 w-2.5 rounded-full bg-brand" />
      </span>
    );
  return <span className={cx(base, state === "skipped" ? "border-dashed border-line" : "border-line")} />;
}

const STATE_WORDS: Record<StageState, string> = {
  done: "Done",
  running: "Running",
  pending: "Waiting",
  failed: "Failed",
  skipped: "Skipped",
};

export function ScanProgress({ initial, buildingId }: { initial: ScanSnapshot; buildingId: string }) {
  const router = useRouter();
  const [snap, setSnap] = useState(initial);
  const [log, setLog] = useState<LogLine[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const lastDetail = useRef(new Map<string, string>());
  const [samplePending, startSample] = useTransition();
  const finished = snap.status === "done" || snap.status === "failed";

  useEffect(() => {
    if (finished) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const res = await fetch(`/api/scans/${initial.id}`, { cache: "no-store" });
        if (res.ok) {
          const next = (await res.json()) as ScanSnapshot;
          if (!alive) return;
          setSnap(next);
          const fresh: LogLine[] = [];
          for (const s of next.stages ?? []) {
            if (s.detail && lastDetail.current.get(s.name) !== s.detail) {
              lastDetail.current.set(s.name, s.detail);
              fresh.push({ t: Date.now(), stage: s.name, text: s.detail });
            }
          }
          if (fresh.length) setLog((l) => [...l, ...fresh].slice(-40));
          if (next.status === "done" || next.status === "failed") return;
        }
      } catch {
        /* keep polling */
      }
      if (alive) timer = setTimeout(tick, POLL_MS);
    };
    timer = setTimeout(tick, 300);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [finished, initial.id]);

  useEffect(() => {
    if (finished) return;
    const t0 = Date.now();
    const id = setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(id);
  }, [finished]);

  useEffect(() => {
    if (snap.status === "done" && snap.hasReport && !initial.hasReport) {
      const id = setTimeout(() => router.push(`/report/${snap.id}`), 1500);
      return () => clearTimeout(id);
    }
  }, [snap.status, snap.hasReport, snap.id, initial.hasReport, router]);

  const rows = stageRows(snap.stages, snap.stage, snap.status);
  const pct = Math.round(Math.min(1, Math.max(0, snap.progress ?? 0)) * 100);

  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-2xl border border-line bg-surface p-4">
        <div className="flex items-baseline justify-between gap-3">
          <p className="font-semibold text-ink" aria-live="polite">
            {snap.status === "done"
              ? "Scan finished"
              : snap.status === "failed"
                ? "Scan failed"
                : snap.status === "queued"
                  ? "Queued: waiting for the pipeline"
                  : `Working: ${rows.find((r) => r.state === "running")?.title ?? "processing"}`}
          </p>
          <span className="font-mono text-sm text-muted tabular-nums">
            {pct}%{!finished && ` · ${elapsed}s`}
          </span>
        </div>
        <div
          className="mt-2 h-3 overflow-hidden rounded-full bg-soft"
          role="progressbar"
          aria-label="Scan progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
        >
          <div
            className={cx("h-full rounded-full transition-[width] duration-500", snap.status === "failed" ? "bg-fail" : "bg-brand", !finished && "es-stripes")}
            style={{ width: `${Math.max(pct, 3)}%` }}
          />
        </div>
        {snap.workerReachable === false && (
          <p className="mt-2 text-sm text-review">Lost contact with the pipeline. Still trying… ({snap.workerError})</p>
        )}
      </div>

      <ol className="flex flex-col">
        {rows.map((r, i) => (
          <li key={r.name} className="relative flex gap-3 pb-4 last:pb-0">
            {i < rows.length - 1 && (
              <span className={cx("absolute top-7 bottom-0 left-[13px] w-0.5", r.state === "done" ? "bg-pass" : "bg-line")} aria-hidden />
            )}
            <StateIcon state={r.state} />
            <div
              className={cx(
                "min-w-0 flex-1 rounded-xl px-3 py-2",
                r.state === "running" ? "border border-brand bg-surface" : "border border-transparent",
              )}
            >
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className={cx("font-semibold", r.state === "pending" ? "text-muted" : "text-ink")}>{r.title}</span>
                <span className="font-mono text-[11px] text-muted">{r.tool}</span>
                <span className="sr-only">: {STATE_WORDS[r.state]}</span>
              </div>
              {r.detail ? (
                <p className={cx("mt-0.5 font-mono text-xs break-all whitespace-pre-wrap", r.state === "failed" ? "text-fail" : "text-ink")}>{r.detail}</p>
              ) : (
                <p className="mt-0.5 text-xs text-muted">{r.what}</p>
              )}
            </div>
          </li>
        ))}
      </ol>

      {log.length > 0 && (
        <section aria-label="Pipeline activity" className="rounded-2xl bg-trace p-3 font-mono text-xs text-trace-fg">
          <p className="mb-1 text-[10px] tracking-widest text-trace-muted uppercase">Live pipeline log</p>
          <ol className="flex max-h-48 flex-col gap-0.5 overflow-y-auto">
            {log.map((l, i) => (
              <li key={i}>
                <span className="text-trace-muted">[{l.stage}]</span> {l.text}
              </li>
            ))}
          </ol>
        </section>
      )}

      {snap.status === "failed" && (
        <div role="alert" className="rounded-xl border border-fail bg-fail-soft p-3 text-sm">
          <p className="font-semibold text-fail">The pipeline stopped</p>
          <p className="mt-0.5 break-all whitespace-pre-wrap text-ink">{snap.error ?? "No reason given."}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Link href={`/scan?building=${buildingId}`} className={buttonClass("primary")}>
              Try again
            </Link>
            <button type="button" className={buttonClass("secondary")} disabled={samplePending} onClick={() => startSample(() => loadSampleReport(buildingId))}>
              Load sample report
            </button>
            <button type="button" className={buttonClass("ghost")} disabled={samplePending} onClick={() => startSample(() => deleteScan(snap.id))}>
              Remove this failed scan
            </button>
          </div>
        </div>
      )}

      {snap.status === "done" && snap.hasReport && (
        <div className="flex flex-wrap items-center gap-3">
          <Link href={`/report/${snap.id}`} className={buttonClass("primary")}>
            Open the report
          </Link>
          {!initial.hasReport && <span className="text-sm text-muted">Opening automatically…</span>}
        </div>
      )}
    </div>
  );
}
