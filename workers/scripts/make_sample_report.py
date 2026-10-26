"""Write docs/contracts/report.sample.json: a realistic Report for building the web UI
before the live pipeline is wired. Values are illustrative (clearly marked sample)."""

from __future__ import annotations

from pathlib import Path

from emberscan_workers.contracts import (
    AgentStep,
    BBox,
    Evidence,
    Fix,
    Hazard,
    Range,
    Report,
    RuleResult,
    ScoreBlock,
)

ROOT = Path(__file__).resolve().parents[2]
CA = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=PRC&sectionNum=4291"


def ev(i: int, x0: float, y0: float, x1: float, y1: float) -> Evidence:
    return Evidence(frame_index=i, timestamp_ms=i * 333, bbox=BBox(left=x0, top=y0, right=x1, bottom=y1))


hazards = [
    Hazard(id="h-wood_mulch-0", cls="wood_mulch", concept="bark mulch", track_id="0",
           label="Bark mulch bed along the front wall", frames=list(range(0, 60)), confidence="high",
           sam_confidence=0.81, method="marker", distance_ft=Range(min=0, max=0.5), zone="Z0", side="S",
           narration="South side, bark mulch right up against the wall.", evidence=[ev(12, 0, 300, 1280, 720)]),
    Hazard(id="h-shrub-0", cls="shrub", concept="shrub", track_id="0", label="Juniper under the front window",
           frames=list(range(20, 70)), confidence="high", sam_confidence=0.77, method="marker",
           distance_ft=Range(min=1.5, max=2.5), clearance_ft=Range(min=0.5, max=1.5), clearance_to="window",
           zone="Z0", side="S", evidence=[ev(40, 380, 260, 760, 640)]),
    Hazard(id="h-woodpile-0", cls="woodpile", concept="stacked firewood", track_id="1",
           label="Stacked firewood by the side fence", frames=list(range(90, 130)), confidence="high",
           sam_confidence=0.88, method="marker", distance_ft=Range(min=8, max=11), zone="Z1", side="E",
           narration="This woodpile belongs to unit 6.", evidence=[ev(110, 520, 330, 760, 560)]),
    Hazard(id="h-combustible_fence-0", cls="combustible_fence", concept="wooden fence", track_id="0",
           label="Wooden fence joining the wall", frames=list(range(125, 160)), confidence="medium",
           sam_confidence=0.69, method="marker", distance_ft=Range(min=0, max=0.3), zone="Z0", side="E",
           evidence=[ev(140, 700, 120, 1280, 640)]),
    Hazard(id="h-shrub-1", cls="shrub", concept="shrub", track_id="3", label="Rosemary hedge near the corner",
           frames=list(range(170, 200)), confidence="medium", sam_confidence=0.64, method="marker",
           distance_ft=Range(min=4, max=7), zone="Z0", zone_uncertain=True, side="W",
           evidence=[ev(185, 200, 380, 560, 650)]),
]

results = [
    RuleResult(rule_id="Z1-04", title="No exposed firewood piles in Zone 1", zone="Z1", rule_status="adopted",
               status="fail", reason="Firewood measured 8â€“11 ft from the wall, inside the 30 ft zone.",
               hazard_ids=["h-woodpile-0"], citation_url=CA, citation_label="14 CCR 1299.03(a)"),
    RuleResult(rule_id="Z0-01", title="No combustible materials in Zone 0", zone="Z0", rule_status="proposed",
               status="needs-review", reason="Would not meet the proposed Zone 0 rule: bark mulch within 0â€“0.5 ft.",
               hazard_ids=["h-wood_mulch-0"], citation_url=CA, citation_label="Zone 0 draft (Aug 2026)"),
    RuleResult(rule_id="Z0-09", title="No vegetation within 2 ft of windows, doors or vents", zone="Z0",
               rule_status="proposed", status="needs-review",
               reason="Would not meet the proposed rule: juniper about 0.5â€“1.5 ft from the window.",
               hazard_ids=["h-shrub-0"], citation_url=CA, citation_label="Zone 0 draft (Aug 2026)"),
    RuleResult(rule_id="Z0-14", title="No woody shrubs in Zone 0", zone="Z0", rule_status="proposed",
               status="needs-review", reason="Rosemary at 4â€“7 ft straddles the 5 ft line. Confirm with a tape.",
               hazard_ids=["h-shrub-1"], citation_url=CA, citation_label="Zone 0 draft (Aug 2026)"),
    RuleResult(rule_id="ALL-02", title="Roof free of leaves, needles and other plant debris", zone="ALL",
               rule_status="adopted", status="pass", reason="Nothing found on the filmed roof edges.",
               citation_url=CA, citation_label="PRC 4291(a)(4)"),
]

fixes = [
    Fix(id="f1", title="Move the firewood 30 ft from the building or into a closed metal box",
        why="A woodpile near the wall burns long and hot right where embers land.", rule_ids=["Z1-04"],
        hazard_ids=["h-woodpile-0"], required=True, effort="S", cost_band="$", owner="Owner", priority=1),
    Fix(id="f2", title="Replace bark mulch within 5 ft of the wall with gravel or pavers",
        why="Mulch against siding is one of the most common ways embers start a house fire.", rule_ids=["Z0-01"],
        hazard_ids=["h-wood_mulch-0"], required=False, effort="M", cost_band="$$", owner="HOA", priority=2),
    Fix(id="f3", title="Remove the juniper under the front window",
        why="Junipers are oily and burn hot; windows are a weak point.", rule_ids=["Z0-09"],
        hazard_ids=["h-shrub-0"], required=False, effort="S", cost_band="$", owner="HOA", priority=3),
]

trace = [
    AgentStep(kind="plan", summary="Check every zone; confirm borderline distances; use narration for ownership."),
    AgentStep(kind="tool_call", summary="list_hazards(zone='Z0')", detail={"returned": 3}),
    AgentStep(kind="tool_call", summary="check_rules(scan)", detail={"fail": 1, "needs_review": 3, "pass": 1}),
    AgentStep(kind="tool_call", summary="get_narration(110 sâ€“120 s)", detail={"text": "This woodpile belongs to unit 6."}),
    AgentStep(kind="verify", summary="All 3 fixes cite existing rule and hazard ids. 0 claims dropped."),
    AgentStep(kind="output", summary="3 fixes, 1 required."),
]

report = Report(
    scan_id="sample-scan", building_label="Building B Â· Units 5â€“8", created_at="2026-10-26T12:00:00Z",
    pack_id="us-ca", pack_version="2026-10-26",
    video={"duration_s": 72.0, "fps": 30, "width": 1280, "height": 720, "sam_fps": 3},
    eave_depth_ft=Range(min=1.5, max=2.0), hazards=hazards, results=results,
    score=ScoreBlock(score=92, label="In good shape", fails=1, reviews=3, passes=1, zone0_met=0, zone0_total=3),
    fixes=fixes, agent_trace=trace, cost={"spent_usd": 0.31, "calls": 14},
)

out = ROOT / "docs" / "contracts" / "report.sample.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
print("wrote", out)
