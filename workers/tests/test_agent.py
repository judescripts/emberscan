"""Fix-plan agent: verifier and tool loop, with a scripted fake Responses API (no network)."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from emberscan_workers.contracts import Report
from emberscan_workers.meta import MetaClient
from emberscan_workers.meta.agent import ScanTools, run_agent, verify_plan
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
