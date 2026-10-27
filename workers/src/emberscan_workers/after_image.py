""" "After" pictures of the top fixes with Muse Image (story E8).

For each of the first few fixes, take the clean video frame behind its closest measured hazard
and ask Muse Image to edit only what the fix changes ("remove the dry leaves along the wall;
keep everything else identical"). The result is an illustration, never evidence: the report
labels it as AI-made, it is never measured, and it is shown next to the fix, not the findings.
A failed or skipped picture never fails the scan.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from pathlib import Path

import cv2
import numpy as np

from .contracts import Fix, Hazard, Illustration
from .meta.client import MetaClient
from .spend import SpendLedger, SpendLimitExceeded, image_cost

log = logging.getLogger(__name__)

MODEL = "muse-image-1.0"
MAX_PICTURES = int(os.environ.get("AFTER_IMAGES", "3"))  # 0 turns the feature off

# What each fix changes in the picture, by hazard class. Classes not listed get no picture.
EDITS = {
    "leaf_litter": "remove the dry leaves, pine needles and plant debris lying on the ground "
    "near the wall, leaving clean bare ground",
    "wood_mulch": "replace the bark or wood mulch near the wall with plain gray gravel",
    "shrub": "remove the shrubs growing right against the wall, leaving bare ground next to "
    "the wall; keep plants that are farther from the wall",
    "dead_vegetation": "remove the dead and brown plants",
    "woodpile": "remove the stacked firewood next to the wall",
    "combustible_fence": "replace the wooden fence section closest to the building with a "
    "metal fence section of the same height",
    "grass_tall": "mow the tall dry grass down to short green grass",
    "tree_branch": "trim back the tree branches near the roof so there is clear space above it",
    "combustible_furniture": "remove the outdoor cushions and furniture near the wall",
    "propane_tank": "clear the plants and debris around the propane tank, leaving bare ground",
    "open_vent": "cover the vent opening with fine metal mesh",
    "gutter_debris": "clear the leaves and debris out of the rain gutter",
    "potted_plant": "remove the potted plants next to the wall",
    "roof_debris": "clear the leaves and debris off the roof",
}

PROMPT = (
    "Edit this exact photo to show one wildfire-safety fix: {edits}. Keep everything else "
    "identical: the same building, wall, windows, other plants, ground, lighting, camera angle "
    "and framing, and the printed checkerboard sheet on the ground. Do not add people, text, "
    "logos or anything new."
)


def pick_hazard(fix: Fix, hazards: dict[str, Hazard]) -> Hazard | None:
    """The fix's hazard to picture: the closest measured one with a frame, else any with one."""
    own = [hazards[h] for h in fix.hazard_ids if h in hazards and hazards[h].evidence]
    own = [h for h in own if h.cls in EDITS]
    if not own:
        return None
    measured = [h for h in own if h.distance_ft is not None]
    return min(measured, key=lambda h: h.distance_ft.min) if measured else own[0]


def edit_prompt(fix: Fix, hazards: dict[str, Hazard]) -> str:
    classes = dict.fromkeys(hazards[h].cls for h in fix.hazard_ids if h in hazards)
    edits = [EDITS[c] for c in classes if c in EDITS]
    return PROMPT.format(edits="; ".join(edits))


def clean_frame(scan_dir: Path, frame_index: int) -> Path:
    """The unannotated frame the evidence image was drawn on (frames/ is 1-based)."""
    return scan_dir / "frames" / f"frame_{frame_index + 1:06d}.jpg"


async def _one(
    client: MetaClient, ledger: SpendLedger, fix: Fix, hazards: dict[str, Hazard], scan_dir: Path
) -> Illustration | None:
    hazard = pick_hazard(fix, hazards)
    if hazard is None:
        return None
    frame = hazard.evidence[0].frame_index
    src = clean_frame(scan_dir, frame)
    if not src.is_file():
        return None
    prompt = edit_prompt(fix, hazards)
    try:
        ledger.check("after_image", image_cost(1))
    except SpendLimitExceeded:
        log.info("after picture for %s skipped: spend limit", fix.id)
        return None
    t0 = time.monotonic()
    try:
        data = await client.edit_image(
            {
                "model": MODEL,
                "prompt": prompt,
                "images": [
                    {
                        "image_url": "data:image/jpeg;base64,"
                        + base64.b64encode(src.read_bytes()).decode()
                    }
                ],
                "n": 1,
                "response_format": "b64_json",
                "output_format": "jpeg",
                # "low" dropped the marker and left the shrub on a real frame; "high" kept the
                # rest of the frame and made the edit, same price and about the same time.
                "reasoning_strength": "high",
            }
        )
        raw = base64.b64decode(data["data"][0]["b64_json"])
    except Exception:  # never fail a scan over a picture
        log.exception("after picture for %s failed", fix.id)
        return None
    ledger.record("after_image", MODEL, image_cost(1), {"images": 1}, time.monotonic() - t0)

    before = cv2.imread(str(src))
    after = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if before is None or after is None:
        return None
    h, w = before.shape[:2]
    if after.shape[:2] != (h, w):  # Muse Image keeps the aspect ratio, not the size
        after = cv2.resize(after, (w, h), interpolation=cv2.INTER_AREA)
    out = scan_dir / "after"
    out.mkdir(exist_ok=True)
    cv2.imwrite(str(out / f"{fix.id}-before.jpg"), before, [cv2.IMWRITE_JPEG_QUALITY, 85])
    cv2.imwrite(str(out / f"{fix.id}.jpg"), after, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Illustration(
        before_path=f"after/{fix.id}-before.jpg",
        after_path=f"after/{fix.id}.jpg",
        hazard_id=hazard.id,
        frame_index=frame,
        model=MODEL,
        prompt=prompt,
    )


async def illustrate_fixes(
    client: MetaClient,
    ledger: SpendLedger,
    fixes: list[Fix],
    hazards: list[Hazard],
    scan_dir: Path,
    limit: int = MAX_PICTURES,
) -> int:
    """Attach an after picture to up to `limit` fixes, in priority order (in place).
    Returns how many were made."""
    by_id = {h.id: h for h in hazards}
    chosen = [f for f in fixes if pick_hazard(f, by_id) is not None][: max(limit, 0)]
    pictures = await asyncio.gather(*(_one(client, ledger, f, by_id, scan_dir) for f in chosen))
    for fix, pic in zip(chosen, pictures, strict=True):
        fix.illustration = pic
    return sum(p is not None for p in pictures)
