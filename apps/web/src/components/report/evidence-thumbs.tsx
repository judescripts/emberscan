import type { Hazard, Report } from "@/lib/report-types";
import { hazardStatus } from "@/lib/score";
import { cx, toneFor } from "../ui";

const BG = { fail: "bg-fail", review: "bg-review", pass: "bg-pass", neutral: "bg-muted" } as const;

/** Small evidence frames for the hazards a fix covers; each jumps to that hazard's evidence card. */
export function EvidenceThumbs({
  report,
  hazardIds,
  imageBase,
  max = 4,
}: {
  report: Report;
  hazardIds: string[];
  imageBase: string | null;
  max?: number;
}) {
  const items = hazardIds
    .map((id) => ({ h: report.hazards.find((x) => x.id === id), n: report.hazards.findIndex((x) => x.id === id) + 1 }))
    .filter((x): x is { h: Hazard; n: number } => Boolean(x.h));
  if (!items.length) return null;
  const shown = items.slice(0, max);
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2" aria-label="Evidence for this fix">
      {shown.map(({ h, n }) => {
        const tone = toneFor(hazardStatus(h.id, report.results));
        const path = h.evidence[0]?.image_path;
        const src = path && imageBase ? `${imageBase}/${path.split("/").map(encodeURIComponent).join("/")}` : null;
        return (
          <a
            key={h.id}
            href={`#${h.id}`}
            className="group relative block h-16 w-16 shrink-0 overflow-hidden rounded-lg border border-line bg-soft"
            title={`${n}. ${h.label}: see evidence`}
          >
            {src ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={src} alt="" loading="lazy" className="h-full w-full object-cover transition-transform group-hover:scale-105" />
            ) : (
              <span className="flex h-full w-full items-center justify-center px-1 text-center text-[10px] text-muted">{h.label}</span>
            )}
            <span className={cx("absolute top-1 left-1 rounded px-1 text-[10px] font-bold text-surface", BG[tone])}>{n}</span>
            <span className="sr-only">
              {n}. {h.label}: see evidence
            </span>
          </a>
        );
      })}
      {items.length > shown.length && (
        <a href={`#${items[shown.length].h.id}`} className="text-xs font-semibold text-brand underline underline-offset-2">
          +{items.length - shown.length} more
        </a>
      )}
    </div>
  );
}
