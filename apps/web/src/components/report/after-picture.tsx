import type { Fix, Report } from "@/lib/report-types";
import { projectedScore } from "@/lib/score";
import { cx } from "../ui";
import { HideIfBroken } from "./hide-if-broken";

/**
 * Now vs. the goal, side by side: the real video frame and the same frame edited by Muse Image to
 * show what the fix should look like. The preview is marked as AI on the picture itself (badge,
 * dashed frame) and in the caption; it is never measured and never changes the score.
 */
export function AfterPicture({ fix, report, imageBase }: { fix: Fix; report: Report; imageBase: string | null }) {
  const ill = fix.illustration;
  if (!ill || !imageBase) return null;
  const url = (p: string) => `${imageBase}/${p.split("/").map(encodeURIComponent).join("/")}`;
  const W = Number(report.video.width) || 1280;
  const H = Number(report.video.height) || 720;
  const hazardNo = report.hazards.findIndex((h) => h.id === ill.hazard_id) + 1;
  // What the fix removes: the fix's hazards SAM boxed on this frame, outlined on "Now" and
  // dashed on "After" so the eye goes to the spot that changed. Tiny boxes get padded to be seen.
  const pad = Math.round(W * 0.03);
  const boxes = report.hazards
    .filter((h) => fix.hazard_ids.includes(h.id))
    .flatMap((h) => h.evidence.filter((e) => e.frame_index === ill.frame_index).map((e) => ({ id: h.id, b: e.bbox })))
    .map(({ id, b }) => {
      const minW = W * 0.12;
      const grow = (lo: number, hi: number, min: number, max: number) => {
        const extra = Math.max(pad, (min - (hi - lo)) / 2);
        return [Math.max(0, lo - extra), Math.min(max, hi + extra)];
      };
      const [x0, x1] = grow(b.left, b.right, minW, W);
      const [y0, y1] = grow(b.top, b.bottom, minW, H);
      return { id, x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
    });
  const stroke = Math.max(3, Math.round(W / 160));
  const projected = projectedScore(report, [fix]);
  return (
    <HideIfBroken>
      <figure className="m-0 mt-3">
        <div className="grid grid-cols-2 gap-2">
          {[
            { src: url(ill.before_path), label: "Now · your video", now: true, alt: `Video frame ${ill.frame_index}, now` },
            {
              src: url(ill.after_path),
              label: "Goal · AI preview",
              now: false,
              alt: `AI-generated preview, not a photo: what it should look like after: ${fix.title}`,
            },
          ].map((p) => (
            <div
              key={p.label}
              className={cx(
                "relative overflow-hidden rounded-xl bg-soft",
                !p.now && "outline-2 -outline-offset-2 outline-white/90 outline-dashed",
              )}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={p.src} alt={p.alt} width={W} height={H} loading="lazy" className="block h-auto w-full" />
              {boxes.length > 0 && (
                <svg
                  viewBox={`0 0 ${W} ${H}`}
                  preserveAspectRatio="none"
                  className="pointer-events-none absolute inset-0 h-full w-full"
                  aria-hidden
                >
                  {boxes.map((r) => (
                    <g key={r.id}>
                      <rect
                        x={r.x}
                        y={r.y}
                        width={r.w}
                        height={r.h}
                        rx={stroke * 3}
                        fill="none"
                        stroke="black"
                        strokeOpacity={0.5}
                        strokeWidth={stroke * 2}
                      />
                      <rect
                        x={r.x}
                        y={r.y}
                        width={r.w}
                        height={r.h}
                        rx={stroke * 3}
                        fill="none"
                        stroke={p.now ? "#f97316" : "white"}
                        strokeWidth={stroke}
                        strokeDasharray={p.now ? undefined : `${stroke * 3} ${stroke * 2}`}
                      />
                    </g>
                  ))}
                </svg>
              )}
              <span className="absolute top-2 left-2 rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-semibold text-white">
                {p.label}
              </span>
              {!p.now && (
                <span className="absolute inset-x-2 bottom-2 flex items-center justify-center gap-1 rounded-lg bg-black/70 px-2 py-1 text-center text-[11px] font-bold tracking-wide text-white uppercase">
                  <svg viewBox="0 0 16 16" className="h-3 w-3 shrink-0" fill="currentColor" aria-hidden>
                    <path d="M8 0l1.8 5.2L15 7l-5.2 1.8L8 14l-1.8-5.2L1 7l5.2-1.8z" />
                  </svg>
                  AI-generated preview · not a photo
                </span>
              )}
            </div>
          ))}
        </div>
        <figcaption className="mt-1.5 text-xs text-muted">
          <span className="font-semibold text-ink">AI preview by Muse Image, not a measurement.</span> What this fix should look like, drawn
          from frame {ill.frame_index}
          {hazardNo > 0 && (
            <>
              {" "}
              of{" "}
              <a href={`#${ill.hazard_id}`} className="underline underline-offset-2">
                evidence {hazardNo}
              </a>
            </>
          )}
          .{boxes.length > 0 && " Orange: what the scan found. Dashed: the same spot in the preview."}
          {ill.checked && " Muse Spark checked that the preview shows this fix."} The score only changes when a rescan confirms the work
          {projected > report.score.score && (
            <>
              : projected{" "}
              <strong className="text-ink">
                {report.score.score} → {projected}
              </strong>
            </>
          )}
          .
        </figcaption>
      </figure>
    </HideIfBroken>
  );
}
