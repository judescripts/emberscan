"""Muse Image after pictures: which hazard is pictured, the prompt, sizing, and failure safety."""

import asyncio
import base64
import json
from pathlib import Path

import cv2
import httpx
import numpy as np

from emberscan_workers.after_image import edit_prompt, illustrate_fixes, pick_hazard
from emberscan_workers.contracts import BBox, Evidence, Fix, Hazard, Range
from emberscan_workers.meta import MetaClient
from emberscan_workers.spend import SpendLedger


def hazard(hid: str, cls: str, frame: int, dist: tuple[float, float] | None) -> Hazard:
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
                bbox=BBox(left=0, top=0, right=1, bottom=1),
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
    assert sent[0]["images"][0]["image_url"].startswith("data:image/jpeg;base64,")
    assert ledger.spent_usd == 0.02


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
