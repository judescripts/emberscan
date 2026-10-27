import type { Fix, Report } from "@/lib/report-types";

/**
 * Now vs. after the fix, side by side: the clean video frame and the same frame edited by Muse Image.
 * Always labelled as an AI illustration; it is never measured and never counts as evidence.
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
  return (
    <figure className="m-0 mt-3">
      <div className="grid grid-cols-2 gap-2">
        {[
          { src: url(ill.before_path), label: "Now", now: true, alt: `Video frame ${ill.frame_index} before the fix` },
          { src: url(ill.after_path), label: "After the fix", now: false, alt: `AI illustration of the same view after: ${fix.title}` },
        ].map((p) => (
          <div key={p.label} className="relative overflow-hidden rounded-xl bg-soft">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={p.src} alt={p.alt} width={W} height={H} loading="lazy" className="block h-auto w-full" />
            {boxes.length > 0 && (
              <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden>
                {boxes.map((r) => (
                  <g key={r.id}>
                    <rect x={r.x} y={r.y} width={r.w} height={r.h} rx={stroke * 3} fill="none" stroke="black" strokeOpacity={0.5} strokeWidth={stroke * 2} />
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
            <span className="absolute top-2 left-2 rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-semibold text-white">{p.label}</span>
          </div>
        ))}
      </div>
      <figcaption className="mt-1.5 text-xs text-muted">
        <span className="font-semibold text-ink">AI illustration (Muse Image), not a measurement.</span> It edits frame {ill.frame_index}
        {hazardNo > 0 && (
          <>
            {" "}
            of{" "}
            <a href={`#${ill.hazard_id}`} className="underline underline-offset-2">
              evidence {hazardNo}
            </a>
          </>
        )}{" "}
        to show what this fix could look like.
        {boxes.length > 0 && " The orange outline is what the scan found; the dashed one marks the same spot after."} Rescan after the
        work to check it.
      </figcaption>
    </figure>
  );
}
