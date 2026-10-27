""" "After" pictures of the top fixes with Muse Image (story E8).

For each of the first few fixes, take the clean video frame behind its closest measured hazard
and ask Muse Image to edit only what the fix changes ("remove the dry leaves along the wall;
keep everything else identical"). The result is an illustration, never evidence: the report
labels it as AI-made, it is never measured, and it is shown next to the fix, not the findings.
Muse Spark then compares each before/after pair and drops pictures where the fix isn't visible
(an inspection fix, or a hazard at the edge of the frame), so "After the fix" never shows the
same picture twice. A failed or skipped picture never fails the scan.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .contracts import Fix, Hazard, Illustration
from .meta.client import MetaClient
from .spend import SpendLedger, SpendLimitExceeded, image_cost, token_cost

log = logging.getLogger(__name__)

CHECK_IMAGE_WIDTH = 1024  # frames sent to Muse Spark for the check are downsized to this


def _data_url(path: Path) -> str:
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > CHECK_IMAGE_WIDTH:
            h = round(im.height * CHECK_IMAGE_WIDTH / im.width)
            im = im.resize((CHECK_IMAGE_WIDTH, h))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _output_text(resp: dict) -> str:
    parts = []
    for item in resp.get("output", []):
        for c in item.get("content", []) or []:
            if c.get("type") in ("output_text", "text"):
                parts.append(c.get("text", ""))
    return "".join(parts) or str(resp.get("output_text", ""))


MODEL = "muse-image-1.0"
MAX_PICTURES = int(os.environ.get("AFTER_IMAGES", "3"))  # 0 turns the feature off
CHECK_MODEL = os.environ.get("AGENT_MODEL", "muse-spark-1.3-contributor")
CHECK_TOKENS = (4_000, 800)  # worst case per check, for the spend check
# A hazard box this share of the frame or more counts as clearly in view. A smaller one (a sliver
# at the edge) loses to a bigger one, even if that one is a little farther from the wall.
VISIBLE_AREA = 0.04

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

CHECK_PROMPT = (
    "The first photo is a real video frame. The second is the same frame edited by an image "
    "model to show this change: {edits}. It illustrates this fix from a wildfire-safety plan: "
    '"{title}". Answer true only if the change is visible (a small change counts) AND the '
    "second photo is a fair picture of what this fix would do (an inspection, check or trim "
    "fix is not fairly shown by removing the plants). Reply with JSON only: "
    '{{"visible": true or false, "reason": "<one short sentence>"}}'
)

PROMPT = (
    "Edit this exact photo to show one wildfire-safety fix: {edits}. Keep everything else "
    "identical: the same building, wall, windows, other plants, ground, lighting, camera angle "
    "and framing, and the printed checkerboard sheet on the ground. Do not add people, text, "
    "logos or anything new."
)


def pick_hazard(
    fix: Fix, hazards: dict[str, Hazard], frame_area: float | None = None
) -> Hazard | None:
    """The fix's hazard to picture: one clearly in view, then the closest measured one."""
    own = [hazards[h] for h in fix.hazard_ids if h in hazards and hazards[h].evidence]
    own = [h for h in own if h.cls in EDITS]
    if not own:
        return None

    def in_view(h: Hazard) -> float:
        if not frame_area:
            return 0.0
        b = h.evidence[0].bbox
        return min((b.right - b.left) * (b.bottom - b.top) / frame_area, VISIBLE_AREA)

    far = float("inf")
    return min(own, key=lambda h: (-in_view(h), h.distance_ft.min if h.distance_ft else far))


def edit_list(fix: Fix, hazards: dict[str, Hazard]) -> str:
    classes = dict.fromkeys(hazards[h].cls for h in fix.hazard_ids if h in hazards)
    return "; ".join(EDITS[c] for c in classes if c in EDITS)


def edit_prompt(fix: Fix, hazards: dict[str, Hazard]) -> str:
    return PROMPT.format(edits=edit_list(fix, hazards))


async def check_edit(
    client: MetaClient, ledger: SpendLedger, before: Path, after: Path, edits: str, title: str
) -> tuple[bool | None, str]:
    """Muse Spark compares the pair: (visible, reason), or (None, "") when it couldn't say."""
    try:
        ledger.check("after_check", token_cost(CHECK_MODEL, *CHECK_TOKENS))
        t0 = time.monotonic()
        resp = await client.create_response(
            {
                "model": CHECK_MODEL,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": CHECK_PROMPT.format(edits=edits, title=title),
                            },
                            {"type": "input_image", "image_url": _data_url(before)},
                            {"type": "input_image", "image_url": _data_url(after)},
                        ],
                    }
                ],
                "reasoning": {"effort": "low"},
                "max_output_tokens": 800,
            }
        )
    except Exception:  # an unchecked picture is kept, not dropped
        log.exception("after picture check failed")
        return None, ""
    usage = resp.get("usage") or {}
    tokens = (int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))
    ledger.record(
        "after_check",
        CHECK_MODEL,
        token_cost(CHECK_MODEL, *tokens),
        {"input_tokens": tokens[0], "output_tokens": tokens[1]},
        time.monotonic() - t0,
    )
    text = _output_text(resp)
    try:
        d = json.loads(text[text.index("{") : text.rindex("}") + 1])
        return bool(d["visible"]), str(d.get("reason", ""))[:200]
    except (ValueError, KeyError, TypeError):
        return None, ""


def clean_frame(scan_dir: Path, frame_index: int) -> Path:
    """The unannotated frame the evidence image was drawn on (frames/ is 1-based)."""
    return scan_dir / "frames" / f"frame_{frame_index + 1:06d}.jpg"


async def _one(
    client: MetaClient,
    ledger: SpendLedger,
    fix: Fix,
    hazards: dict[str, Hazard],
    scan_dir: Path,
    frame_area: float | None = None,
) -> Illustration | None:
    hazard = pick_hazard(fix, hazards, frame_area)
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
    visible, reason = await check_edit(
        client,
        ledger,
        out / f"{fix.id}-before.jpg",
        out / f"{fix.id}.jpg",
        edit_list(fix, hazards),
        fix.title,
    )
    if visible is False:
        log.info("after picture for %s dropped: %s", fix.id, reason)
        for name in (f"{fix.id}-before.jpg", f"{fix.id}.jpg"):
            (out / name).unlink(missing_ok=True)
        return None
    return Illustration(
        before_path=f"after/{fix.id}-before.jpg",
        after_path=f"after/{fix.id}.jpg",
        hazard_id=hazard.id,
        frame_index=frame,
        model=MODEL,
        prompt=prompt,
        checked=visible is True,
        check_reason=reason,
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
    first = next(iter(sorted((scan_dir / "frames").glob("frame_*.jpg"))), None)
    img = cv2.imread(str(first)) if first else None
    area = float(img.shape[0] * img.shape[1]) if img is not None else None
    chosen = [f for f in fixes if pick_hazard(f, by_id) is not None][: max(limit, 0)]
    pictures = await asyncio.gather(
        *(_one(client, ledger, f, by_id, scan_dir, area) for f in chosen)
    )
    for fix, pic in zip(chosen, pictures, strict=True):
        fix.illustration = pic
    return sum(p is not None for p in pictures)
