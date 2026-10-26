"""Fix-plan agent on Muse Spark (stories D2, D3; ADR 0005).

The agent plans and explains; deterministic code measures and judges. It inspects the
scan through tools, then must call `submit_plan`. A verifier written in code checks every
claim against the tool data: unknown or mismatched ids are rejected, a plan that skips a
failed rule is sent back once, and fields the model must not decide (`required`, order of
required fixes) are set by code. The whole exchange is kept as a trace for the report.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from ..contracts import AgentStep, Fix, Hazard, RuleResult
from ..spend import SpendLedger, token_cost
from .client import MetaClient
from .voice import Transcript

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "muse-spark-1.3-contributor")
MAX_TURNS = 8
MAX_OUTPUT_TOKENS = 4000  # includes reasoning tokens
EST_COST_PER_TURN_TOKENS = (12_000, 2_000)  # worst-case input/output per turn for the check

SYSTEM = """You are EmberScan's fix planner for wildfire defensible space.
Measurements and rule results come from deterministic code and are final: never change a
pass/fail/needs-review status, never invent hazards, distances or rules.
Work like this:
1. Call get_rule_results to see what failed or needs review.
2. Call list_hazards (optionally by zone) to see the measured hazards behind them.
3. Call get_narration for time ranges where the resident spoke (context such as ownership).
4. Call estimate_cost for each kind of fix you propose.
5. Call submit_plan once with your fixes.
Rules for the plan: one fix per distinct action; every fix must cite the rule_ids and hazard_ids
it resolves, taken exactly from tool results; cover EVERY rule with status "fail" AND every
"needs-review" rule that lists hazard_ids (those are recommended fixes, e.g. proposed Zone 0
rules or borderline distances: say "confirm with a tape measure" when a distance straddles a
limit); you may group rules fixed by the same action; prefer fixes closest to the house first;
use narration to decide ownership when it says who an item belongs to; write in plain,
friendly English for a homeowner or HOA board (no jargon, no legal advice, never say the
property is safe or compliant); owner is "HOA"
for shared landscaping, roofs, gutters and fences, "Owner" for items on a unit's patio or porch,
"Unclear" otherwise."""

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_rule_results",
        "description": "Rule results from the deterministic engine. Filter by status.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["fail", "needs-review", "pass", "any"]}
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_hazards",
        "description": "Measured hazards tracked across the video. Filter by zone or class.",
        "parameters": {
            "type": "object",
            "properties": {"zone": {"type": "string"}, "cls": {"type": "string"}},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_narration",
        "description": "What the resident said between two times in the video (seconds).",
        "parameters": {
            "type": "object",
            "properties": {"start_s": {"type": "number"}, "end_s": {"type": "number"}},
            "required": ["start_s", "end_s"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "estimate_cost",
        "description": "Rough effort and cost band for a kind of fix.",
        "parameters": {
            "type": "object",
            "properties": {
                "fix_type": {
                    "type": "string",
                    "enum": sorted(
                        [
                            "remove_mulch",
                            "remove_shrub",
                            "trim_tree",
                            "move_firewood",
                            "clean_gutters",
                            "clean_roof",
                            "replace_fence_section",
                            "mow_grass",
                            "move_items",
                            "screen_vents",
                            "clear_propane_area",
                            "remove_dead_plants",
                            "other",
                        ]
                    ),
                }
            },
            "required": ["fix_type"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "submit_plan",
        "description": "Submit the final fix plan. Call exactly once when done.",
        "parameters": {
            "type": "object",
            "properties": {
                "fixes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "why": {"type": "string"},
                            "rule_ids": {"type": "array", "items": {"type": "string"}},
                            "hazard_ids": {"type": "array", "items": {"type": "string"}},
                            "effort": {"type": "string", "enum": ["S", "M", "L"]},
                            "cost_band": {"type": "string", "enum": ["free", "$", "$$", "$$$"]},
                            "owner": {"type": "string", "enum": ["HOA", "Owner", "Unclear"]},
                        },
                        "required": [
                            "title",
                            "why",
                            "rule_ids",
                            "hazard_ids",
                            "effort",
                            "cost_band",
                            "owner",
                        ],
                        "additionalProperties": False,
                    },
                },
                "summary": {"type": "string"},
            },
            "required": ["fixes", "summary"],
            "additionalProperties": False,
        },
    },
]

COST_TABLE = {
    "remove_mulch": ("M", "$$"),
    "remove_shrub": ("S", "$"),
    "trim_tree": ("M", "$$"),
    "move_firewood": ("S", "free"),
    "clean_gutters": ("S", "$"),
    "clean_roof": ("S", "$"),
    "replace_fence_section": ("M", "$$"),
    "mow_grass": ("S", "$"),
    "move_items": ("S", "free"),
    "screen_vents": ("S", "$"),
    "clear_propane_area": ("S", "$"),
    "remove_dead_plants": ("S", "$"),
    "other": ("M", "$$"),
}


@dataclass
class AgentResult:
    fixes: list[Fix]
    summary: str
    trace: list[AgentStep] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)


def _range_text(r) -> str | None:
    if r is None:
        return None
    return f"{r.min:g}" if r.min == r.max else f"{r.min:g}-{r.max:g}"


class ScanTools:
    """Read-only views of one scan, used as the agent's tools."""

    def __init__(
        self,
        hazards: list[Hazard],
        results: list[RuleResult],
        transcript: Transcript | None,
        sam_fps: float,
    ) -> None:
        self.hazards = {h.id: h for h in hazards}
        self.results = {r.rule_id: r for r in results}
        self.transcript = transcript
        self.sam_fps = sam_fps

    def get_rule_results(self, status: str = "any") -> list[dict]:
        return [
            {
                "rule_id": r.rule_id,
                "title": r.title,
                "zone": r.zone,
                "status": r.status,
                "rule_status": r.rule_status,
                "reason": r.reason,
                "hazard_ids": r.hazard_ids,
            }
            for r in self.results.values()
            if status in ("any", r.status)
        ]

    def list_hazards(self, zone: str | None = None, cls: str | None = None) -> list[dict]:
        out = []
        for h in self.hazards.values():
            if (zone and h.zone != zone) or (cls and h.cls != cls):
                continue
            first, last = (min(h.frames), max(h.frames)) if h.frames else (0, 0)
            out.append(
                {
                    "hazard_id": h.id,
                    "class": h.cls,
                    "label": h.label,
                    "zone": h.zone,
                    "zone_uncertain": h.zone_uncertain,
                    "distance_ft": _range_text(h.distance_ft),
                    "clearance_ft": _range_text(h.clearance_ft),
                    "clearance_to": h.clearance_to,
                    "confidence": h.confidence,
                    "tracked_frames": len(h.frames),
                    "time_s": [round(first / self.sam_fps, 1), round(last / self.sam_fps, 1)],
                }
            )
        return out

    def get_narration(self, start_s: float, end_s: float) -> list[dict]:
        if not self.transcript:
            return []
        turns = self.transcript.near(int(start_s * 1000), int(end_s * 1000), pad_ms=0)
        return [
            {"start_s": t.start_ms / 1000, "end_s": t.end_ms / 1000, "text": t.text} for t in turns
        ]

    def estimate_cost(self, fix_type: str) -> dict:
        effort, cost = COST_TABLE.get(fix_type, COST_TABLE["other"])
        return {
            "fix_type": fix_type,
            "effort": effort,
            "cost_band": cost,
            "note": "Rough band only: $ under $100, $$ $100-1,000, $$$ over $1,000.",
        }

    def call(self, name: str, args: dict) -> Any:
        if name == "get_rule_results":
            return self.get_rule_results(args.get("status") or "any")
        if name == "list_hazards":
            return self.list_hazards(args.get("zone"), args.get("cls"))
        if name == "get_narration":
            return self.get_narration(float(args["start_s"]), float(args["end_s"]))
        if name == "estimate_cost":
            return self.estimate_cost(str(args["fix_type"]))
        raise KeyError(name)


def verify_plan(plan: dict, tools: ScanTools) -> tuple[list[Fix], list[str], list[str]]:
    """Code-level verifier. Returns (accepted fixes, dropped reasons, blocking problems).

    A fix is kept only if every rule id exists with status fail/needs-review and every hazard
    id exists and is linked to one of those rules. `required` and the order of required fixes
    are decided here, not by the model. Missing coverage of a failed rule is blocking.
    """
    fixes: list[Fix] = []
    dropped: list[str] = []
    for i, raw in enumerate(plan.get("fixes") or []):
        title = str(raw.get("title", "")).strip() or f"fix {i + 1}"
        rule_ids = [r for r in raw.get("rule_ids") or [] if isinstance(r, str)]
        hazard_ids = [h for h in raw.get("hazard_ids") or [] if isinstance(h, str)]
        bad_rules = [
            r for r in rule_ids if r not in tools.results or tools.results[r].status == "pass"
        ]
        linked = {h for r in rule_ids if r in tools.results for h in tools.results[r].hazard_ids}
        bad_hazards = [h for h in hazard_ids if h not in tools.hazards or h not in linked]
        if not rule_ids or bad_rules or bad_hazards:
            dropped.append(
                f"Dropped '{title}': unknown or unrelated ids "
                f"{bad_rules + bad_hazards or ['(no rule cited)']}"
            )
            continue
        required = any(
            tools.results[r].status == "fail" and tools.results[r].rule_status == "adopted"
            for r in rule_ids
        )
        fixes.append(
            Fix(
                id=f"f{len(fixes) + 1}",
                title=title,
                why=str(raw.get("why", "")).strip(),
                rule_ids=rule_ids,
                hazard_ids=hazard_ids,
                required=required,
                effort=raw.get("effort") if raw.get("effort") in ("S", "M", "L") else "M",
                cost_band=raw.get("cost_band")
                if raw.get("cost_band") in ("free", "$", "$$", "$$$")
                else "$$",
                owner=raw.get("owner")
                if raw.get("owner") in ("HOA", "Owner", "Unclear")
                else "Unclear",
                priority=0,
            )
        )
    covered = {r for f in fixes for r in f.rule_ids}
    failed = [r.rule_id for r in tools.results.values() if r.status == "fail"]
    blocking = [f"No fix covers failed rule {r}" for r in failed if r not in covered]
    # Required fixes first (in model order), then the rest.
    ordered = [f for f in fixes if f.required] + [f for f in fixes if not f.required]
    for n, f in enumerate(ordered, start=1):
        f.priority = n
        f.id = f"f{n}"
    return ordered, dropped, blocking


async def run_agent(
    client: MetaClient, ledger: SpendLedger, tools: ScanTools, model: str = DEFAULT_MODEL
) -> AgentResult:
    trace: list[AgentStep] = [
        AgentStep(
            kind="plan",
            summary=(
                "Review rule results, inspect the measured hazards behind them, use narration for "
                "context, estimate costs, then submit a plan that cites every rule and hazard."
            ),
        )
    ]
    open_items = [r for r in tools.results.values() if r.status != "pass"]
    if not open_items:
        trace.append(AgentStep(kind="output", summary="No open items; no fixes needed."))
        return AgentResult([], "No fixes needed for the rules checked.", trace)

    body: dict[str, Any] = {
        "model": model,
        "instructions": SYSTEM,
        "tools": TOOLS,
        "tool_choice": "auto",
        "reasoning": {"effort": "low"},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "input": [{"role": "user", "content": "Plan the fixes for this scan."}],
    }
    previous_id: str | None = None
    retried = False
    for _ in range(MAX_TURNS):
        ledger.check("agent", token_cost(model, *EST_COST_PER_TURN_TOKENS))
        t0 = time.monotonic()
        resp = await client.create_response(
            body
            if previous_id is None
            else {
                **{k: v for k, v in body.items() if k != "input"},
                "previous_response_id": previous_id,
                "input": body["input"],
            }
        )
        usage = resp.get("usage") or {}
        ledger.record(
            "agent",
            model,
            token_cost(
                model,
                int(usage.get("input_tokens", 0)),
                int(usage.get("output_tokens", 0)),
                int((usage.get("input_tokens_details") or {}).get("cached_tokens", 0)),
            ),
            {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            time.monotonic() - t0,
        )
        previous_id = resp.get("id")
        calls = [o for o in resp.get("output", []) if o.get("type") == "function_call"]
        if not calls:
            if retried:
                break
            retried = True
            body["input"] = [{"role": "user", "content": "Call submit_plan now with your fixes."}]
            trace.append(
                AgentStep(kind="note", summary="Model answered in text; asked it to submit_plan.")
            )
            continue

        outputs: list[dict[str, Any]] = []
        for call in calls:
            name = call.get("name", "")
            try:
                args = json.loads(call.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            if name == "submit_plan":
                fixes, dropped, blocking = verify_plan(args, tools)
                trace.append(
                    AgentStep(
                        kind="tool_call",
                        summary=f"submit_plan({len(args.get('fixes') or [])} fixes)",
                    )
                )
                trace.append(
                    AgentStep(
                        kind="verify",
                        summary=(
                            f"{len(fixes)} fixes accepted, {len(dropped)} dropped"
                            + (f", {len(blocking)} problems" if blocking else "")
                        ),
                        detail={"dropped": dropped, "problems": blocking},
                    )
                )
                if blocking and not retried:
                    retried = True
                    outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.get("call_id"),
                            "output": json.dumps(
                                {"accepted": False, "problems": blocking, "dropped": dropped}
                            ),
                        }
                    )
                    continue
                trace.append(
                    AgentStep(
                        kind="output",
                        summary=f"{len(fixes)} fixes, {sum(f.required for f in fixes)} required.",
                    )
                )
                return AgentResult(fixes, str(args.get("summary", "")).strip(), trace, dropped)
            try:
                result = tools.call(name, args)
            except Exception as e:  # unknown tool or bad args: tell the model, don't crash
                result = {"error": str(e)}
            n = len(result) if isinstance(result, list) else 1
            trace.append(
                AgentStep(
                    kind="tool_call",
                    summary=f"{name}({_args_text(args)}) -> {n} item(s)",
                    detail={"args": args},
                )
            )
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.get("call_id"),
                    "output": json.dumps(result),
                }
            )
        body["input"] = outputs

    trace.append(
        AgentStep(
            kind="note", summary="Agent did not submit a valid plan; using rule-based fallback."
        )
    )
    return AgentResult(fallback_plan(tools), "Fixes listed from the rule results.", trace)


def _args_text(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def fallback_plan(tools: ScanTools) -> list[Fix]:
    """Deterministic plan when the model fails: one fix per open rule."""
    fixes = []
    for r in tools.results.values():
        if r.status == "pass":
            continue
        fixes.append(
            {
                "title": f"Address: {r.title}",
                "why": r.reason,
                "rule_ids": [r.rule_id],
                "hazard_ids": r.hazard_ids,
                "effort": "M",
                "cost_band": "$$",
                "owner": "Unclear",
            }
        )
    accepted, _, _ = verify_plan({"fixes": fixes}, tools)
    return accepted
