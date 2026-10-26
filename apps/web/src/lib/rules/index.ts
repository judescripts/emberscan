import usCa from "./us-ca.json";
import type { RulePackStatus } from "../report-types";

// Rule packs are data (ADR 0004). The web app reads them for the Rules screen and labels;
// the worker's deterministic engine is what evaluates them.

export interface PackRule {
  id: string;
  zone: string;
  title: string;
  hazard_classes: string[];
  check: { type: string; [key: string]: unknown };
  plain_language: string;
  status: RulePackStatus;
  effective_date: string | null;
  applies_to: string;
  existing_phase_in?: string;
  citation_url: string;
  citation_label: string;
}

export interface PackZone {
  id: string;
  name: string;
  min_ft: number;
  max_ft: number;
  status: string;
  note: string;
}

export interface RulePack {
  pack_id: string;
  jurisdiction: { country: string; state?: string };
  version: string;
  checked_on: string;
  applies_where: string;
  disclaimer: string;
  status_notes: Record<string, unknown>;
  zones: PackZone[];
  rules: PackRule[];
  sources: { label: string; url: string }[];
}

export const PACKS: Record<string, RulePack> = {
  "us-ca": usCa as unknown as RulePack,
};

/** Packs shown in the community form. Only California is live for the hackathon. */
export const PACK_OPTIONS = [
  { id: "us-ca", label: "California (CAL FIRE, PRC 4291)", available: true },
  { id: "us-or", label: "Oregon", available: false },
  { id: "us-co", label: "Colorado", available: false },
  { id: "us-baseline", label: "US best practice (guidance only)", available: false },
] as const;

export function getPack(id: string): RulePack {
  return PACKS[id] ?? PACKS["us-ca"];
}

export function packLabel(id: string): string {
  return PACK_OPTIONS.find((p) => p.id === id)?.label ?? id;
}

export function findRule(packId: string, ruleId: string): PackRule | undefined {
  return getPack(packId).rules.find((r) => r.id === ruleId);
}

/** Plain-language threshold for a rule's typed check. */
export function thresholdWords(rule: PackRule): string {
  const c = rule.check;
  const ft = c.ft;
  switch (c.type) {
    case "absent_within": {
      const reach =
        ft === "eave"
          ? `under the eaves (the overhang's width, ${c.min_ft ?? 0}–${c.max_ft ?? 5} ft)`
          : `within ${typeof c.min_ft === "number" ? `${c.min_ft}–` : ""}${ft} ft of the building`;
      return `None ${reach}`;
    }
    case "min_clearance":
      return `At least ${ft} ft from the ${String(c.reference ?? "building").replace(/_/g, " ")}`;
    case "max_height":
      return `No taller than ${c.inches} in`;
    case "present": {
      const where: Record<string, string> = {
        roof: "on the roof",
        gutter: "in the gutters",
        under_or_adjacent_deck_balcony_stairs: "under or next to decks, balconies or stairs",
        under_deck_balcony_pergola_stairs: "under decks, balconies, pergolas or stairs",
      };
      const loc = String(c.location ?? "");
      return `None ${where[loc] ?? loc.replace(/_/g, " ")}`;
    }
    case "manual_review":
      return "Check on site: video can't settle this one";
    default:
      return c.type;
  }
}

export const ZONE_ORDER = ["Z0", "Z1", "Z12", "Z2", "ALL"];
