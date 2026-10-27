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
  return (
    <figure className="m-0 mt-3">
      <div className="grid grid-cols-2 gap-2">
        {[
          { src: url(ill.before_path), label: "Now", alt: `Video frame ${ill.frame_index} before the fix` },
          { src: url(ill.after_path), label: "After the fix", alt: `AI illustration of the same view after: ${fix.title}` },
        ].map((p) => (
          <div key={p.label} className="relative overflow-hidden rounded-xl bg-soft">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={p.src} alt={p.alt} width={W} height={H} loading="lazy" className="block h-auto w-full" />
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
        to show what this fix could look like. Rescan after the work to check it.
      </figcaption>
    </figure>
  );
}
