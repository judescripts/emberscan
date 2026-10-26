"""Tests for the deterministic rules engine (ADR 0004) and score (ADR 0007)."""

from __future__ import annotations

import random
from typing import Any

import pytest

from emberscan_workers.contracts import Hazard, Range, RuleResult
from emberscan_workers.rules import (
    VEGETATION_ANY,
    RulePack,
    compute_score,
    evaluate,
    load_pack,
    score_label,
)

ZONES = [
    {"id": "ALL", "name": "All", "min_ft": 0, "max_ft": 100},
    {"id": "Z0", "name": "Zone 0", "min_ft": 0, "max_ft": 5},
    {"id": "Z1", "name": "Zone 1", "min_ft": 0, "max_ft": 30},
    {"id": "Z12", "name": "Zones 1-2", "min_ft": 0, "max_ft": 100},
    {"id": "Z2", "name": "Zone 2", "min_ft": 30, "max_ft": 100},
]


def R(
    rule_id: str,
    classes: list[str],
    check: dict[str, Any],
    *,
    zone: str = "Z1",
    status: str = "adopted",
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "zone": zone,
        "title": f"Rule {rule_id}",
        "hazard_classes": classes,
        "check": check,
        "plain_language": "Test rule.",
        "status": status,
        "effective_date": None if status != "adopted" else "2013-07-01",
        "applies_to": "all",
        "citation_url": f"https://example.com/{rule_id}",
        "citation_label": f"Cite {rule_id}",
    }


def P(*rules: dict[str, Any]) -> RulePack:
    return RulePack.model_validate(
        {"pack_id": "test", "version": "1", "checked_on": "2026-10-26", "zones": ZONES,
         "rules": list(rules)}
    )


def rng(lo: float, hi: float) -> Range:
    return Range(min=lo, max=hi)


def H(hid: str, cls: str, label: str | None = None, **kw: Any) -> Hazard:
    kw.setdefault("confidence", "high")
    return Hazard(id=hid, cls=cls, concept=cls, track_id="0", label=label or cls, frames=[1], **kw)


def one(hazards: list[Hazard], pack: RulePack, **kw: Any) -> RuleResult:
    kw.setdefault("eave_depth_ft", None)
    res = evaluate(hazards, pack, **kw)
    assert len(res.results) == 1
    return res.results[0]


FIREWOOD_30 = P(R("Z1-04", ["woodpile"], {"type": "absent_within", "ft": 30}))


# ----------------------------------------------------------------------------- absent_within


def test_absent_within_whole_range_inside_fails() -> None:
    r = one([H("w", "woodpile", "Firewood", distance_ft=rng(8, 11))], FIREWOOD_30)
    assert r.status == "fail"
    assert r.hazard_ids == ["w"]
    assert r.reason == "Firewood measured 8–11 ft from the wall, inside the 30 ft zone."
    assert (r.title, r.zone, r.rule_status) == ("Rule Z1-04", "Z1", "adopted")
    assert r.citation_url == "https://example.com/Z1-04"
    assert r.citation_label == "Cite Z1-04"


def test_absent_within_straddle_needs_review() -> None:
    r = one([H("w", "woodpile", "Firewood", distance_ft=rng(25, 35))], FIREWOOD_30)
    assert r.status == "needs-review"
    assert "straddling" in r.reason and r.hazard_ids == ["w"]


def test_absent_within_outside_passes_without_driving_hazard() -> None:
    r = one([H("w", "woodpile", distance_ft=rng(31, 40))], FIREWOOD_30)
    assert r.status == "pass" and r.hazard_ids == []
    assert r.reason == "No woodpile seen within 30 ft."


def test_absent_within_unknown_distance_needs_review() -> None:
    r = one([H("w", "woodpile")], FIREWOOD_30)
    assert r.status == "needs-review"
    assert "wasn't measured" in r.reason


def test_absent_within_band_with_inner_edge() -> None:
    pack = P(R("Z2-01", ["dead_vegetation"], {"type": "absent_within", "ft": 100, "min_ft": 30},
               zone="Z2"))
    assert one([H("d", "dead_vegetation", distance_ft=rng(40, 50))], pack).status == "fail"
    assert one([H("d", "dead_vegetation", distance_ft=rng(10, 20))], pack).status == "pass"
    assert one([H("d", "dead_vegetation", distance_ft=rng(25, 35))], pack).status == "needs-review"


def test_low_confidence_never_fails() -> None:
    r = one([H("w", "woodpile", distance_ft=rng(1, 2), confidence="low")], FIREWOOD_30)
    assert r.status == "needs-review"
    assert "low confidence" in r.reason


def test_medium_confidence_can_fail() -> None:
    r = one([H("w", "woodpile", distance_ft=rng(1, 2), confidence="medium")], FIREWOOD_30)
    assert r.status == "fail"


def test_unrelated_classes_ignored_and_vegetation_any_expansion() -> None:
    pack = P(R("V", ["vegetation_any"], {"type": "absent_within", "ft": 5}, zone="Z0"))
    for cls in sorted(VEGETATION_ANY):
        assert one([H("v", cls, distance_ft=rng(1, 2))], pack).status == "fail", cls
    for cls in ("leaf_litter", "wood_mulch", "woodpile"):
        assert one([H("x", cls, distance_ft=rng(1, 2))], pack).status == "pass", cls


def test_exclude_list_is_respected() -> None:
    pack = P(R("V", ["vegetation_any"], {"type": "absent_within", "ft": 5, "exclude": ["tree"]}))
    assert one([H("t", "tree", distance_ft=rng(1, 2))], pack).status == "pass"
    assert one([H("s", "shrub", distance_ft=rng(1, 2))], pack).status == "fail"


# ----------------------------------------------------------------------------- eave strip

EAVE = P(R("E", ["vegetation_any"],
           {"type": "absent_within", "ft": "eave", "min_ft": 1, "max_ft": 5}))


def test_eave_strip_inside_low_limit_fails() -> None:
    r = one([H("s", "shrub", distance_ft=rng(0.5, 1.5))], EAVE, eave_depth_ft=rng(2, 2.5))
    assert r.status == "fail"
    assert "2–2.5 ft eave strip" in r.reason


def test_eave_strip_between_limits_needs_review() -> None:
    r = one([H("s", "shrub", distance_ft=rng(1.5, 2.2))], EAVE, eave_depth_ft=rng(2, 2.5))
    assert r.status == "needs-review"
    assert "edge of the 2–2.5 ft eave strip" in r.reason


def test_eave_strip_beyond_high_limit_passes() -> None:
    r = one([H("s", "shrub", distance_ft=rng(2.6, 3))], EAVE, eave_depth_ft=rng(2, 2.5))
    assert r.status == "pass"


def test_eave_is_clamped_to_min_and_max() -> None:
    # Eave 8-9 ft clamps to 5 ft: a shrub at 4-4.5 ft is inside, 5.5 ft is outside.
    assert one([H("s", "shrub", distance_ft=rng(4, 4.5))], EAVE,
               eave_depth_ft=rng(8, 9)).status == "fail"
    assert one([H("s", "shrub", distance_ft=rng(5.5, 6))], EAVE,
               eave_depth_ft=rng(8, 9)).status == "pass"
    # Eave 0.3-0.5 ft clamps up to the 1 ft minimum strip.
    assert one([H("s", "shrub", distance_ft=rng(0.6, 0.9))], EAVE,
               eave_depth_ft=rng(0.3, 0.5)).status == "fail"


def test_no_eave_measurement_needs_review_within_max() -> None:
    r = one([H("s", "shrub", distance_ft=rng(2, 3))], EAVE, eave_depth_ft=None)
    assert r.status == "needs-review"
    assert "eave depth wasn't measured" in r.reason
    # Beyond the 5 ft cap the hazard can't be under any eave.
    assert one([H("s", "shrub", distance_ft=rng(6, 7))], EAVE, eave_depth_ft=None).status == "pass"


# ----------------------------------------------------------------------------- min_clearance

CHIMNEY = P(R("ALL-01", ["tree", "tree_branch"],
              {"type": "min_clearance", "ft": 10, "reference": "chimney"}, zone="ALL"))
WINDOW = P(R("Z0-09", ["vegetation_any"],
             {"type": "min_clearance", "ft": 2, "reference": "window_door_vent"}, zone="ALL"))
TANK = P(R("Z12-01", ["propane_tank", "vegetation_any"],
           {"type": "min_clearance", "ft": 20, "reference": "propane_tank"}, zone="Z12"))
WALL = P(R("Z0-07", ["tree_branch"], {"type": "min_clearance", "ft": 1, "reference": "wall"},
           zone="Z0"))


def test_min_clearance_uses_clearance_to_matching_reference() -> None:
    br = H("b", "tree_branch", "Oak branch", distance_ft=rng(0, 1), clearance_ft=rng(4, 6),
           clearance_to="chimney")
    r = one([br], CHIMNEY)
    assert r.status == "fail"
    assert r.reason == "Oak branch measured 4–6 ft from the chimney, inside the 10 ft minimum."


def test_min_clearance_straddle_and_clear() -> None:
    mk = lambda c: H("b", "tree_branch", clearance_ft=c, clearance_to="chimney")  # noqa: E731
    assert one([mk(rng(8, 12))], CHIMNEY).status == "needs-review"
    r = one([mk(rng(12, 14))], CHIMNEY)
    assert r.status == "pass" and r.hazard_ids == ["b"] and "meeting the 10 ft" in r.reason


def test_min_clearance_ignores_unrelated_distance() -> None:
    # A branch 3 ft from the wall says nothing about the chimney.
    assert one([H("b", "tree_branch", distance_ft=rng(3, 4))], CHIMNEY).status == "pass"


def test_min_clearance_compound_reference() -> None:
    for to in ("window", "door", "vent"):
        s = H("s", "shrub", clearance_ft=rng(0.5, 1.5), clearance_to=to)
        assert one([s], WINDOW).status == "fail", to


def test_min_clearance_reference_object_uses_its_clearance() -> None:
    tank = H("t", "propane_tank", "Propane tank", distance_ft=rng(15, 18),
             clearance_ft=rng(12, 15), clearance_to="vegetation")
    r = one([tank], TANK)
    assert r.status == "fail" and r.hazard_ids == ["t"]
    unmeasured = H("t", "propane_tank", distance_ft=rng(15, 18))
    assert one([unmeasured], TANK).status == "needs-review"


def test_min_clearance_wall_reference_uses_distance() -> None:
    assert one([H("b", "tree_branch", distance_ft=rng(0.2, 0.6))], WALL).status == "fail"
    assert one([H("b", "tree_branch", distance_ft=rng(0.8, 1.4))], WALL).status == "needs-review"
    assert one([H("b", "tree_branch", distance_ft=rng(2, 3))], WALL).status == "pass"
    # Outside the rule's zone band (Z0 = 0-5 ft): not relevant.
    assert one([H("b", "tree_branch", distance_ft=rng(20, 25))], WALL).hazard_ids == []


# ----------------------------------------------------------------------------- max_height

GRASS = P(R("Z2-03", ["grass_tall"], {"type": "max_height", "inches": 4}, zone="Z2"))


def test_max_height_paths() -> None:
    mk = lambda h: H("g", "grass_tall", "Dry grass", distance_ft=rng(40, 50), height_in=h)  # noqa: E731
    r = one([mk(rng(10, 14))], GRASS)
    assert r.status == "fail"
    assert r.reason == "Dry grass measured 10–14 in tall, over the 4 in limit."
    assert one([mk(rng(3, 6))], GRASS).status == "needs-review"
    assert one([mk(rng(2, 3))], GRASS).status == "pass"
    assert one([mk(None)], GRASS).status == "needs-review"


def test_max_height_respects_zone_band() -> None:
    near = H("g", "grass_tall", distance_ft=rng(2, 4), height_in=rng(10, 14))
    r = one([near], GRASS)
    assert r.status == "pass" and "within 30–100 ft" in r.reason


# ----------------------------------------------------------------------------- present

ROOF = P(R("ALL-02", ["roof_debris"], {"type": "present", "location": "roof"}, zone="ALL"))
DECK = P(R("Z1-05", ["vegetation_any", "woodpile"],
           {"type": "present", "location": "under_or_adjacent_deck_balcony_stairs"}))


def test_present_fails_on_medium_and_reviews_on_low() -> None:
    r = one([H("r", "roof_debris", "Pine needles", confidence="medium")], ROOF)
    assert r.status == "fail" and r.reason == "Pine needles seen on the roof."
    assert one([H("r", "roof_debris", confidence="low")], ROOF).status == "needs-review"
    assert one([], ROOF).status == "pass"


def test_present_with_location_needs_location_evidence() -> None:
    under = H("w", "woodpile", "Firewood", clearance_ft=rng(0, 0), clearance_to="deck")
    r = one([under], DECK)
    assert r.status == "fail" and r.reason == "Firewood seen by the deck."
    elsewhere = H("w", "woodpile", distance_ft=rng(8, 11))
    assert one([elsewhere], DECK).status == "pass"


# ----------------------------------------------------------------------------- manual_review

MANUAL = P(R("ALL-03", ["shrub"], {"type": "manual_review"}, zone="ALL"))


def test_manual_review_paths() -> None:
    r = one([H("s", "shrub", "Juniper", distance_ft=rng(1, 2))], MANUAL)
    assert r.status == "needs-review" and r.hazard_ids == ["s"]
    assert r.reason.endswith("check on site.")
    assert one([], MANUAL).status == "pass"


def test_manual_review_with_reach() -> None:
    pack = P(R("Z0-16", ["combustible_fence"], {"type": "manual_review", "ft": 5}, zone="Z0"))
    assert one([H("f", "combustible_fence", distance_ft=rng(1, 2))], pack).status == "needs-review"
    assert one([H("f", "combustible_fence", distance_ft=rng(8, 9))], pack).status == "pass"


# ----------------------------------------------------------------------------- rule status


def test_proposed_violation_is_review_with_wording() -> None:
    pack = P(R("Z0-01", ["wood_mulch"], {"type": "absent_within", "ft": 5}, zone="Z0",
               status="proposed"))
    r = one([H("m", "wood_mulch", "Bark mulch", distance_ft=rng(0, 0.5))], pack)
    assert r.status == "needs-review"
    assert r.reason.startswith("Would not meet the proposed rule")
    assert r.rule_status == "proposed"


def test_guidance_violation_is_review_with_wording() -> None:
    pack = P(R("Z0-20", ["vehicle_or_boat"], {"type": "absent_within", "ft": 5}, zone="Z0",
               status="guidance"))
    r = one([H("v", "vehicle_or_boat", distance_ft=rng(2, 3))], pack)
    assert r.status == "needs-review" and r.reason.startswith("Below recommended practice")


def test_include_proposed_false_drops_proposed_and_guidance() -> None:
    pack = P(
        R("A", ["woodpile"], {"type": "absent_within", "ft": 30}),
        R("B", ["woodpile"], {"type": "absent_within", "ft": 5}, zone="Z0", status="proposed"),
        R("C", ["woodpile"], {"type": "absent_within", "ft": 5}, zone="Z0", status="guidance"),
    )
    res = evaluate([], pack, eave_depth_ft=None, include_proposed=False)
    assert [r.rule_id for r in res.results] == ["A"]
    assert (res.score.zone0_met, res.score.zone0_total) == (0, 0)


# ----------------------------------------------------------------------------- filming coverage


def test_unfilmed_sides_noted_in_pass_and_cap_score() -> None:
    res = evaluate([], FIREWOOD_30, eave_depth_ft=None, observed_sides={"N", "E"})
    r = res.results[0]
    assert r.status == "pass"
    assert r.reason == ("No woodpile seen within 30 ft on the filmed sides; "
                        "the S and W sides were not filmed.")
    assert res.score.unfilmed_sides == ["S", "W"]
    assert res.score.score == 80 and res.score.label == "A few fixes needed"


def test_nothing_filmed_is_never_a_pass() -> None:
    res = evaluate([], FIREWOOD_30, eave_depth_ft=None, observed_sides=set())
    assert res.results[0].status == "needs-review"
    assert "not filmed" in res.results[0].reason


def test_all_sides_filmed_no_cap_or_note() -> None:
    res = evaluate([], FIREWOOD_30, eave_depth_ft=None, observed_sides={"N", "E", "S", "W"})
    assert res.score.score == 100 and res.score.unfilmed_sides == []
    assert "filmed" not in res.results[0].reason


# ----------------------------------------------------------------------------- score


def _res(zone: str, status: str, rule_status: str = "adopted", rid: str = "X") -> RuleResult:
    return RuleResult(rule_id=rid, title="t", zone=zone, rule_status=rule_status, status=status,
                      reason="r", citation_url="https://example.com", citation_label="c")


def test_score_penalties_by_zone() -> None:
    results = [_res("ALL", "fail"), _res("Z1", "fail"), _res("Z12", "fail"), _res("Z2", "fail")]
    assert compute_score(results, []).score == 100 - 10 - 8 - 8 - 4
    reviews = [_res("ALL", "needs-review"), _res("Z1", "needs-review"), _res("Z2", "needs-review")]
    assert compute_score(reviews, []).score == 100 - 5 - 4 - 2


def test_score_ignores_proposed_and_guidance() -> None:
    results = [_res("Z0", "needs-review", "proposed"), _res("Z0", "needs-review", "guidance"),
               _res("Z0", "pass", "proposed")]
    block = compute_score(results, [])
    assert block.score == 100
    assert (block.zone0_met, block.zone0_total) == (1, 2)
    assert (block.fails, block.reviews, block.passes) == (0, 2, 1)


def test_score_floor_and_cap() -> None:
    assert compute_score([_res("ALL", "fail")] * 15, []).score == 0
    assert compute_score([_res("Z2", "fail")], ["W"]).score == 80
    assert compute_score([_res("ALL", "fail")] * 3, ["W"]).score == 70


@pytest.mark.parametrize(
    ("score", "label"),
    [(100, "In good shape"), (90, "In good shape"), (89, "A few fixes needed"),
     (75, "A few fixes needed"), (74, "Needs work"), (0, "Needs work")],
)
def test_score_labels(score: int, label: str) -> None:
    assert score_label(score) == label


# ----------------------------------------------------------------------------- ordering


def test_results_ordered_by_status_zone_id() -> None:
    pack = P(
        R("Z2-01", ["dead_vegetation"], {"type": "absent_within", "ft": 100, "min_ft": 30},
          zone="Z2"),
        R("Z1-02", ["woodpile"], {"type": "absent_within", "ft": 30}),
        R("Z1-01", ["woodpile"], {"type": "absent_within", "ft": 30}),
        R("ALL-01", ["shrub"], {"type": "manual_review"}, zone="ALL"),
        R("Z0-01", ["woodpile"], {"type": "absent_within", "ft": 5}, zone="Z0",
          status="proposed"),
        R("Z12-01", ["outbuilding"], {"type": "absent_within", "ft": 30}, zone="Z12"),
    )
    hz = [H("w", "woodpile", distance_ft=rng(1, 2)), H("s", "shrub", distance_ft=rng(1, 2))]
    ids = [r.rule_id for r in evaluate(hz, pack, eave_depth_ft=None).results]
    assert ids == ["Z1-01", "Z1-02", "ALL-01", "Z0-01", "Z12-01", "Z2-01"]


# ----------------------------------------------------------------------------- real pack


@pytest.fixture(scope="module")
def us_ca() -> RulePack:
    return load_pack("us-ca")


def _walkaround() -> list[Hazard]:
    return [
        H("h-wood_mulch-0", "wood_mulch", "Bark mulch", distance_ft=rng(0, 0.5)),
        H("h-woodpile-0", "woodpile", "Firewood", distance_ft=rng(8, 11)),
        H("h-shrub-0", "shrub", "Juniper", distance_ft=rng(0.5, 1.5),
          clearance_ft=rng(0.5, 1.5), clearance_to="window"),
        H("h-fence_attached-0", "fence_attached", "Wood fence", distance_ft=rng(0, 0.3)),
        H("h-propane_tank-0", "propane_tank", "Propane tank", distance_ft=rng(18, 21),
          clearance_ft=rng(12, 15), clearance_to="vegetation"),
    ]


def test_us_ca_smoke(us_ca: RulePack) -> None:
    res = evaluate(_walkaround(), us_ca, eave_depth_ft=rng(1.5, 2),
                   observed_sides={"N", "E", "S", "W"})
    by_id = {r.rule_id: r for r in res.results}
    assert len(by_id) == len(us_ca.rules)

    assert by_id["Z1-04"].status == "fail"
    assert by_id["Z1-04"].hazard_ids == ["h-woodpile-0"]
    assert "8–11 ft" in by_id["Z1-04"].reason

    assert by_id["Z0-01"].status == "needs-review"
    assert by_id["Z0-01"].reason.startswith("Would not meet the proposed rule")
    assert by_id["Z0-01"].hazard_ids == ["h-wood_mulch-0"]

    assert by_id["Z0-09"].status == "needs-review"
    assert by_id["Z0-09"].hazard_ids == ["h-shrub-0"]
    assert by_id["Z0-15"].status == "needs-review"
    assert by_id["Z12-01"].status == "fail"
    assert by_id["Z12-01"].hazard_ids == ["h-propane_tank-0"]

    # Firewood at 8-11 ft is outside Zone 0 and not near a deck; nothing proposed fails.
    assert by_id["Z0-03"].status == "pass"
    assert by_id["Z1-05"].status == "pass"
    assert all(r.status != "fail" for r in res.results if r.rule_status != "adopted")

    s = res.score
    assert s.fails == 2
    assert s.fails + s.reviews + s.passes == len(us_ca.rules)
    assert 0 <= s.zone0_met <= s.zone0_total == sum(
        r.zone == "Z0" and r.status == "proposed" for r in us_ca.rules
    )
    assert s.score == 100 - 8 - 8 - 5 - 5  # Z1-04, Z12-01 fail; ALL-03, ALL-04 review
    assert s.label == "Needs work"


def test_us_ca_without_proposed(us_ca: RulePack) -> None:
    res = evaluate(_walkaround(), us_ca, eave_depth_ft=None, include_proposed=False)
    assert all(r.rule_status == "adopted" for r in res.results)
    assert res.score.zone0_total == 0


def test_determinism(us_ca: RulePack) -> None:
    hz = _walkaround()
    kw: dict[str, Any] = {"eave_depth_ft": rng(1.5, 2), "observed_sides": {"N", "S", "E"}}
    first = evaluate(hz, us_ca, **kw).model_dump_json()
    assert evaluate(hz, us_ca, **kw).model_dump_json() == first
    shuffled = hz[:]
    random.Random(7).shuffle(shuffled)
    assert evaluate(shuffled, us_ca, **kw).model_dump_json() == first
