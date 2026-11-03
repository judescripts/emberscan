# ADR 0005: Agent design (Muse Spark)

**Status:** Accepted (2026-10-26). Built; see "As built" below.

## Context
Judging rewards going beyond one API call (Meta AI tooling, 25%) and offers a Best Agentic Use-Case prize. The agent must add real value without making the product unverifiable. Facts (model notes, Oct 26): Muse Spark has 1M context, JSON-schema structured output enforced during decoding, tool calling on the Responses API with `tool_choice: "auto"` only (no forcing a specific tool).

## Decision
**The agent plans and explains; deterministic tools measure and judge.**

**Tools** (all return structured, ID'd results):
| Tool | Returns |
|---|---|
| `list_hazards(scan_id, zone?, class?)` | Tracked hazards with ids, classes, frame refs |
| `measure(hazard_id)` | Distance range, confidence, method |
| `check_rules(scan_id)` | Rule results with citations (the engine, ADR 0004) |
| `get_narration(t_start, t_end)` | Transcript turns near a moment in the video |
| `estimate_cost(fix_type, quantity)` | Cost band from a small cost table |
| `request_recheck(hazard_id, reason)` | Flags a hazard for user confirmation (low confidence) |

**Loop:** plan → call tools → draft fix plan → **verify** → output.
- **Plan:** the agent writes what it will check (zones, uncertain hazards, narration).
- **Verify:** every claim in the draft must cite tool results (hazard id, rule id, measurement). A checker (code, not the model) drops or rejects any claim whose ids don't exist or don't match; a claim that contradicts a rule result is discarded and logged.
- **Output** (JSON schema): ordered fixes with `rule_ids`, `hazard_ids`, plain-language why, effort, cost band, owner vs HOA, plus a short summary.
- Because `tool_choice` can't force a tool, the system prompt lists required checks and the verifier rejects a plan that skipped them (e.g. never called `check_rules`), triggering one retry.

**Trace for the demo:** the plan, each tool call and result, and the verifier's decisions are stored per scan and shown in the report ("How EmberScan got here"). This is what makes it visibly an agent, not an image description.

**Budget:** step and token limits per run; usage logged.

## Consequences
- The agent can be wrong about wording, never about pass/fail or distances.
- A cheaper Spark version is used in development; the open-weight path (ADR 0006) runs at least one agent step.

## As built (Nov 2)
- Tools: `get_rule_results`, `list_hazards`, `get_narration`, `estimate_cost`, `submit_plan`. Measurements come with the hazards; `measure` and `request_recheck` were folded in (hazards that can't be measured are marked by the pipeline).
- The plan runs on **Muse Spark Open** (ADR 0006) with hosted Muse Spark as the fallback, then a deterministic plan if both fail.
- Loop guards: a repeated tool call is answered "already answered, call submit_plan now", and with two turns left the agent is told to submit.
- A second agent researches each building's address (`lookup_address`, `fire_hazard_zone`, `recent_fires`, `law_that_applies`, `submit_note`); code drops any fact citing a source it never looked up.
- The report's trace shows the privacy guard, the plan, every tool call, the verifier's decisions and the Muse Image previews.
