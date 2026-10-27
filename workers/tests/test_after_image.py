"""Muse Image after pictures: which hazard is pictured, the prompt, sizing, and failure safety."""

import asyncio
import base64
import json
from pathlib import Path

import cv2
import httpx
import numpy as np

from emberscan_workers.after_image import (
    edit_prompt,
    illustrate_fixes,
    pick_hazard,
    where_in_frame,
)
from emberscan_workers.contracts import BBox, Evidence, Fix, Hazard, Range
from emberscan_workers.meta import MetaClient
from emberscan_workers.spend import SpendLedger


def hazard(
    hid: str,
    cls: str,
    frame: int,
    dist: tuple[float, float] | None,
    box: tuple[float, float, float, float] = (0, 0, 1, 1),
) -> Hazard:
    return Hazard(
        id=hid,
        cls=cls,
        label=cls,
        concept=cls,
        track_id="1",
        frames=[frame],
        confidence="high",
        distance_ft=Range(min=dist[0], max=dist[1]) if dist else None,
        evidence=[
            Evidence(
                frame_index=frame,
                timestamp_ms=0,
                bbox=BBox(left=box[0], top=box[1], right=box[2], bottom=box[3]),
                image_path=f"evidence/{hid}.jpg",
            )
        ],
    )


def fix(fid: str, hazard_ids: list[str]) -> Fix:
    return Fix(
        id=fid,
        title="Clear it",
        why="Close to the wall.",
        rule_ids=["Z0-01"],
        hazard_ids=hazard_ids,
        required=True,
        effort="S",
        cost_band="$",
        owner="HOA",
        priority=1,
    )


HAZARDS = [
    hazard("h-leaf-far", "leaf_litter", 4, (3.0, 3.5)),
    hazard("h-leaf-near", "leaf_litter", 2, (1.0, 1.2)),
    hazard("h-mulch", "wood_mulch", 1, None),
]


def test_pictures_the_closest_measured_hazard_and_describes_only_the_fix() -> None:
    by_id = {h.id: h for h in HAZARDS}
    f = fix("f1", ["h-leaf-far", "h-leaf-near"])
    assert pick_hazard(f, by_id).id == "h-leaf-near"
    prompt = edit_prompt(f, by_id)
    assert "dry leaves" in prompt and "mulch" not in prompt and "identical" in prompt
    assert pick_hazard(fix("f2", ["h-unknown"]), by_id) is None


def test_prefers_a_hazard_in_view_over_a_sliver_that_is_closer() -> None:
    small = hazard("h-shrub-small", "shrub", 1, (0.5, 1.0), box=(10, 10, 15, 15))
    big = hazard("h-shrub-big", "shrub", 3, (1.5, 2.0), box=(5, 5, 30, 60))
    by_id = {h.id: h for h in (small, big)}
    f = fix("f1", [small.id, big.id])
    assert pick_hazard(f, by_id, size=(36, 64)).id == "h-shrub-big"
    assert pick_hazard(f, by_id).id == "h-shrub-small"  # no frame size: closest wins


def test_a_box_cut_off_by_the_frame_edge_loses_to_one_fully_in_view() -> None:
    edge = hazard("h-edge", "shrub", 1, (0.0, 0.8), box=(640, 595, 720, 1096))  # 8% of frame
    inside = hazard("h-inside", "shrub", 2, (0.0, 0.5), box=(200, 600, 420, 860))  # 6%
    by_id = {h.id: h for h in (edge, inside)}
    assert pick_hazard(fix("f1", ["h-edge", "h-inside"]), by_id, size=(720, 1280)).id == "h-inside"
    # every box cut off: the biggest one, not the first listed
    wide = hazard("h-wide", "shrub", 3, (0.0, 0.8), box=(0, 510, 318, 834))
    by_id = {h.id: h for h in (edge, wide)}
    assert pick_hazard(fix("f2", ["h-edge", "h-wide"]), by_id, size=(720, 1280)).id == "h-wide"


def test_prompt_says_where_the_hazard_is() -> None:
    h = hazard("h-right", "shrub", 1, (0.0, 0.5), box=(500, 900, 700, 1200))
    assert where_in_frame(h, (720, 1280)) == "on the right side, near the bottom"
    prompt = edit_prompt(fix("f1", ["h-right"]), {h.id: h}, h, (720, 1280))
    assert "Start with the shrub on the right side, near the bottom of the photo." in prompt


def _frames(tmp: Path) -> None:
    (tmp / "frames").mkdir()
    img = np.full((64, 36, 3), 120, np.uint8)
    for i in range(1, 6):
        cv2.imwrite(str(tmp / "frames" / f"frame_{i:06d}.jpg"), img)


def test_illustrate_writes_before_and_after_at_frame_size(tmp_path: Path) -> None:
    _frames(tmp_path)
    big = cv2.imencode(".jpg", np.full((128, 72, 3), 200, np.uint8))[1].tobytes()
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        if request.url.path.endswith("/responses"):
            return httpx.Response(200, json=_verdict(True))
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(big).decode()}]})

    fixes = [fix("f1", ["h-leaf-near"]), fix("f2", ["h-mulch"]), fix("f3", ["h-leaf-far"])]
    ledger = SpendLedger("t", 1.0)

    async def run():
        async with MetaClient(api_key="k", transport=httpx.MockTransport(handler)) as c:
            return await illustrate_fixes(c, ledger, fixes, HAZARDS, tmp_path, limit=2)

    assert asyncio.run(run()) == 2
    assert fixes[2].illustration is None  # over the limit
    ill = fixes[0].illustration
    assert ill and ill.hazard_id == "h-leaf-near" and ill.frame_index == 2
    after = cv2.imread(str(tmp_path / ill.after_path))
    assert after.shape[:2] == (64, 36)  # resized back to the frame
    assert (tmp_path / ill.before_path).is_file()
    edits = [b for b in sent if "images" in b]
    assert edits[0]["images"][0]["image_url"].startswith("data:image/jpeg;base64,")
    checks = [b for b in sent if "input" in b]
    assert len(checks) == 2 and len(checks[0]["input"][0]["content"]) == 3  # text + both images
    assert ill.checked
    assert round(ledger.spent_usd, 2) == 0.02


def _verdict(visible: bool) -> dict:
    text = json.dumps({"visible": visible, "reason": "same picture"})
    return {
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        "usage": {"input_tokens": 1500, "output_tokens": 60},
    }


def test_picture_without_a_visible_change_is_dropped(tmp_path: Path) -> None:
    _frames(tmp_path)
    same = cv2.imencode(".jpg", np.full((64, 36, 3), 120, np.uint8))[1].tobytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/responses"):
            return httpx.Response(200, json=_verdict(False))
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(same).decode()}]})

    fixes = [fix("f1", ["h-leaf-near"])]

    async def run():
        async with MetaClient(api_key="k", transport=httpx.MockTransport(handler)) as c:
            return await illustrate_fixes(c, SpendLedger("t", 1.0), fixes, HAZARDS, tmp_path)

    assert asyncio.run(run()) == 0
    assert fixes[0].illustration is None
    assert not list((tmp_path / "after").iterdir())  # both files removed


def test_failed_picture_never_fails_the_scan(tmp_path: Path) -> None:
    _frames(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "content_policy_violation"}})

    fixes = [fix("f1", ["h-leaf-near"])]

    async def run():
        async with MetaClient(api_key="k", transport=httpx.MockTransport(handler)) as c:
            return await illustrate_fixes(c, SpendLedger("t", 1.0), fixes, HAZARDS, tmp_path)

    assert asyncio.run(run()) == 0
    assert fixes[0].illustration is None
