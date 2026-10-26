"""Deterministic rules engine: hazards + rule pack -> rule results + score (ADR 0004, ADR 0007).

The engine is a pure function. A model never decides compliance: every result comes from a
rule's typed `check` applied to measured ranges, so the same scan always gives the same report.

Decision logic, per hazard and per rule:

* A hazard is *relevant* to a rule when its class matches the rule's `hazard_classes`
  (`vegetation_any` expands to every plant class) and it lies in the rule's area.
* Each relevant hazard yields one outcome: **violation** (the whole measured range breaks the
  threshold), **review** (the range straddles it, or the measurement is missing) or **clear**.
* A low-confidence hazard can never produce a violation; it is downgraded to review.
* A violation fails an `adopted` rule. For `proposed` / `guidance` rules it becomes
  needs-review ("would not meet the proposed rule" / "below recommended practice").
* With no relevant hazards a rule passes only if its area was filmed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from ..contracts import Hazard, Range, RuleResult, RuleStatus, ScoreBlock
from .pack import (
    AbsentWithin,
    ManualReview,
    MaxHeight,
    MinClearance,
    Present,
    Rule,
    RulePack,
    Zone,
)

__all__ = [
    "GROUND_SIDES",
    "VEGETATION_ANY",
    "EngineResult",
    "compute_score",
    "evaluate",
    "score_label",
]

#: Plant classes that the catch-all `vegetation_any` stands for in a rule's hazard_classes.
#: Leaf litter and wood mulch are ground fuels, not plants: rules must list them explicitly.
VEGETATION_ANY: frozenset[str] = frozenset(
    {
        "shrub",
        "tree",
        "tree_branch",
        "grass_tall",
        "herbaceous_planting",
        "potted_plant",
        "dead_vegetation",
        "ladder_fuel",
        "vegetation_any",  # the SAM "plant" catch-all concept itself
    }
)

#: The four walls a walkaround must film. Missing any of them caps the score.
GROUND_SIDES: tuple[str, ...] = ("N", "E", "S", "W")

#: Points lost per failed adopted rule, by zone (ADR 0007). Needs-review loses half.
ZONE_PENALTY: dict[str, int] = {"ALL": 10, "Z0": 10, "Z1": 8, "Z12": 8, "Z2": 4}
DEFAULT_PENALTY = 8
UNFILMED_CAP = 80

_STATUS_ORDER: dict[str, int] = {"fail": 0, "needs-review": 1, "pass": 2}
_ZONE_ORDER: dict[str, int] = {"ALL": 0, "Z0": 1, "Z1": 2, "Z12": 3, "Z2": 4}

# Locations a hazard's class already implies (roof_debris is on the roof by definition).
_CLASS_IMPLIED_LOCATIONS = frozenset({"roof", "gutter"})
# Filler words dropped when splitting compound references like "window_door_vent".
_STOPWORDS = frozenset({"under", "or", "and", "adjacent", "to", "attached", "over", "near"})

_CLASS_NAMES = {"vegetation_any": "vegetation", "grass_tall": "tall grass"}

Outcome = Literal["violation", "review", "clear"]


class EngineResult(BaseModel):
    """Everything the engine produces for one scan: ordered rule results and the score."""

    results: list[RuleResult]
    score: ScoreBlock


@dataclass(frozen=True)
class _Finding:
    """One relevant hazard's outcome for one rule, with a plain-language fragment."""

    hazard: Hazard
    outcome: Outcome
    text: str  # e.g. "Firewood measured 8–11 ft from the wall, inside the 30 ft zone"


# --------------------------------------------------------------------------- formatting


def _num(x: float) -> str:
    return f"{round(x, 1):g}"


def _span(lo: float, hi: float) -> str:
    return _num(lo) if round(lo, 1) == round(hi, 1) else f"{_num(lo)}–{_num(hi)}"


def _band(lo: float, hi: float) -> str:
    """A zone band from the wall: "30" for 0-30 ft, "30–100" for 30-100 ft."""
    return _num(hi) if lo <= 0 else _span(lo, hi)


def _bounds(r: Range) -> tuple[float, float]:
    return (min(r.min, r.max), max(r.min, r.max))


def _fmt(r: Range) -> str:
    return _span(*_bounds(r))


def _name(h: Hazard) -> str:
    label = (h.label or h.cls.replace("_", " ")).strip()
    return label[:1].upper() + label[1:]


def _lower_first(text: str) -> str:
    if len(text) > 1 and text[1].islower():
        return text[:1].lower() + text[1:]
    return text


def _join(words: list[str], conj: str = "or") -> str:
    if len(words) <= 1:
        return "".join(words)
    return f"{', '.join(words[:-1])} {conj} {words[-1]}"


def _tokens(name: str) -> set[str]:
    norm = name.strip().lower().replace(" ", "_").replace("-", "_")
    return {t for t in norm.split("_") if t and t not in _STOPWORDS}


def _human_ref(reference: str) -> str:
    parts = [t for t in reference.lower().split("_") if t and t not in _STOPWORDS]
    return _join(parts) if parts else reference


def _human_classes(classes: Iterable[str]) -> str:
    names = {_CLASS_NAMES.get(c, c.replace("_", " ")) for c in classes}
    return _join(sorted(names))


# --------------------------------------------------------------------------- matching


def _matches_class(rule: Rule, h: Hazard) -> bool:
    classes = set(rule.hazard_classes)
    if "vegetation_any" in classes:
        classes |= VEGETATION_ANY
    excluded = set(getattr(rule.check, "exclude", []) or [])
    return h.cls in classes and h.cls not in excluded


def _in_band(h: Hazard, lo: float | None, hi: float | None) -> bool:
    """False only when the hazard's distance is known and lies wholly outside lo..hi."""
    if h.distance_ft is None:
        return True
    d_lo, d_hi = _bounds(h.distance_ft)
    if hi is not None and d_lo > hi:
        return False
    return not (lo is not None and d_hi < lo)


def _refers_to(clearance_to: str | None, reference: str) -> bool:
    return bool(clearance_to) and bool(_tokens(clearance_to or "") & _tokens(reference))


# --------------------------------------------------------------------------- checks


def _check_absent_within(c: AbsentWithin, h: Hazard, eave: Range | None) -> _Finding | None:
    if c.ft == "eave":
        return _check_eave_strip(c, h, eave)
    lo = c.min_ft or 0.0
    hi = float(c.ft)
    band = _band(lo, hi)
    if h.distance_ft is None:
        return _Finding(
            h,
            "review",
            f"{_name(h)} was seen but its distance from the wall "
            f"wasn't measured, so it may be inside the {band} ft zone",
        )
    d_lo, d_hi = _bounds(h.distance_ft)
    if d_lo > hi or d_hi < lo:
        return None
    where = f"{_name(h)} measured {_fmt(h.distance_ft)} ft from the wall"
    if d_lo >= lo and d_hi <= hi:
        return _Finding(h, "violation", f"{where}, inside the {band} ft zone")
    return _Finding(h, "review", f"{where}, straddling the edge of the {band} ft zone")


def _check_eave_strip(c: AbsentWithin, h: Hazard, eave: Range | None) -> _Finding | None:
    lo_clamp = c.min_ft if c.min_ft is not None else 0.0
    hi_clamp = c.max_ft if c.max_ft is not None else float("inf")

    def clamp(x: float) -> float:
        return max(lo_clamp, min(hi_clamp, x))

    if eave is None:
        # Unknown eave: the strip is at least min_ft and at most max_ft deep.
        lim_lo, lim_hi = lo_clamp, hi_clamp
    else:
        e_lo, e_hi = _bounds(eave)
        lim_lo, lim_hi = clamp(e_lo), clamp(e_hi)
    if h.distance_ft is None:
        return _Finding(
            h,
            "review",
            f"{_name(h)} was seen but its distance from the wall "
            "wasn't measured, so it may be under the eave",
        )
    d_lo, d_hi = _bounds(h.distance_ft)
    if d_lo > lim_hi:
        return None
    where = f"{_name(h)} measured {_fmt(h.distance_ft)} ft from the wall"
    if d_hi <= lim_lo:
        strip = f"{_num(lim_lo)} ft" if eave is None else f"{_span(lim_lo, lim_hi)} ft eave"
        return _Finding(h, "violation", f"{where}, inside the {strip} strip")
    if eave is None:
        return _Finding(h, "review", f"{where}, but the eave depth wasn't measured")
    return _Finding(
        h, "review", f"{where}, at the edge of the {_span(lim_lo, lim_hi)} ft eave strip"
    )


def _check_min_clearance(c: MinClearance, h: Hazard) -> _Finding | None:
    ref = c.reference
    limit = f"{_num(c.ft)} ft minimum"
    if ref and _refers_to(h.clearance_to, ref) and h.clearance_ft is not None:
        measured = h.clearance_ft
        where = f"{_name(h)} measured {_fmt(measured)} ft from the {h.clearance_to}"
    elif ref is None or ref == "wall":
        if h.distance_ft is None:
            return _Finding(
                h, "review", f"{_name(h)} was seen but its distance from the wall wasn't measured"
            )
        measured = h.distance_ft
        where = f"{_name(h)} measured {_fmt(measured)} ft from the wall"
    elif h.cls == ref:
        # The hazard is the reference object itself: clearance_ft is its clearance to the
        # nearest subject (e.g. a propane tank's clearance to vegetation).
        if h.clearance_ft is None:
            return _Finding(h, "review", f"{_name(h)} was seen but its clearance wasn't measured")
        measured = h.clearance_ft
        where = f"{_name(h)} has {_fmt(measured)} ft of clearance"
    elif _refers_to(h.clearance_to, ref):
        return _Finding(
            h,
            "review",
            f"{_name(h)} is near the {_human_ref(ref)} but the clearance wasn't measured",
        )
    else:
        return None  # no measurement relates this hazard to the rule's reference
    m_lo, m_hi = _bounds(measured)
    if m_hi < c.ft:
        return _Finding(h, "violation", f"{where}, inside the {limit}")
    if m_lo >= c.ft:
        return _Finding(h, "clear", f"{where}, meeting the {limit}")
    return _Finding(h, "review", f"{where}, straddling the {limit}")


def _check_max_height(c: MaxHeight, h: Hazard) -> _Finding:
    limit = f"{_num(c.inches)} in limit"
    if h.height_in is None:
        return _Finding(h, "review", f"{_name(h)} was seen but its height wasn't measured")
    lo, hi = _bounds(h.height_in)
    where = f"{_name(h)} measured {_fmt(h.height_in)} in tall"
    if lo > c.inches:
        return _Finding(h, "violation", f"{where}, over the {limit}")
    if hi <= c.inches:
        return _Finding(h, "clear", f"{where}, within the {limit}")
    return _Finding(h, "review", f"{where}, around the {limit}")


def _where_seen(h: Hazard, location: str | None) -> str:
    if location == "roof":
        return " on the roof"
    if location == "gutter":
        return " in the gutters"
    if location and h.clearance_to:
        return f" by the {h.clearance_to}"
    if h.distance_ft is not None:
        return f" {_fmt(h.distance_ft)} ft from the wall"
    return ""


def _check_present(c: Present, h: Hazard) -> _Finding | None:
    loc = c.location
    if loc and loc not in _CLASS_IMPLIED_LOCATIONS and not _refers_to(h.clearance_to, loc):
        return None  # nothing ties this hazard to the rule's location (e.g. under the deck)
    return _Finding(h, "violation", f"{_name(h)} seen{_where_seen(h, loc)}")


def _check_manual(c: ManualReview, h: Hazard) -> _Finding | None:
    if c.ft is not None and not _in_band(h, None, c.ft):
        return None
    where = f" {_fmt(h.distance_ft)} ft from the wall" if h.distance_ft is not None else ""
    return _Finding(h, "review", f"{_name(h)} seen{where}, which video can't settle")


def _finding(rule: Rule, zone: Zone | None, h: Hazard, eave: Range | None) -> _Finding | None:
    c = rule.check
    if isinstance(c, AbsentWithin):
        f = _check_absent_within(c, h, eave)
    else:
        # Other checks have no distance of their own: keep to the rule's zone band.
        if zone is not None and not _in_band(h, zone.min_ft, zone.max_ft):
            return None
        if isinstance(c, MinClearance):
            f = _check_min_clearance(c, h)
        elif isinstance(c, MaxHeight):
            f = _check_max_height(c, h)
        elif isinstance(c, Present):
            f = _check_present(c, h)
        else:
            f = _check_manual(c, h)
    if f is not None and f.outcome == "violation" and h.confidence == "low":
        return _Finding(h, "review", f"{f.text}, but the detection is low confidence")
    return f


# --------------------------------------------------------------------------- per rule


def _summarize(findings: list[_Finding]) -> str:
    text = findings[0].text
    if len(findings) > 1:
        text += f" (and {len(findings) - 1} more)"
    return text


def _unfilmed_note(unfilmed: list[str]) -> str:
    if not unfilmed:
        return ""
    noun = "side was" if len(unfilmed) == 1 else "sides were"
    return f"; the {_join(unfilmed, 'and')} {noun} not filmed"


def _evaluate_rule(
    rule: Rule,
    zone: Zone | None,
    hazards: list[Hazard],
    eave: Range | None,
    observed: bool,
    unfilmed: list[str],
) -> RuleResult:
    findings = [
        f
        for h in hazards
        if _matches_class(rule, h)
        if (f := _finding(rule, zone, h, eave)) is not None
    ]
    violations = [f for f in findings if f.outcome == "violation"]
    reviews = [f for f in findings if f.outcome == "review"]
    clears = [f for f in findings if f.outcome == "clear"]

    status: RuleStatus
    driving: list[_Finding]
    if violations:
        driving = violations
        text = _summarize(violations)
        if rule.status == "adopted":
            status, reason = "fail", f"{text}."
        elif rule.status == "proposed":
            status, reason = "needs-review", f"Would not meet the proposed rule: {text}."
        else:
            status, reason = "needs-review", f"Below recommended practice: {text}."
    elif reviews:
        driving = reviews
        status, reason = "needs-review", f"{_summarize(reviews)}; check on site."
    elif not observed:
        driving = []
        status = "needs-review"
        reason = "This area was not filmed, so the rule can't be checked; check on site."
    elif clears:
        driving = clears
        status, reason = "pass", f"{_summarize(clears)}{_unfilmed_note(unfilmed)}."
    else:
        driving = []
        status = "pass"
        reason = f"No {_human_classes(rule.hazard_classes)} seen{_scope(rule, zone)}"
        reason += f"{' on the filmed sides' if unfilmed else ''}{_unfilmed_note(unfilmed)}."

    return RuleResult(
        rule_id=rule.id,
        title=rule.title,
        zone=rule.zone,
        rule_status=rule.status,
        status=status,
        reason=reason,
        hazard_ids=[f.hazard.id for f in driving],
        citation_url=str(rule.citation_url),
        citation_label=rule.citation_label,
    )


def _scope(rule: Rule, zone: Zone | None) -> str:
    """Where the engine looked, for "No firewood seen within 30 ft" style pass reasons."""
    c = rule.check
    if isinstance(c, AbsentWithin):
        if c.ft == "eave":
            return " under the eave"
        return f" within {_band(c.min_ft or 0.0, float(c.ft))} ft"
    if isinstance(c, MinClearance) and c.reference and c.reference != "wall":
        return f" too close to the {_human_ref(c.reference)}"
    if isinstance(c, Present) and c.location:
        return {"roof": " on the roof", "gutter": " in the gutters"}.get(
            c.location, f" by the {_human_ref(c.location)}"
        )
    if isinstance(c, ManualReview) and c.ft is not None:
        return f" within {_num(c.ft)} ft"
    if zone is not None and zone.max_ft is not None:
        return f" within {_band(zone.min_ft or 0.0, zone.max_ft)} ft"
    return ""


# --------------------------------------------------------------------------- score


def score_label(score: int) -> str:
    """Plain-language label for a score (ADR 0007)."""
    if score >= 90:
        return "In good shape"
    if score >= 75:
        return "A few fixes needed"
    return "Needs work"


def compute_score(results: list[RuleResult], unfilmed_sides: list[str]) -> ScoreBlock:
    """Score per ADR 0007. Only adopted rules move the score; proposed Zone 0 rules feed the
    separate readiness meter (zone0_met / zone0_total)."""
    score = 100
    for r in results:
        if r.rule_status != "adopted" or r.status == "pass":
            continue
        penalty = ZONE_PENALTY.get(r.zone, DEFAULT_PENALTY)
        score -= penalty if r.status == "fail" else penalty // 2
    if unfilmed_sides:
        score = min(score, UNFILMED_CAP)
    score = max(score, 0)
    zone0 = [r for r in results if r.zone == "Z0" and r.rule_status == "proposed"]
    return ScoreBlock(
        score=score,
        label=score_label(score),
        fails=sum(r.status == "fail" for r in results),
        reviews=sum(r.status == "needs-review" for r in results),
        passes=sum(r.status == "pass" for r in results),
        zone0_met=sum(r.status == "pass" for r in zone0),
        zone0_total=len(zone0),
        unfilmed_sides=list(unfilmed_sides),
    )


# --------------------------------------------------------------------------- entry point


def _sort_key(r: RuleResult) -> tuple[int, int, str, str]:
    return (_STATUS_ORDER[r.status], _ZONE_ORDER.get(r.zone, len(_ZONE_ORDER)), r.zone, r.rule_id)


def evaluate(
    hazards: list[Hazard],
    pack: RulePack,
    *,
    eave_depth_ft: Range | None,
    include_proposed: bool = True,
    observed_sides: set[str] | None = None,
) -> EngineResult:
    """Evaluate every rule in `pack` against the scan's hazards.

    Args:
        hazards: Hazards from the measurement stage. Input order doesn't affect the output.
        pack: The rule pack (e.g. `load_pack("us-ca")`).
        eave_depth_ft: Measured eave depth, used by `absent_within` checks with `ft: "eave"`.
        include_proposed: When False, proposed and guidance rules are left out entirely.
        observed_sides: Wall sides the video covered. None means coverage is unknown and is
            treated as complete. Missing N/E/S/W sides cap the score and are noted in passes.

    Returns:
        One RuleResult per evaluated rule, ordered fail -> needs-review -> pass, then zone
        (ALL, Z0, Z1, Z12, Z2), then rule id; plus the ScoreBlock.
    """
    ordered = sorted(hazards, key=lambda h: h.id)
    zones = {z.id: z for z in pack.zones}
    if observed_sides is None:
        observed, unfilmed = True, []
    else:
        observed = any(s in observed_sides for s in GROUND_SIDES)
        unfilmed = [s for s in GROUND_SIDES if s not in observed_sides]
    results = [
        _evaluate_rule(rule, zones.get(rule.zone), ordered, eave_depth_ft, observed, unfilmed)
        for rule in pack.rules
        if include_proposed or rule.status == "adopted"
    ]
    results.sort(key=_sort_key)
    return EngineResult(results=results, score=compute_score(results, unfilmed))
