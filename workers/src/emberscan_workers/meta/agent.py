"""Fix-plan agent on Muse Spark Open or hosted Muse Spark (stories D2, D3, D4; ADRs 0005, 0006).

Muse Spark Open (open weights, on Baseten) plans first when BASETEN_API_KEY is set; hosted
Muse Spark is the backup. Both run the same tools, verifier and trace.

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
from ..spend import SpendLedger, SpendLimitExceeded, token_cost
from .client import MetaClient
from .openweight import LABEL as OPEN_LABEL
from .openweight import PRICE_KEY as OPEN_PRICE_KEY
from .openweight import OpenWeightClient
from .voice import Transcript

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "muse-spark-1.3-contributor")
MAX_TURNS = 8
MAX_OUTPUT_TOKENS = 4000  # includes reasoning tokens
OPEN_MAX_TOKENS = 8000  # Muse Spark Open always reasons before answering
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
    model: dict | None = None  # {model, provider, label, seconds} of the model that planned
    fell_back: bool = False  # the model gave no valid plan; fixes are rule-based


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


AUDIENCE = {
    "Commercial": (
        "This is a COMMERCIAL property. Write for a property manager. In the owner field, "
        '"HOA" means the property manager (shared landscaping, the building exterior) and '
        '"Owner" means a tenant (items at a tenant\'s own entrance, patio or storage). In the '
        'text say "property manager" or "tenant"; never say homeowner, HOA or HOA board.'
    ),
    "Home": (
        'This is a single home. Write for the homeowner; use "Owner" for nearly everything and '
        "never mention an HOA."
    ),
}


@dataclass
class _Reply:
    calls: list[dict[str, str]]  # {"call_id", "name", "arguments"}
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0


class _HostedChat:
    """Hosted Muse Spark on the Responses API; the server keeps the conversation."""

    provider = "meta"
    label = "Muse Spark (Meta Model API)"
    est_tokens = EST_COST_PER_TURN_TOKENS

    def __init__(self, client: MetaClient, model: str, instructions: str) -> None:
        self.client, self.model, self.price_model = client, model, model
        self.base: dict[str, Any] = {
            "model": model,
            "instructions": instructions,
            "tools": TOOLS,
            "tool_choice": "auto",
            "reasoning": {"effort": "low"},
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        }
        self.previous_id: str | None = None

    async def send(self, items: list[dict[str, str]]) -> _Reply:
        inputs = [
            {"role": "user", "content": i["text"]}
            if i["type"] == "user"
            else {"type": "function_call_output", "call_id": i["call_id"], "output": i["output"]}
            for i in items
        ]
        body = {**self.base, "input": inputs}
        if self.previous_id is not None:
            body["previous_response_id"] = self.previous_id
        resp = await self.client.create_response(body)
        self.previous_id = resp.get("id")
        usage = resp.get("usage") or {}
        return _Reply(
            [
                {
                    "call_id": o.get("call_id", ""),
                    "name": o.get("name", ""),
                    "arguments": o.get("arguments") or "{}",
                }
                for o in resp.get("output", [])
                if o.get("type") == "function_call"
            ],
            int(usage.get("input_tokens", 0)),
            int(usage.get("output_tokens", 0)),
            int((usage.get("input_tokens_details") or {}).get("cached_tokens", 0)),
        )


class _OpenChat:
    """Muse Spark Open on Baseten (Chat Completions); we keep the conversation. Same tools,
    same verifier: Baseten doesn't enforce JSON schemas, so verify_plan is the only judge."""

    provider = "baseten"
    label = OPEN_LABEL
    est_tokens = (12_000, OPEN_MAX_TOKENS)

    def __init__(self, client: OpenWeightClient, instructions: str) -> None:
        self.client, self.model, self.price_model = client, client.model, OPEN_PRICE_KEY
        self.tools = [
            {
                "type": "function",
                "function": {k: t[k] for k in ("name", "description", "parameters")},
            }
            for t in TOOLS
        ]
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": instructions}]

    async def send(self, items: list[dict[str, str]]) -> _Reply:
        for i in items:
            self.messages.append(
                {"role": "user", "content": i["text"]}
                if i["type"] == "user"
                else {"role": "tool", "tool_call_id": i["call_id"], "content": i["output"]}
            )
        resp = await self.client.chat(
            {
                "messages": self.messages,
                "tools": self.tools,
                "tool_choice": "auto",
                "max_tokens": OPEN_MAX_TOKENS,  # it always reasons first; leave it room
            }
        )
        msg = (resp.get("choices") or [{}])[0].get("message") or {}
        tool_calls = msg.get("tool_calls") or []
        # Keep the assistant turn (minus its reasoning) so tool results line up with call ids.
        self.messages.append(
            {"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls}
            if tool_calls
            else {"role": "assistant", "content": msg.get("content") or ""}
        )
        usage = resp.get("usage") or {}
        return _Reply(
            [
                {
                    "call_id": c.get("id", ""),
                    "name": (c.get("function") or {}).get("name", ""),
                    "arguments": (c.get("function") or {}).get("arguments") or "{}",
                }
                for c in tool_calls
            ],
            int(usage.get("prompt_tokens", 0)),
            int(usage.get("completion_tokens", 0)),
            int((usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0),
        )


async def run_agent(
    client: MetaClient,
    ledger: SpendLedger,
    tools: ScanTools,
    model: str = DEFAULT_MODEL,
    site_type: str = "HOA",
    open_client: OpenWeightClient | None = None,
) -> AgentResult:
    """Plan fixes. With `open_client`, Muse Spark Open plans first and hosted Muse Spark is the
    backup; hosted gets one fresh retry if the API drops the conversation; the last resort is
    the rule-based plan. A flaky model call never fails the scan."""
    instructions = SYSTEM + ("\n" + AUDIENCE[site_type] if site_type in AUDIENCE else "")
    chats: list[Any] = [_HostedChat(client, model, instructions) for _ in (1, 2)]
    if open_client is not None:
        chats.insert(0, _OpenChat(open_client, instructions))
    notes: list[AgentStep] = []
    for n, chat in enumerate(chats):
        last = n == len(chats) - 1
        try:
            result = await _run_agent_once(chat, ledger, tools)
        except SpendLimitExceeded:
            if chat.provider != "baseten" or last:
                raise
            # Spark Open bills Baseten credits at list price, under its own per-run limit.
            notes.append(
                AgentStep(
                    kind="note",
                    summary=f"{chat.label} would pass the scan's partner spend limit; "
                    f"trying {chats[n + 1].label}.",
                )
            )
            continue
        except Exception as e:  # e.g. "referenced response not found or expired"
            notes.append(
                AgentStep(
                    kind="note",
                    summary=f"{chat.label} call failed ({type(e).__name__}); "
                    + ("giving up." if last else f"trying {chats[n + 1].label}."),
                    detail={"error": str(e)[:300]},
                )
            )
            continue
        if result.fell_back and chat.provider == "baseten" and not last:
            notes += result.trace[:-1]
            notes.append(
                AgentStep(
                    kind="note",
                    summary=f"{chat.label} gave no valid plan; trying {chats[n + 1].label}.",
                )
            )
            continue
        result.trace[:0] = notes
        return result
    notes.append(AgentStep(kind="note", summary="Using the rule-based fallback plan."))
    return AgentResult(fallback_plan(tools), "Fixes listed from the rule results.", notes)


async def _run_agent_once(chat: Any, ledger: SpendLedger, tools: ScanTools) -> AgentResult:
    trace: list[AgentStep] = [
        AgentStep(
            kind="plan",
            summary=(
                "Review rule results, inspect the measured hazards behind them, use narration for "
                "context, estimate costs, then submit a plan that cites every rule and hazard."
            ),
            detail={"model": chat.model, "provider": chat.provider, "label": chat.label},
        )
    ]
    model_info = {"model": chat.model, "provider": chat.provider, "label": chat.label}
    open_items = [r for r in tools.results.values() if r.status != "pass"]
    if not open_items:
        trace.append(AgentStep(kind="output", summary="No open items; no fixes needed."))
        return AgentResult([], "No fixes needed for the rules checked.", trace)

    items: list[dict[str, str]] = [{"type": "user", "text": "Plan the fixes for this scan."}]
    retried = False
    started = time.monotonic()
    seen: set[str] = set()  # tool calls already answered, to stop loops
    for turn in range(MAX_TURNS):
        partner = chat.provider == "baseten"  # Baseten credits, not the Meta account
        ledger.check("agent", token_cost(chat.price_model, *chat.est_tokens), partner=partner)
        t0 = time.monotonic()
        reply = await chat.send(items)
        ledger.record(
            "agent",
            chat.model,
            token_cost(
                chat.price_model, reply.input_tokens, reply.output_tokens, reply.cached_tokens
            ),
            {"input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens},
            time.monotonic() - t0,
            partner=partner,
        )
        calls = reply.calls
        if not calls:
            if retried:
                break
            retried = True
            items = [{"type": "user", "text": "Call submit_plan now with your fixes."}]
            trace.append(
                AgentStep(kind="note", summary="Model answered in text; asked it to submit_plan.")
            )
            continue

        outputs: list[dict[str, str]] = []
        for call in calls:
            name = call.get("name", "")
            try:
                args = json.loads(call.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
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
                            "type": "tool",
                            "call_id": call["call_id"],
                            "output": json.dumps(
                                {"accepted": False, "problems": blocking, "dropped": dropped}
                            ),
                        }
                    )
                    continue
                seconds = round(time.monotonic() - started, 1)
                trace.append(
                    AgentStep(
                        kind="output",
                        summary=f"{len(fixes)} fixes, {sum(f.required for f in fixes)} required "
                        f"· planned by {chat.label} in {seconds:g} s.",
                        detail={**model_info, "seconds": seconds},
                    )
                )
                return AgentResult(
                    fixes,
                    str(args.get("summary", "")).strip(),
                    trace,
                    dropped,
                    model={**model_info, "seconds": seconds},
                )
            key = f"{name}:{json.dumps(args, sort_keys=True)}"
            if key in seen:  # a loop: answer once, then push toward the plan
                outputs.append(
                    {
                        "type": "tool",
                        "call_id": call["call_id"],
                        "output": json.dumps(
                            {"note": "Already answered above. Call submit_plan now."}
                        ),
                    }
                )
                continue
            seen.add(key)
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
                {"type": "tool", "call_id": call["call_id"], "output": json.dumps(result)}
            )
        if turn >= MAX_TURNS - 3:  # two turns left: the next answer has to be the plan
            outputs.append(
                {
                    "type": "user",
                    "text": "You're out of turns. Call submit_plan now with your fixes.",
                }
            )
        items = outputs

    trace.append(
        AgentStep(
            kind="note", summary="Agent did not submit a valid plan; using rule-based fallback."
        )
    )
    return AgentResult(
        fallback_plan(tools), "Fixes listed from the rule results.", trace, fell_back=True
    )


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
