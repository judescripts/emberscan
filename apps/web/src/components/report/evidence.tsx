import { formatTimestamp, framesTracked, hazardMeasurements, sideWords, zoneWords } from "@/lib/format";
import type { Hazard, Report } from "@/lib/report-types";
import { hazardStatus } from "@/lib/score";
import { StatusPill, toneFor, cx } from "../ui";
import { EvidenceImage, type Reason } from "./evidence-image";

const RING = { fail: "border-fail", review: "border-review", pass: "border-pass", neutral: "border-muted" } as const;
const BG = { fail: "bg-fail", review: "bg-review", pass: "bg-pass", neutral: "bg-muted" } as const;

/** Where in the walkaround SAM 3.1 kept this object: one tick per tracked frame. */
function TrackStrip({ frames, totalFrames, tone }: { frames: number[]; totalFrames: number; tone: keyof typeof BG }) {
  const total = Math.max(totalFrames, (frames.length ? Math.max(...frames) : 0) + 1, 1);
  const runs: [number, number][] = [];
  [...frames]
    .sort((a, b) => a - b)
    .forEach((f) => {
      const last = runs[runs.length - 1];
      if (last && f === last[1] + 1) last[1] = f;
      else runs.push([f, f]);
    });
  return (
    <div>
      <div className="relative h-3 w-full overflow-hidden rounded-full bg-soft" aria-hidden>
        {runs.map(([a, b]) => (
          <span
            key={a}
            className={cx("absolute inset-y-0", BG[tone])}
            style={{ left: `${(a / total) * 100}%`, width: `${Math.max(((b - a + 1) / total) * 100, 0.6)}%` }}
          />
        ))}
      </div>
      <div className="mt-0.5 flex justify-between text-[10px] text-muted" aria-hidden>
        <span>start of video</span>
        <span>end</span>
      </div>
    </div>
  );
}

function Frame({ hazard, report, imageBase, n, tone }: { hazard: Hazard; report: Report; imageBase: string | null; n: number; tone: keyof typeof BG }) {
  const ev = hazard.evidence[0];
  const W = Number(report.video.width) || 1280;
  const H = Number(report.video.height) || 720;
  const box = ev
    ? {
        left: `${(ev.bbox.left / W) * 100}%`,
        top: `${(ev.bbox.top / H) * 100}%`,
        width: `${((ev.bbox.right - ev.bbox.left) / W) * 100}%`,
        height: `${((ev.bbox.bottom - ev.bbox.top) / H) * 100}%`,
      }
    : null;
  const src = ev?.image_path && imageBase ? `${imageBase}/${ev.image_path.split("/").map(encodeURIComponent).join("/")}` : null;
  if (src) {
    // Annotated frame from the worker: mask, wall line and a caption strip under the frame are
    // drawn in, so nothing is laid over it here. Shown whole (no crop). Same-origin proxy route.
    const reasons: Reason[] = report.results
      .filter((r) => r.hazard_ids.includes(hazard.id))
      .map((r) => ({ ruleId: r.rule_id, title: r.title, status: r.status as Reason["status"], reason: r.reason }));
    return (
      <figure className="m-0">
        <EvidenceImage
          src={src}
          alt={`Video frame ${ev!.frame_index} showing ${hazard.label}`}
          measurement={hazardMeasurements(hazard)[0] ?? null}
          reasons={reasons}
          width={W}
          height={Math.round(H * 1.06)} // frame plus the caption strip the worker adds under it
        />
        <figcaption className="mt-2.5 flex items-start gap-2 text-xs text-muted">
          <span className={cx("shrink-0 rounded px-1.5 py-0.5 font-bold text-surface", BG[tone])}>{n}</span>
          <span className="pt-0.5">
            Frame {ev!.frame_index} at {formatTimestamp(ev!.timestamp_ms)} · SAM 3.1 object #{hazard.track_id} for “
            {hazard.concept}”
            {typeof hazard.sam_confidence === "number" && ` · match score ${Math.round(hazard.sam_confidence * 100)}%`}
          </span>
        </figcaption>
      </figure>
    );
  }
  return (
    <figure className="m-0">
      <div className="relative w-full overflow-hidden rounded-xl bg-soft" style={{ aspectRatio: `${W} / ${H}` }}>
        {(
          <div
            className="absolute inset-0 flex items-end justify-start p-2 text-[11px] text-muted"
            style={{
              backgroundImage:
                "linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)",
              backgroundSize: "10% 14.3%",
            }}
          >
            <span className="rounded bg-surface/80 px-1.5 py-0.5">Frame image not in this report · box shows where SAM 3.1 found it</span>
          </div>
        )}
        {box && (
          <div className={cx("absolute rounded-sm border-2", RING[tone])} style={box} aria-hidden>
            <span className={cx("absolute -top-px -left-px rounded-br px-1.5 py-0.5 text-[11px] font-bold text-surface", BG[tone])}>
              {n} · {hazard.concept}
            </span>
          </div>
        )}
      </div>
      {ev && (
        <figcaption className="mt-1 text-xs text-muted">
          Frame {ev.frame_index} at {formatTimestamp(ev.timestamp_ms)} · SAM 3.1 object #{hazard.track_id} for “{hazard.concept}”
          {typeof hazard.sam_confidence === "number" && ` · match score ${Math.round(hazard.sam_confidence * 100)}%`}
        </figcaption>
      )}
    </figure>
  );
}

export function EvidenceList({ report, imageBase }: { report: Report; imageBase: string | null }) {
  const samFps = Number(report.video.sam_fps) || undefined;
  const totalFrames = samFps && report.video.duration_s ? Math.round(Number(report.video.duration_s) * samFps) : 0;
  return (
    <ol className="flex flex-col gap-4">
      {report.hazards.map((h, i) => {
        const status = hazardStatus(h.id, report.results);
        const tone = toneFor(status);
        const rules = report.results.filter((r) => r.hazard_ids.includes(h.id));
        const fixes = report.fixes.filter((f) => f.hazard_ids.includes(h.id));
        return (
          <li key={h.id} id={h.id} className="target-ring scroll-mt-28 rounded-xl border border-line p-4">
            <div className="mb-3 flex items-start gap-3">
              <span className={cx("flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold text-surface", BG[tone])}>
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <h3 className="font-bold text-ink">{h.label}</h3>
                <p className="text-xs text-muted">
                  {sideWords(h.side)} · {zoneWords(h.zone)}
                  {h.zone_uncertain && " · close to a zone line"}
                </p>
              </div>
              {status && <StatusPill status={status} />}
            </div>
            <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <Frame hazard={h} report={report} imageBase={imageBase} n={i + 1} tone={tone} />
              <div className="flex flex-col gap-3 text-sm">
                <div>
                  <p className="font-semibold text-ink">{framesTracked(h.frames, samFps)}</p>
                  {totalFrames > 0 && <TrackStrip frames={h.frames} totalFrames={totalFrames} tone={tone} />}
                </div>
                <ul className="flex flex-col gap-1">
                  {hazardMeasurements(h).map((line) => (
                    <li key={line} className="text-ink">
                      {line}
                    </li>
                  ))}
                  {hazardMeasurements(h).length === 0 && <li className="text-muted">No distance measured for this one.</li>}
                </ul>
                {h.narration && (
                  <blockquote className="border-l-4 border-line pl-3 text-ink italic">
                    “{h.narration}”
                    <span className="mt-0.5 block text-xs text-muted not-italic">From your narration (Muse Voice Transcribe)</span>
                  </blockquote>
                )}
                {fixes.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-muted">{fixes.length === 1 ? "Fix for this" : "Fixes for this"}</p>
                    <ul className="mt-1 flex flex-col gap-1">
                      {fixes.map((f) => (
                        <li key={f.id}>
                          <a
                            href={`#fix-${f.id}`}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-soft px-2.5 py-1.5 text-sm font-semibold text-ink hover:bg-line"
                          >
                            <span className="text-muted">Fix {f.priority}</span>
                            <span>{f.title}</span>
                            <span aria-hidden className="text-muted">
                              →
                            </span>
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {rules.length > 0 && (
                  <ul className="flex flex-col gap-1">
                    {rules.map((r) => (
                      <li key={r.rule_id}>
                        <a href={`#rule-${r.rule_id}`} className="text-xs text-brand underline underline-offset-2">
                          {r.rule_id} · {r.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
