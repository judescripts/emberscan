import type { FixStatus, Responsibility } from "./db/schema";
import type { Fix, Report, RuleStatus } from "./report-types";

// Fix tracking rules (ADR 0007): Open, In progress, Fixed – needs rescan, Verified by rescan,
// Won't fix (needs a reason). Only a rescan sets Verified.

export const STATUS_LABEL: Record<FixStatus, string> = {
  open: "Open",
  progress: "In progress",
  fixed: "Fixed – needs rescan",
  verified: "Verified by rescan",
  wontfix: "Won't fix",
};

/** Statuses a person can pick. "verified" is deliberately missing: only a rescan sets it. */
export const USER_STATUSES: FixStatus[] = ["open", "progress", "fixed", "wontfix"];

export function isUserSettable(s: string): s is FixStatus {
  return (USER_STATUSES as string[]).includes(s);
}

/** The rule a fix is tracked under (one task per building and rule). */
export function taskRuleId(fix: Fix): string {
  return fix.rule_ids[0] ?? fix.id;
}

export function defaultOwner(r: Responsibility): string {
  return r === "HOA" ? "HOA board" : r === "Owner" ? "Homeowner" : "";
}

export interface RescanOutcome {
  status: FixStatus;
  note?: string;
}

/**
 * What a new scan does to an existing task. `ruleStatus` is the rule's result in the new scan
 * (undefined when the new report doesn't mention the rule).
 */
export function rescanTransition(prev: FixStatus, ruleStatus: RuleStatus | undefined, stillHasFix: boolean): RescanOutcome {
  const cleared = ruleStatus === "pass" || (ruleStatus === undefined && !stillHasFix);
  if (prev === "wontfix") return { status: prev };
  if (cleared) {
    if (prev === "verified") return { status: prev };
    return { status: "verified", note: "Verified by rescan: the rule no longer flags this." };
  }
  if (prev === "verified" || prev === "fixed") {
    return { status: "open", note: "Rescan still finds this. Reopened." };
  }
  return { status: prev };
}

export function ruleStatusMap(report: Report): Map<string, RuleStatus> {
  return new Map(report.results.map((r) => [r.rule_id, r.status]));
}
