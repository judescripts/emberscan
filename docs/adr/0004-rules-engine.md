# ADR 0004: Deterministic rules engine and rule packs

**Status:** Accepted (2026-10-26)

## Context
Judges will ask "isn't this just an image analyzer?" The answer is rule-level pass/fail with citations that is reproducible. If a model decides compliance, results vary per run and can't be audited. California's Zone 0 is still proposed (Board of Forestry votes Nov 5 to resubmit), so rules must be data, not code. Most US states have no statewide defensible-space law.

## Decision
- **Rules are data:** rule packs in `docs/rules/*.json` (first: `us-ca`). Each rule: `id`, `zone`, `hazard_classes`, typed `check` (`absent_within`, `min_clearance`, `max_height`, `present`, `manual_review`), `plain_language`, `status` (adopted / proposed / guidance), `effective_date`, `applies_to`, `citation_url`, `citation_label`.
- **Engine:** a pure function `(hazards, building, pack, settings) → results`, one result per rule: `pass` | `fail` | `needs-review`, with `hazard_ids`, the citation and a short reason. Unit tests per check type.
- **Decision logic:**
  - `fail` only for an **adopted** rule, when the hazard's **whole** distance range violates the threshold at medium or high confidence.
  - `needs-review` when the range straddles the threshold, confidence is low, the check is `manual_review`, or the rule is proposed/guidance ("would not meet the proposed rule").
  - `pass` only if the relevant area was observed and nothing matched. "Not filmed" is never a pass.
- **Score:** counts adopted rules only; proposed Zone 0 rules get a separate readiness meter.
- **Model boundary:** the agent (ADR 0005) reads results but can never change them (D3).
- **Packs for other places (roadmap H6):** state law where it exists, local overlays (stricter wins, both cited), and a national best-practice baseline that is always `guidance`, never pass/fail. Hackathon scope: `us-ca` only, a per-community "include proposed rules" setting, and a Rules screen.
- **Versioning:** each scan stores `pack_id` and `version`, so old reports stay reproducible after rule updates.

## Consequences
- Reproducible, auditable results; updating to a new regulation is a JSON change.
- Rules that video can't settle become "check on site" items instead of fake verdicts.
