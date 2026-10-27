"""Fix-plan agent: verifier and tool loop, with a scripted fake Responses API (no network)."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from emberscan_workers.contracts import Report
from emberscan_workers.meta import MetaClient
from emberscan_workers.meta.agent import ScanTools, run_agent, verify_plan
from emberscan_workers.meta.openweight import OpenWeightClient
from emberscan_workers.meta.voice import Transcript, Turn
from emberscan_workers.spend import SpendLedger

SAMPLE = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "report.sample.json"


@pytest.fixture
def tools() -> ScanTools:
    rep = Report.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    t = Transcript([Turn(36_000, 40_000, "This woodpile belongs to unit 6.")], "", 72_000)
    return ScanTools(rep.hazards, rep.results, t, sam_fps=3)


def fix(**kw) -> dict:
    base = {
        "title": "Move firewood",
        "why": "Too close.",
        "rule_ids": ["Z1-04"],
        "hazard_ids": ["h-woodpile-0"],
        "effort": "S",
        "cost_band": "free",
        "owner": "Owner",
    }
    return {**base, **kw}


def test_verifier_accepts_grounded_fix_and_sets_required(tools: ScanTools) -> None:
    fixes, dropped, blocking = verify_plan({"fixes": [fix()]}, tools)
    assert [f.title for f in fixes] == ["Move firewood"]
    assert fixes[0].required and fixes[0].priority == 1
    assert not dropped and not blocking


def test_verifier_drops_invented_ids(tools: ScanTools) -> None:
    plan = {
        "fixes": [
            fix(),
            fix(title="Ghost", rule_ids=["Z9-99"]),
            fix(title="Wrong hazard", hazard_ids=["h-shrub-0"]),
        ]
    }
    fixes, dropped, _ = verify_plan(plan, tools)
    assert [f.title for f in fixes] == ["Move firewood"]
    assert len(dropped) == 2


def test_verifier_blocks_uncovered_failed_rule(tools: ScanTools) -> None:
    plan = {"fixes": [fix(title="Mulch", rule_ids=["Z0-01"], hazard_ids=["h-wood_mulch-0"])]}
    fixes, _, blocking = verify_plan(plan, tools)
    assert fixes and not fixes[0].required  # proposed rule: recommended, not required
    assert blocking == ["No fix covers failed rule Z1-04"]


def test_verifier_cannot_mark_pass_rule(tools: ScanTools) -> None:
    fixes, dropped, _ = verify_plan({"fixes": [fix(rule_ids=["ALL-02"], hazard_ids=[])]}, tools)
    assert not fixes and dropped


def test_tools(tools: ScanTools) -> None:
    assert {r["rule_id"] for r in tools.get_rule_results("fail")} == {"Z1-04"}
    assert all(h["zone"] == "Z0" for h in tools.list_hazards(zone="Z0"))
    assert tools.get_narration(30, 45)[0]["text"].startswith("This woodpile")
    assert tools.estimate_cost("move_firewood")["cost_band"] == "free"


def _scripted(responses: list[dict]):
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=responses[len(calls) - 1])

    return handler, calls


def _fc(name: str, args: dict, call_id: str) -> dict:
    return {
        "type": "function_call",
        "name": name,
        "arguments": json.dumps(args),
        "call_id": call_id,
    }


def _resp(i: int, *outputs: dict) -> dict:
    return {
        "id": f"resp_{i}",
        "output": list(outputs),
        "usage": {"input_tokens": 1000, "output_tokens": 200},
    }


def test_agent_loop_with_retry_on_blocking(tools: ScanTools) -> None:
    handler, calls = _scripted(
        [
            _resp(1, _fc("get_rule_results", {"status": "any"}, "c1")),
            _resp(
                2,
                _fc(
                    "submit_plan",
                    {
                        "fixes": [
                            fix(title="Mulch", rule_ids=["Z0-01"], hazard_ids=["h-wood_mulch-0"])
                        ],
                        "summary": "s",
                    },
                    "c2",
                ),
            ),
            _resp(3, _fc("submit_plan", {"fixes": [fix()], "summary": "Move the firewood."}, "c3")),
        ]
    )
    ledger = SpendLedger(run_id="t", limit_usd=1.0)

    async def run():
        async with MetaClient(api_key="k", transport=httpx.MockTransport(handler)) as c:
            return await run_agent(c, ledger, tools, model="muse-spark-1.3-contributor")

    res = asyncio.run(run())
    assert [f.title for f in res.fixes] == ["Move firewood"]
    assert res.summary == "Move the firewood."
    # Turn 2 was rejected with the problem fed back; turn 3 carries previous_response_id.
    fed_back = json.loads(calls[2]["input"][0]["output"])
    assert fed_back["accepted"] is False and "Z1-04" in fed_back["problems"][0]
    assert calls[2]["previous_response_id"] == "resp_2"
    assert any(s.kind == "verify" for s in res.trace)
    assert ledger.summary()["calls"] == 3


def test_agent_falls_back_when_model_never_submits(tools: ScanTools) -> None:
    text_only = {"id": "r", "output": [{"type": "message", "content": []}], "usage": {}}
    handler, _ = _scripted([text_only, text_only])
    ledger = SpendLedger(run_id="t", limit_usd=1.0)

    async def run():
        async with MetaClient(api_key="k", transport=httpx.MockTransport(handler)) as c:
            return await run_agent(c, ledger, tools, model="muse-spark-1.3-contributor")

    res = asyncio.run(run())
    assert {r for f in res.fixes for r in f.rule_ids} >= {"Z1-04"}
    assert res.trace[-1].kind == "note"


def _chat(*calls: tuple[str, dict, str]) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": "thinking...",
                    "tool_calls": [
                        {
                            "id": cid,
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(args)},
                        }
                        for name, args, cid in calls
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 900, "completion_tokens": 300},
    }


def test_open_weight_plans_with_same_tools_and_verifier(tools: ScanTools) -> None:
    handler, calls = _scripted(
        [
            _chat(("get_rule_results", {"status": "fail"}, "a1")),
            _chat(("submit_plan", {"fixes": [fix()], "summary": "Move the firewood."}, "a2")),
        ]
    )
    ledger = SpendLedger(run_id="t", limit_usd=1.0)

    async def run():
        async with OpenWeightClient(api_key="k", transport=httpx.MockTransport(handler)) as o:
            return await run_agent(None, ledger, tools, open_client=o)

    res = asyncio.run(run())
    assert [f.title for f in res.fixes] == ["Move firewood"]
    assert res.model and res.model["provider"] == "baseten"
    assert calls[0]["model"] == "meta-models/muse-spark-open-1026"
    assert calls[0]["tools"][0]["function"]["name"] == "get_rule_results"
    # Turn 2 replays the conversation: the tool result answers call a1; reasoning is not resent.
    tool_msg = calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "a1"
    assert all("reasoning_content" not in m for m in calls[1]["messages"])
    assert ledger.records[0].model == "meta-models/muse-spark-open-1026"


def test_repeated_tool_calls_are_cut_short_and_the_plan_is_asked_for(tools: ScanTools) -> None:
    loop = [_chat(("estimate_cost", {"fix_type": "other"}, f"e{i}")) for i in range(6)]
    submit = _chat(("submit_plan", {"fixes": [fix()], "summary": "s"}, "s1"))
    handler, calls = _scripted([*loop, submit])

    async def run():
        async with OpenWeightClient(api_key="k", transport=httpx.MockTransport(handler)) as o:
            return await run_agent(None, SpendLedger("t", 1.0), tools, open_client=o)

    res = asyncio.run(run())
    assert res.model and res.model["provider"] == "baseten" and res.fixes
    repeat = json.loads(calls[2]["messages"][-1]["content"])
    assert "Already answered" in repeat["note"]  # the repeat isn't run again
    assert sum(1 for s in res.trace if s.kind == "tool_call" and "estimate_cost" in s.summary) == 1
    last = calls[-1]["messages"][-1]
    assert last["role"] == "user" and "out of turns" in last["content"]


def test_open_weight_failure_falls_back_to_hosted(tools: ScanTools) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "overloaded"})

    handler, _ = _scripted([_resp(1, _fc("submit_plan", {"fixes": [fix()], "summary": "s"}, "c1"))])
    ledger = SpendLedger(run_id="t", limit_usd=1.0)

    async def run():
        async with (
            OpenWeightClient(api_key="k", transport=httpx.MockTransport(down)) as o,
            MetaClient(api_key="k", transport=httpx.MockTransport(handler)) as c,
        ):
            return await run_agent(c, ledger, tools, open_client=o)

    res = asyncio.run(run())
    assert res.model and res.model["provider"] == "meta"
    assert "Muse Spark Open" in res.trace[0].summary and res.trace[0].kind == "note"


def test_open_weight_over_run_limit_uses_hosted(tools: ScanTools) -> None:
    def never(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Spark Open must not be called over the limit")

    handler, _ = _scripted([_resp(1, _fc("submit_plan", {"fixes": [fix()], "summary": "s"}, "c1"))])
    ledger = SpendLedger(run_id="t", limit_usd=1.0, partner_limit_usd=0.01)  # < one Spark Open turn

    async def run():
        async with (
            OpenWeightClient(api_key="k", transport=httpx.MockTransport(never)) as o,
            MetaClient(api_key="k", transport=httpx.MockTransport(handler)) as c,
        ):
            return await run_agent(c, ledger, tools, open_client=o)

    res = asyncio.run(run())
    assert res.model and res.model["provider"] == "meta" and res.fixes


def test_api_failure_retries_then_falls_back(monkeypatch, tools: ScanTools) -> None:
    import asyncio

    from emberscan_workers.meta import agent as A

    calls = {"n": 0}

    async def boom(*args, **kwargs):
        calls["n"] += 1
        raise RuntimeError("referenced response not found or expired")

    monkeypatch.setattr(A, "_run_agent_once", boom)
    res = asyncio.run(A.run_agent(None, SpendLedger("t", 1.0), tools, site_type="Commercial"))
    assert calls["n"] == 2
    assert res.fixes and all(f.rule_ids for f in res.fixes)  # rule-based plan
    assert [s.kind for s in res.trace][-1] == "note"
