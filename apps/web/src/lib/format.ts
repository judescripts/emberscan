import type { Confidence, Fix, Hazard, Method, Range, RulePackStatus, RuleStatus, Side } from "./report-types";

// Plain-language formatting (ADR 0007): words people use, never internal codes.

/** 6 -> "6", 0.5 -> "0.5", 12.3 -> "12". */
export function formatNumber(n: number): string {
  if (!Number.isFinite(n)) return "?";
  if (Math.abs(n) >= 10) return String(Math.round(n));
  const rounded = Math.round(n * 10) / 10; // one decimal below 10
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

/** {min: 6, max: 9} -> "6–9 ft"; equal ends collapse to "6 ft". */
export function formatRange(range: Range, unit = "ft"): string {
  const lo = formatNumber(Math.min(range.min, range.max));
  const hi = formatNumber(Math.max(range.min, range.max));
  return lo === hi ? `${lo} ${unit}` : `${lo}–${hi} ${unit}`;
}

const CONFIDENCE_WORDS: Record<Confidence, string> = {
  high: "quite sure",
  medium: "fairly sure",
  low: "not sure",
};

const METHOD_WORDS: Record<Method, string> = {
  marker: "measured with the marker",
  tape: "measured with a tape",
  door: "sized from a nearby door",
  depth: "estimated from depth",
  visual: "estimated by eye from the video",
};

export function confidenceWords(c: Confidence): string {
  return CONFIDENCE_WORDS[c] ?? c;
}

export function methodWords(m: Method): string {
  return METHOD_WORDS[m] ?? m;
}

const REFERENCE_WORDS: Record<string, string> = {
  wall: "the wall",
  window: "the window",
  door: "the door",
  vent: "the vent",
  window_door_vent: "the window",
  chimney: "the chimney",
  roof: "the roof",
  ground: "the ground",
  woodpile: "the woodpile",
  propane_tank: "the propane tank",
  outbuilding: "the shed",
  attached_deck_stairs_pergola: "the deck",
  fence_attachment_point: "where the fence meets the wall",
};

export function referenceWords(ref: string | null | undefined): string {
  if (!ref) return "the wall";
  return REFERENCE_WORDS[ref] ?? `the ${ref.replace(/_/g, " ")}`;
}

/**
 * "About 6–9 ft from the chimney · fairly sure, measured with the marker".
 * Uses the clearance to a reference when there is one, else the distance from the wall.
 */
export function describeDistance(
  range: Range,
  reference: string | null | undefined,
  confidence: Confidence,
  method: Method,
): string {
  return `About ${formatRange(range)} from ${referenceWords(reference)} · ${confidenceWords(confidence)}, ${methodWords(method)}`;
}

/** Every measured line for a hazard, most specific first. */
export function hazardMeasurements(h: Hazard): string[] {
  const lines: string[] = [];
  if (h.clearance_ft) lines.push(describeDistance(h.clearance_ft, h.clearance_to, h.confidence, h.method));
  if (h.distance_ft) lines.push(describeDistance(h.distance_ft, "wall", h.confidence, h.method));
  if (h.height_in) lines.push(`About ${formatRange(h.height_in, "in")} tall · ${confidenceWords(h.confidence)}, ${methodWords(h.method)}`);
  return lines;
}

export function statusWords(s: RuleStatus): string {
  return s === "fail" ? "Fails" : s === "needs-review" ? "Needs review" : "Passes";
}

export function rulePackStatusWords(s: RulePackStatus): string {
  return s === "adopted" ? "In force" : s === "proposed" ? "Proposed" : "Guidance";
}

export function zoneWords(zone: string | null | undefined): string {
  switch (zone) {
    case "Z0":
      return "Zone 0 · 0–5 ft";
    case "Z1":
      return "Zone 1 · up to 30 ft";
    case "Z2":
      return "Zone 2 · 30–100 ft";
    case "Z12":
      return "Zones 1 and 2";
    case "ALL":
      return "Whole property";
    default:
      return "Zone unknown";
  }
}

export function sideWords(side: Side | string): string {
  switch (side) {
    case "N":
      return "North side";
    case "E":
      return "East side";
    case "S":
      return "South side";
    case "W":
      return "West side";
    case "roof":
      return "Roof";
    default:
      return "Side not known";
  }
}

export function effortWords(e: Fix["effort"]): string {
  return e === "S" ? "Quick job" : e === "M" ? "Half day" : "Project";
}

export function costWords(c: Fix["cost_band"]): string {
  switch (c) {
    case "free":
      return "Free";
    case "$":
      return "Under $100";
    case "$$":
      return "$100–$1,000";
    default:
      return "Over $1,000";
  }
}

/** Who's-responsible wording for a community type. Stored values stay HOA / Owner / Unclear. */
export function respWords(type?: string | null) {
  if (type === "Commercial")
    return { HOA: "Property manager", Owner: "Tenant", Unclear: "Unclear", owners: "Tenants", tasks: "Site tasks" };
  if (type === "Home") return { HOA: "HOA", Owner: "Homeowner", Unclear: "Unclear", owners: "Homeowner", tasks: "Tasks" };
  return { HOA: "HOA", Owner: "Homeowner", Unclear: "Unclear", owners: "Homeowners", tasks: "HOA tasks" };
}

export function ownerWords(o: Fix["owner"], type?: string | null): string {
  const w = respWords(type);
  return o === "Unclear" ? "Unclear who" : w[o];
}

/** 13320 -> "0:13". */
export function formatTimestamp(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function framesTracked(frames: readonly number[], samFps?: number): string {
  const n = frames.length;
  const base = `tracked in ${n} frame${n === 1 ? "" : "s"}`;
  if (!samFps || n < 2) return base;
  const seconds = (Math.max(...frames) - Math.min(...frames) + 1) / samFps;
  return `${base} (about ${Math.max(1, Math.round(seconds))} s of video)`;
}

export function formatDate(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
}
