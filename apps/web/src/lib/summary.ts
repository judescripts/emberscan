import { formatRange } from "./format";
import type { Report } from "./report-types";

/** One-line proof of pipeline work for cards: what was tracked, and the closest measured hazard. */
export function pipelineSummary(report: Report): { tracked: string; closest: string | null } {
  const frames = new Set(report.hazards.flatMap((h) => h.frames)).size;
  const tracked = `${report.hazards.length} hazard${report.hazards.length === 1 ? "" : "s"} tracked across ${frames} frames`;
  const measured = report.hazards.filter((h) => h.distance_ft);
  if (measured.length === 0) return { tracked, closest: null };
  const c = measured.reduce((a, b) => (b.distance_ft!.min < a.distance_ft!.min ? b : a));
  return { tracked, closest: `${c.label}: about ${formatRange(c.distance_ft!)} from the wall` };
}

export function firstCitation(report: Report): string | null {
  const r = report.results.find((x) => x.status === "fail") ?? report.results.find((x) => x.status === "needs-review");
  return r ? `${r.title} (${r.citation_label})` : null;
}
