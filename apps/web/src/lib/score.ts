import type { Fix, Report, RuleResult, RuleStatus } from "./report-types";

// ADR 0007: ≥90 "In good shape", 75–89 "A few fixes needed", <75 "Needs work".
export type ScoreTone = "pass" | "review" | "fail";

export function scoreLabel(score: number): string {
  if (score >= 90) return "In good shape";
  if (score >= 75) return "A few fixes needed";
  return "Needs work";
}

export function scoreTone(score: number): ScoreTone {
  if (score >= 90) return "pass";
  if (score >= 75) return "review";
  return "fail";
}

/** Points a single result takes off the score. Only adopted rules count (ADR 0004). */
export function rulePenalty(result: Pick<RuleResult, "zone" | "status" | "rule_status">): number {
  if (result.rule_status !== "adopted") return 0;
  const full = result.zone === "Z2" ? 4 : result.zone === "Z1" || result.zone === "Z12" ? 8 : 10;
  if (result.status === "fail") return full;
  if (result.status === "needs-review") return full / 2;
  return 0;
}

export function scoreCap(unfilmedSides: readonly string[]): number {
  return unfilmedSides.length > 0 ? 80 : 100;
}

export function computeScore(results: readonly RuleResult[], unfilmedSides: readonly string[] = []): number {
  const penalty = results.reduce((sum, r) => sum + rulePenalty(r), 0);
  return Math.max(0, Math.min(scoreCap(unfilmedSides), Math.round(100 - penalty)));
}

/** The fixes to start with: required ones first, then by the agent's priority. */
export function topFixes(fixes: readonly Fix[], n = 3): Fix[] {
  return [...fixes]
    .sort((a, b) => Number(b.required) - Number(a.required) || a.priority - b.priority)
    .slice(0, n);
}

/** Score after the given fixes are done (and confirmed by a rescan). */
export function projectedScore(report: Pick<Report, "score" | "results">, fixes: readonly Fix[]): number {
  const ruleIds = new Set(fixes.flatMap((f) => f.rule_ids));
  const regained = report.results
    .filter((r) => ruleIds.has(r.rule_id))
    .reduce((sum, r) => sum + rulePenalty(r), 0);
  const cap = scoreCap(report.score.unfilmed_sides ?? []);
  return Math.max(0, Math.min(cap, Math.round(report.score.score + regained)));
}

const STATUS_RANK: Record<RuleStatus, number> = { fail: 0, "needs-review": 1, pass: 2 };

/** Worst status among the results that reference a hazard, or null if none do. */
export function hazardStatus(hazardId: string, results: readonly RuleResult[]): RuleStatus | null {
  let worst: RuleStatus | null = null;
  for (const r of results) {
    if (!r.hazard_ids.includes(hazardId)) continue;
    if (worst === null || STATUS_RANK[r.status] < STATUS_RANK[worst]) worst = r.status;
  }
  return worst;
}

export function compareStatus(a: RuleStatus, b: RuleStatus): number {
  return STATUS_RANK[a] - STATUS_RANK[b];
}
