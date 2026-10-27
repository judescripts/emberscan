import type { Hazard, Report } from "@/lib/report-types";
import { hazardStatus } from "@/lib/score";
import { toneFor } from "../ui";
import { ThumbStrip, type Thumb } from "./thumb-strip";

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
  const thumbs: Thumb[] = hazardIds
    .map((id) => ({ h: report.hazards.find((x) => x.id === id), n: report.hazards.findIndex((x) => x.id === id) + 1 }))
    .filter((x): x is { h: Hazard; n: number } => Boolean(x.h))
    .map(({ h, n }) => {
      const path = h.evidence[0]?.image_path;
      return {
        id: h.id,
        n,
        label: h.label,
        tone: toneFor(hazardStatus(h.id, report.results)),
        src: path && imageBase ? `${imageBase}/${path.split("/").map(encodeURIComponent).join("/")}` : null,
      };
    });
  if (!thumbs.length) return null;
  return <ThumbStrip thumbs={thumbs} max={max} />;
}
