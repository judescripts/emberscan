"""Address research: a Muse Spark agent looks up a building's address in public data and writes a
cited note (jurisdiction, fire hazard zone, which defensible-space law applies, recent fires).

The lookups are deterministic HTTP calls to public sources; the model only chooses which to
call and writes the summary. A code-side check drops any fact that cites a source the agent
never looked up, and a deterministic note is used if the model fails.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .contracts import AgentStep
from .meta import MetaClient
from .spend import SpendLedger, token_cost

MODEL = os.environ.get(
    "RESEARCH_MODEL", os.environ.get("AGENT_MODEL", "muse-spark-1.3-contributor")
)
MAX_TURNS = 6
MAX_OUTPUT_TOKENS = 3000
EST_TURN_TOKENS = (6_000, 1_500)
HTTP_TIMEOUT_S = 15.0

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
# Statewide Fire Hazard Severity Zones from CAL FIRE / the State Fire Marshal (CAL FIRE's ArcGIS).
_CALFIRE = "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services"
FHSZ_SRA_URL = f"{_CALFIRE}/FHSZSRA_23_3/FeatureServer/0"  # State Responsibility Area zones
FHSZ_LRA_URL = f"{_CALFIRE}/FHSALRA25_v1_All/FeatureServer/0"  # Local Responsibility Area, 2025
ZONE_CLASSES = ("Moderate", "High", "Very High")  # other values (e.g. "NonWildland") = no zone
FIRES_URL = (
    "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/"
    "California_Fire_Perimeters_last_5_years_View/FeatureServer/0"
)
OSFM_VIEWER = "https://osfm.fire.ca.gov/what-we-do/community-wildfire-preparedness-and-mitigation/fire-hazard-severity-zones"

SOURCES: dict[str, dict[str, str]] = {
    "census": {"name": "US Census Geocoder", "url": "https://geocoding.geo.census.gov/geocoder/"},
    "calfire-fhsz-sra": {
        "name": "CAL FIRE / State Fire Marshal: Fire Hazard Severity Zones in SRA",
        "url": FHSZ_SRA_URL,
    },
    "calfire-fhsz-lra": {
        "name": "CAL FIRE / State Fire Marshal: Fire Hazard Severity Zones in LRA (Mar 2025 map)",
        "url": FHSZ_LRA_URL,
    },
    "calfire-fires": {
        "name": "CAL FIRE fire perimeters, last 5 years",
        "url": FIRES_URL.rsplit("/FeatureServer", 1)[0],
    },
    "osfm": {"name": "CAL FIRE / OSFM Fire Hazard Severity Zones", "url": OSFM_VIEWER},
    "rules": {
        "name": "EmberScan rule reference (PRC 4291, Gov. Code 51182)",
        "url": "https://github.com/judescripts/emberscan/blob/main/docs/rules/defensible-space.md",
    },
}

DISCLAIMER = (
    "Background from public map data, not a determination. Hazard zones and enforcing agencies "
    "can change; confirm with the local fire agency."
)


class Fact(BaseModel):
    label: str
    value: str
    source_id: str


class Source(BaseModel):
    id: str
    name: str
    url: str


class BuildingNote(BaseModel):
    address: str
    matched_address: str | None = None
    lat: float | None = None
    lon: float | None = None
    state: str | None = None  # e.g. "California"; EmberScan's rules are California's only
    county: str | None = None
    city: str | None = None  # incorporated city, or None when unincorporated
    hazard_class: str | None = None  # "Very High" | "High" | "Moderate" | None (unknown)
    responsibility: str | None = None  # "SRA" | "LRA" | None
    summary: str = ""
    facts: list[Fact] = Field(default_factory=list)
    to_check: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    trace: list[AgentStep] = Field(default_factory=list)
    model: str | None = None
    cost_usd: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    disclaimer: str = DISCLAIMER


# ---------------------------------------------------------------- public-data lookups


async def geocode(http: httpx.AsyncClient, address: str) -> dict[str, Any]:
    r = await http.get(
        CENSUS_URL,
        params={
            "address": address,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "layers": "States,Counties,Incorporated Places,Census Designated Places",
            "format": "json",
        },
    )
    r.raise_for_status()
    matches = (r.json().get("result") or {}).get("addressMatches") or []
    if not matches:
        return {"found": False, "source_id": "census"}
    m = matches[0]
    geo = m.get("geographies") or {}

    def first(layer: str) -> str | None:
        items = geo.get(layer) or []
        return items[0].get("NAME") if items else None

    return {
        "found": True,
        "matched_address": m.get("matchedAddress"),
        "lat": round(float(m["coordinates"]["y"]), 6),
        "lon": round(float(m["coordinates"]["x"]), 6),
        "state": first("States"),
        "county": first("Counties"),
        "incorporated_city": _place_name(first("Incorporated Places")),
        "census_place": first("Census Designated Places"),
        "source_id": "census",
    }


def _place_name(name: str | None) -> str | None:
    """Census place names carry a type suffix: "Santa Clarita city" -> "Santa Clarita"."""
    if not name:
        return None
    for suffix in (" city", " town"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


async def _arcgis_point(
    http: httpx.AsyncClient, layer: str, lat: float, lon: float, **extra: str
) -> list[dict]:
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
        **extra,
    }
    r = await http.get(f"{layer}/query", params=params)
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(str(body["error"].get("message")))
    return [f.get("attributes", {}) for f in body.get("features", [])]


async def hazard_zone(http: httpx.AsyncClient, lat: float, lon: float) -> dict:
    """The point's zone anywhere in California: State Responsibility Area map first, then the
    2025 Local Responsibility Area map. Federal land (FRA) isn't mapped by the state."""
    for source_id, url in (("calfire-fhsz-sra", FHSZ_SRA_URL), ("calfire-fhsz-lra", FHSZ_LRA_URL)):
        feats = await _arcgis_point(http, url, lat, lon, outFields="SRA,FHSZ_Description")
        if not feats:
            continue
        cls, resp = feats[0].get("FHSZ_Description"), feats[0].get("SRA")
        if cls not in ZONE_CLASSES:
            return {
                "available": True,
                "in_zone": False,
                "hazard_class": None,
                "responsibility": resp,
                "note": f"Mapped as {cls or 'unzoned'} (not a Fire Hazard Severity Zone).",
                "source_id": source_id,
            }
        out = {
            "available": True,
            "in_zone": True,
            "hazard_class": cls,
            "responsibility": resp,
            "source_id": source_id,
        }
        if source_id == "calfire-fhsz-lra":
            out["note"] = "State Fire Marshal's 2025 LRA map; local agencies adopt it by ordinance."
        return out
    return {
        "available": True,
        "in_zone": False,
        "hazard_class": None,
        "note": "Not inside a mapped Fire Hazard Severity Zone (or on federal land, which the "
        "state doesn't map).",
        "check_url": OSFM_VIEWER,
        "source_id": "osfm",
    }


async def recent_fires(http: httpx.AsyncClient, lat: float, lon: float, miles: float) -> dict:
    miles = max(0.5, min(float(miles), 15.0))
    feats = await _arcgis_point(
        http,
        FIRES_URL,
        lat,
        lon,
        distance=str(miles),
        units="esriSRUnit_StatuteMile",
        orderByFields="YEAR_ DESC",
        resultRecordCount="10",
    )
    fires = [
        {
            "name": str(a.get("FIRE_NAME") or "").title() or "Unnamed",
            "year": a.get("YEAR_"),
            "acres": round(float(a.get("GIS_ACRES") or 0)),
        }
        for a in feats
    ]
    return {"within_miles": miles, "fires": fires, "source_id": "calfire-fires"}


def law_that_applies(responsibility: str | None, hazard_class: str | None) -> dict:
    """Which state defensible-space law applies (docs/rules/defensible-space.md)."""
    resp, cls = (responsibility or "").upper(), (hazard_class or "").title()
    if resp == "SRA" and cls:
        out = {
            "applies": True,
            "law": "PRC 4291",
            "enforced_by": "CAL FIRE",
            "covers": "Every building or structure",
        }
    elif resp == "LRA" and cls == "Very High":
        out = {
            "applies": True,
            "law": "Gov. Code 51182",
            "enforced_by": "the local fire agency",
            "covers": "Occupied dwellings and occupied structures, commercial included",
        }
    elif resp == "LRA":
        out = {
            "applies": False,
            "law": None,
            "note": "State defensible-space law covers LRA only in Very High zones; local "
            "ordinances may still apply.",
        }
    else:
        out = {"applies": None, "note": "Zone unknown, so the applicable law can't be decided."}
    out["zones"] = "0-5 ft (Zone 0, proposed), 5-30 ft, 30-100 ft, stopping at the property line"
    out["source_id"] = "rules"
    return out


# ---------------------------------------------------------------- agent


SYSTEM = """You research one building address for EmberScan, a wildfire defensible-space tool.
Use only what the tools return; never guess a hazard zone, agency, or fire. Steps:
1. lookup_address to get coordinates, county and city.
2. fire_hazard_zone with those coordinates.
3. recent_fires within 5 miles.
4. law_that_applies with the zone's responsibility area and hazard class.
5. submit_note: a 2-4 sentence plain-language summary for a homeowner or property manager,
   facts (each citing the source_id from the tool output it came from), and things the owner
   should confirm (for example which local fire agency enforces, or the zone when unknown).
If the address is outside California, say so first: EmberScan only has California's rules so far.
Never say a property is safe or compliant."""

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "lookup_address",
        "description": "Geocode the address: coordinates, county, incorporated city.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "fire_hazard_zone",
        "description": "Fire Hazard Severity Zone and responsibility area (SRA/LRA) at a point.",
        "parameters": {
            "type": "object",
            "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}},
            "required": ["lat", "lon"],
        },
    },
    {
        "type": "function",
        "name": "recent_fires",
        "description": "CAL FIRE fire perimeters from the last 5 years within a radius (miles).",
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "miles": {"type": "number"},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "type": "function",
        "name": "law_that_applies",
        "description": "Which state defensible-space law applies for a responsibility area "
        "(SRA or LRA) and hazard class (Moderate, High, Very High).",
        "parameters": {
            "type": "object",
            "properties": {
                "responsibility": {"type": "string"},
                "hazard_class": {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "submit_note",
        "description": "Submit the building note. Every fact must cite a source_id you received.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "facts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                            "source_id": {"type": "string"},
                        },
                        "required": ["label", "value", "source_id"],
                    },
                },
                "to_check": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "facts"],
        },
    },
]


@dataclass
class ResearchTools:
    address: str
    http: httpx.AsyncClient
    seen_sources: set[str] = field(default_factory=set)
    results: dict[str, Any] = field(default_factory=dict)

    @property
    def outside_california(self) -> bool:
        state = (self.results.get("address") or {}).get("state")
        return bool(state) and state != "California"

    async def call(self, name: str, args: dict[str, Any]) -> Any:
        if name == "lookup_address":
            out = self.results.get("address") or await geocode(self.http, self.address)
            self.results["address"] = out
        elif name == "fire_hazard_zone":
            if self.outside_california:
                out = {"available": False, "reason": "Outside California.", "source_id": "census"}
            else:
                out = await hazard_zone(self.http, float(args["lat"]), float(args["lon"]))
            self.results["zone"] = out
        elif name == "recent_fires":
            out = await recent_fires(
                self.http, float(args["lat"]), float(args["lon"]), args.get("miles", 5)
            )
            self.results["fires"] = out
        elif name == "law_that_applies":
            if self.outside_california:
                out = {
                    "applies": None,
                    "law": None,
                    "note": "This address is outside California. EmberScan only has California's "
                    "rules so far; this state's rules are not covered.",
                    "source_id": "census",
                }
            else:
                out = law_that_applies(args.get("responsibility"), args.get("hazard_class"))
            self.results["law"] = out
        else:
            raise ValueError(f"unknown tool {name}")
        if isinstance(out, dict) and out.get("source_id"):
            self.seen_sources.add(out["source_id"])
        return out


def verify_note(args: dict[str, Any], tools: ResearchTools) -> tuple[list[Fact], list[str]]:
    """Keep facts that cite a source the agent actually looked up."""
    facts, dropped = [], []
    for raw in args.get("facts") or []:
        try:
            f = Fact.model_validate(raw)
        except Exception:
            dropped.append(str(raw)[:80])
            continue
        if f.source_id in tools.seen_sources and f.label.strip() and f.value.strip():
            facts.append(f)
        else:
            dropped.append(f"{f.label}: cites '{f.source_id}' which was not looked up")
    return facts, dropped


def _fallback(tools: ResearchTools) -> tuple[str, list[Fact], list[str]]:
    a, z = tools.results.get("address") or {}, tools.results.get("zone") or {}
    fires, law = tools.results.get("fires") or {}, tools.results.get("law") or {}
    facts: list[Fact] = []
    if a.get("found"):
        facts.append(Fact(label="Matched address", value=a["matched_address"], source_id="census"))
        city = a.get("incorporated_city") or "Unincorporated area"
        facts.append(Fact(label="Jurisdiction", value=f"{city}, {a['county']}", source_id="census"))
    if z.get("in_zone"):
        facts.append(
            Fact(
                label="Fire hazard zone",
                value=f"{z['hazard_class']} ({z.get('responsibility')})",
                source_id=z["source_id"],
            )
        )
    if law.get("law"):
        facts.append(
            Fact(
                label="State law",
                value=f"{law['law']}, enforced by {law['enforced_by']}",
                source_id="rules",
            )
        )
    if fires.get("fires"):
        top = ", ".join(f"{f['name']} ({f['year']})" for f in fires["fires"][:3])
        facts.append(Fact(label="Recent fires nearby", value=top, source_id="calfire-fires"))
    checks = ["Confirm the hazard zone and enforcing fire agency with the local fire department."]
    if tools.outside_california:
        summary = (
            f"This address is in {a.get('state')}. EmberScan only has California's rules so far, "
            "so a scan here won't reflect this state's requirements."
        )
        return summary, facts, checks
    return "Background on this address from public map data.", facts, checks


async def _gather_all(tools: ResearchTools) -> None:
    """Deterministic pass used by the fallback when the model didn't call every tool."""
    if "address" not in tools.results:
        await tools.call("lookup_address", {})
    a = tools.results["address"]
    if not a.get("found"):
        return
    lat, lon = a["lat"], a["lon"]
    if "zone" not in tools.results:
        await tools.call("fire_hazard_zone", {"lat": lat, "lon": lon})
    if "fires" not in tools.results:
        await tools.call("recent_fires", {"lat": lat, "lon": lon, "miles": 5})
    if "law" not in tools.results:
        z = tools.results["zone"]
        await tools.call(
            "law_that_applies",
            {"responsibility": z.get("responsibility"), "hazard_class": z.get("hazard_class")},
        )


def _note(tools: ResearchTools, summary: str, facts: list[Fact], checks: list[str]) -> BuildingNote:
    a, z = tools.results.get("address") or {}, tools.results.get("zone") or {}
    return BuildingNote(
        address=tools.address,
        matched_address=a.get("matched_address"),
        lat=a.get("lat"),
        lon=a.get("lon"),
        state=a.get("state"),
        county=a.get("county"),
        city=a.get("incorporated_city"),
        hazard_class=z.get("hazard_class"),
        responsibility=z.get("responsibility"),
        summary=summary,
        facts=facts,
        to_check=checks,
        sources=[Source(id=s, **SOURCES[s]) for s in sorted(tools.seen_sources) if s in SOURCES],
    )


async def research_address(
    address: str,
    client: MetaClient,
    ledger: SpendLedger,
    http: httpx.AsyncClient,
    model: str = MODEL,
) -> BuildingNote:
    tools = ResearchTools(address=address, http=http)
    trace = [AgentStep(kind="plan", summary="Geocode, check hazard zone, recent fires, law.")]
    try:
        body: dict[str, Any] = {
            "model": model,
            "instructions": SYSTEM,
            "tools": TOOLS,
            "tool_choice": "auto",
            "reasoning": {"effort": "low"},
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "input": [{"role": "user", "content": f"Research this building address: {address}"}],
        }
        previous_id: str | None = None
        for _ in range(MAX_TURNS):
            ledger.check("research", token_cost(model, *EST_TURN_TOKENS))
            t0 = time.monotonic()
            req = body if previous_id is None else {**body, "previous_response_id": previous_id}
            resp = await client.create_response(req)
            usage = resp.get("usage") or {}
            ledger.record(
                "research",
                model,
                token_cost(
                    model, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
                ),
                {k: usage.get(k, 0) for k in ("input_tokens", "output_tokens")},
                time.monotonic() - t0,
            )
            previous_id = resp.get("id")
            calls = [o for o in resp.get("output", []) if o.get("type") == "function_call"]
            if not calls:
                body["input"] = [{"role": "user", "content": "Call submit_note now."}]
                continue
            outputs = []
            for call in calls:
                name = call.get("name", "")
                try:
                    args = json.loads(call.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                if name == "submit_note":
                    facts, dropped = verify_note(args, tools)
                    trace.append(
                        AgentStep(
                            kind="verify",
                            summary=f"{len(facts)} facts kept, {len(dropped)} dropped",
                            detail={"dropped": dropped},
                        )
                    )
                    if facts:
                        checks = [str(c) for c in args.get("to_check") or []][:6]
                        note = _note(tools, str(args.get("summary", "")).strip(), facts, checks)
                        return _finish(note, trace, ledger, model)
                    outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.get("call_id"),
                            "output": json.dumps({"accepted": False, "problems": dropped}),
                        }
                    )
                    continue
                try:
                    result = await tools.call(name, args)
                except Exception as e:  # tell the model; don't crash the research
                    result = {"error": str(e)[:200]}
                trace.append(AgentStep(kind="tool_call", summary=_step_text(name, result)))
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.get("call_id"),
                        "output": json.dumps(result),
                    }
                )
            body["input"] = outputs
        trace.append(AgentStep(kind="note", summary="Agent did not submit a note; using lookups."))
    except Exception as e:  # model or budget failure: still return the deterministic note
        trace.append(AgentStep(kind="note", summary=f"Agent stopped ({type(e).__name__})."))
    try:
        await _gather_all(tools)
    except Exception as e:
        trace.append(AgentStep(kind="note", summary=f"Lookup failed ({type(e).__name__})."))
    summary, facts, checks = _fallback(tools)
    return _finish(_note(tools, summary, facts, checks), trace, ledger, None)


def _finish(
    note: BuildingNote, trace: list[AgentStep], ledger: SpendLedger, model: str | None
) -> BuildingNote:
    note.trace = trace + [AgentStep(kind="output", summary=f"{len(note.facts)} facts")]
    note.model = model
    note.cost_usd = round(ledger.spent_usd, 6)
    return note


def _step_text(name: str, result: Any) -> str:
    if isinstance(result, dict) and "error" in result:
        return f"{name}: error"
    if name == "lookup_address":
        return f"lookup_address -> {result.get('matched_address') or 'no match'}"
    if name == "fire_hazard_zone":
        if not result.get("available"):
            return "fire_hazard_zone -> no source for this county"
        return f"fire_hazard_zone -> {result.get('hazard_class') or 'not in a zone'}"
    if name == "recent_fires":
        return f"recent_fires -> {len(result.get('fires', []))} within {result['within_miles']} mi"
    if name == "law_that_applies":
        return f"law_that_applies -> {result.get('law') or 'state law does not apply'}"
    return name


async def research_address_safe(address: str, ledger: SpendLedger) -> BuildingNote:
    """Entry point for the service: owns the HTTP and Meta clients."""
    async with (
        httpx.AsyncClient(timeout=HTTP_TIMEOUT_S, headers={"User-Agent": "EmberScan"}) as http,
        MetaClient() as client,
    ):
        note = await research_address(address, client, ledger, http=http)
        if note.model is None:  # the agent stopped (timeout, API error): one more try
            retry = await research_address(address, client, ledger, http=http)
            if retry.model is not None:
                retry.trace = [*note.trace[:-1], *retry.trace]  # keep why the first try stopped
                return retry
        return note


__all__ = ["BuildingNote", "research_address", "research_address_safe", "law_that_applies"]
