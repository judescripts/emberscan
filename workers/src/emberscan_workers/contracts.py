"""Shared data contracts between pipeline stages and the web app.

Every stage reads and writes these models; the web app consumes `Report` as JSON
(see docs/contracts/report.sample.json). Change them deliberately: they're the seams.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["N", "E", "S", "W", "roof", "unknown"]
Confidence = Literal["high", "medium", "low"]
Method = Literal["marker", "tape", "door", "depth", "visual"]
RuleStatus = Literal["pass", "fail", "needs-review"]
RulePackStatus = Literal["adopted", "proposed", "guidance"]


class Range(BaseModel):
    """A measured quantity with honest uncertainty: never a single number."""

    min: float
    max: float

    @property
    def mid(self) -> float:
        return (self.min + self.max) / 2


class BBox(BaseModel):
    """Pixel box in the normalized video's frame (left, top, right, bottom)."""

    left: float
    top: float
    right: float
    bottom: float


class Evidence(BaseModel):
    frame_index: int
    timestamp_ms: int
    bbox: BBox
    image_path: str | None = None  # annotated frame (mask + ruler), relative to the scan dir


class Hazard(BaseModel):
    id: str  # stable per scan, e.g. "h-wood_mulch-0"
    cls: str  # hazard class from docs/hazard-taxonomy.md
    concept: str  # SAM text prompt that found it
    track_id: str  # SAM object id within that concept's response
    label: str  # short human description
    frames: list[int]  # frames (in the SAM video) where it was tracked
    confidence: Confidence
    sam_confidence: float | None = None
    method: Method = "visual"
    distance_ft: Range | None = None  # from the wall line, along the ground
    clearance_ft: Range | None = None  # to a reference (chimney, window, ...)
    clearance_to: str | None = None
    height_in: Range | None = None
    zone: str | None = None  # "Z0" | "Z1" | "Z2" | None (unknown)
    zone_uncertain: bool = False  # range straddles a zone boundary
    side: Side = "unknown"
    narration: str | None = None  # transcript snippet near this hazard
    evidence: list[Evidence] = Field(default_factory=list)


class RuleResult(BaseModel):
    rule_id: str
    title: str
    zone: str
    rule_status: RulePackStatus  # adopted / proposed / guidance (from the pack)
    status: RuleStatus  # engine result
    reason: str  # plain-language why
    hazard_ids: list[str] = Field(default_factory=list)
    citation_url: str
    citation_label: str


class Illustration(BaseModel):
    """An AI-edited picture of what a fix would look like. Not a measurement."""

    before_path: str  # the clean video frame, relative to the scan folder
    after_path: str  # the same frame edited by Muse Image
    hazard_id: str
    frame_index: int
    model: str
    prompt: str
    checked: bool = False  # Muse Spark compared the pair and saw the fix
    check_reason: str = ""


class Fix(BaseModel):
    id: str
    title: str
    why: str
    rule_ids: list[str]
    hazard_ids: list[str]
    required: bool  # backs a failed adopted rule
    effort: Literal["S", "M", "L"]
    cost_band: Literal["free", "$", "$$", "$$$"]
    owner: Literal["HOA", "Owner", "Unclear"]
    priority: int
    illustration: Illustration | None = None  # Muse Image "after" picture; never evidence


class AgentStep(BaseModel):
    # privacy: the guard that blurs people and plates before anything is kept;
    # illustrate: Muse Image after pictures of the top fixes.
    kind: Literal[
        "privacy", "plan", "tool_call", "tool_result", "verify", "output", "illustrate", "note"
    ]
    summary: str
    detail: dict | None = None


class ScoreBlock(BaseModel):
    score: int
    label: str
    fails: int
    reviews: int
    passes: int
    zone0_met: int
    zone0_total: int
    unfilmed_sides: list[str] = Field(default_factory=list)


class Report(BaseModel):
    version: Literal["1"] = "1"
    scan_id: str
    building_label: str
    created_at: str
    pack_id: str
    pack_version: str
    include_proposed: bool = True
    video: dict  # {duration_s, fps, width, height, sam_fps}
    eave_depth_ft: Range | None = None
    # "entered" (typed by the owner, always wins) or "corner_video" (Muse Spark estimate).
    eave_source: Literal["entered", "corner_video"] | None = None
    eave_estimate: dict | None = None  # {confidence, reason, frames, model} for corner_video
    hazards: list[Hazard]
    results: list[RuleResult]
    score: ScoreBlock
    fixes: list[Fix]
    agent_trace: list[AgentStep] = Field(default_factory=list)
    # {model, provider ("baseten" | "meta"), label, seconds}; None = rule-based fallback plan
    agent_model: dict | None = None
    # {people, plates, frames_blurred, regions_blurred, raw_deleted, checked, summary, model}
    privacy: dict | None = None
    cost: dict = Field(default_factory=dict)  # spend ledger summary
    disclaimer: str = (
        "EmberScan flags likely wildfire hazards and suggests fixes based on published "
        "defensible space rules. It is not an inspection and does not certify that any "
        "property is safe or compliant. Confirm requirements with your local fire authority."
    )
