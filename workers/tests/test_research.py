"""Address research: law mapping, fact verification and the scripted agent loop (no network)."""

import asyncio
import json
from typing import Any

import httpx

from emberscan_workers.research import (
    ResearchTools,
    _place_name,
    law_that_applies,
    research_address,
    verify_note,
)
from emberscan_workers.spend import SpendLedger

CENSUS = {
    "result": {
        "addressMatches": [
            {
                "matchedAddress": "1 TEST RD, VALENCIA, CA, 91355",
                "coordinates": {"x": -118.5, "y": 34.4},
                "geographies": {
                    "Counties": [{"NAME": "Los Angeles County"}],
                    "Incorporated Places": [{"NAME": "Santa Clarita city"}],
                },
            }
        ]
    }
}
ZONE = {"features": [{"attributes": {"HAZ_CLASS": "Very High", "SRA": "LRA", "Revised": 0}}]}
FIRES = {"features": [{"attributes": {"FIRE_NAME": "HUGHES", "YEAR_": 2025, "GIS_ACRES": 10397}}]}


def _http() -> httpx.AsyncClient:
    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if "geocoding" in url:
            return httpx.Response(200, json=CENSUS)
        if "Perimeters" in url:
            return httpx.Response(200, json=FIRES)
        return httpx.Response(200, json=ZONE)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class ScriptedClient:
    """Plays back Responses API turns: tool calls, then submit_note."""

    def __init__(self, turns: list[list[tuple[str, dict]]]) -> None:
        self.turns = turns
        self.seen: list[dict] = []

    async def create_response(self, body: dict[str, Any]) -> dict[str, Any]:
        self.seen.append(body)
        calls = self.turns.pop(0) if self.turns else []
        return {
            "id": f"r{len(self.seen)}",
            "usage": {"input_tokens": 1000, "output_tokens": 200},
            "output": [
                {"type": "function_call", "name": n, "arguments": json.dumps(a), "call_id": f"c{i}"}
                for i, (n, a) in enumerate(calls)
            ],
        }


def test_law_mapping() -> None:
    assert law_that_applies("SRA", "Moderate")["law"] == "PRC 4291"
    assert law_that_applies("LRA", "Very High")["law"] == "Gov. Code 51182"
    assert law_that_applies("LRA", "High")["applies"] is False
    assert law_that_applies(None, None)["applies"] is None


def test_place_name() -> None:
    assert _place_name("Santa Clarita city") == "Santa Clarita"
    assert _place_name("Altadena") == "Altadena"
    assert _place_name(None) is None


def test_verify_drops_facts_citing_unseen_sources() -> None:
    tools = ResearchTools(address="x", http=_http())
    tools.seen_sources = {"census"}
    facts, dropped = verify_note(
        {
            "facts": [
                {"label": "City", "value": "Santa Clarita", "source_id": "census"},
                {"label": "Zone", "value": "Very High", "source_id": "la-fhsz"},
            ]
        },
        tools,
    )
    assert [f.label for f in facts] == ["City"] and len(dropped) == 1


def test_agent_loop_builds_cited_note() -> None:
    client = ScriptedClient(
        [
            [("lookup_address", {})],
            [("fire_hazard_zone", {"lat": 34.4, "lon": -118.5})],
            [("recent_fires", {"lat": 34.4, "lon": -118.5, "miles": 5})],
            [
                (
                    "submit_note",
                    {
                        "summary": "Very High zone.",
                        "facts": [
                            {"label": "Zone", "value": "Very High (LRA)", "source_id": "la-fhsz"},
                            {"label": "Invented", "value": "x", "source_id": "made-up"},
                        ],
                        "to_check": ["Confirm the fire agency."],
                    },
                )
            ],
        ]
    )

    async def go():
        async with _http() as http:
            return await research_address("1 Test Rd", client, SpendLedger("t", 0.05), http=http)

    note = asyncio.run(go())
    assert note.city == "Santa Clarita" and note.hazard_class == "Very High"
    assert [f.label for f in note.facts] == ["Zone"]
    assert {s.id for s in note.sources} == {"census", "la-fhsz", "calfire-fires"}
    assert note.model and note.cost_usd > 0


def test_falls_back_to_lookups_when_model_never_submits() -> None:
    client = ScriptedClient([])  # model answers in text every turn

    async def go():
        async with _http() as http:
            return await research_address("1 Test Rd", client, SpendLedger("t", 0.05), http=http)

    note = asyncio.run(go())
    assert note.model is None
    labels = [f.label for f in note.facts]
    assert "Fire hazard zone" in labels and "Recent fires nearby" in labels
    assert "State law" in labels


def test_safe_entry_retries_once_when_the_agent_stops(monkeypatch) -> None:
    from emberscan_workers import research as R
    from emberscan_workers.contracts import AgentStep

    def note(model: str | None, step: str) -> R.BuildingNote:
        n = R.BuildingNote(address="1 Test Rd", summary=step)
        n.model, n.trace = model, [AgentStep(kind="note", summary=step)]
        return n

    tries = iter([note(None, "Agent stopped (ReadTimeout)."), note("m", "ok")])

    async def fake(*args, **kwargs):
        return next(tries)

    monkeypatch.setattr(R, "research_address", fake)
    monkeypatch.setenv("META_API_KEY", "test")
    out = asyncio.run(R.research_address_safe("1 Test Rd", SpendLedger("t", 0.05)))
    assert out.model == "m"
