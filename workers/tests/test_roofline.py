from emberscan_workers.meta.sam import Box, SegmentationResult, Track
from emberscan_workers.pipeline import hazards_from_tracks


def _result(prompt: str, top: float, bottom: float) -> SegmentationResult:
    boxes = {i: Box(left=100, top=top, right=160, bottom=bottom, confidence=0.9) for i in range(4)}
    t = Track(object_id="1", concept=prompt, boxes=boxes)
    return SegmentationResult(
        concept=prompt, tracks={"1": t}, frames_billed=4, cost_usd=0, latency_s=0, complete=True
    )


def test_gutter_debris_low_in_the_frame_is_a_leaf_on_the_ground() -> None:
    hs = hazards_from_tracks([_result("leaves in a rain gutter", 1150, 1220)], 2.0, 1280)
    assert hs == []


def test_gutter_debris_up_at_the_roofline_is_kept() -> None:
    hs = hazards_from_tracks([_result("leaves in a rain gutter", 90, 160)], 2.0, 1280)
    assert [h.cls for h in hs] == ["gutter_debris"]


def test_ground_classes_are_not_height_checked() -> None:
    hs = hazards_from_tracks([_result("dry leaves on the ground", 1150, 1220)], 2.0, 1280)
    assert [h.cls for h in hs] == ["leaf_litter"]
