"""Eave depth from corner clips (shot list #3: film along the wall at a corner so the roof
overhang shows in profile, with the scale marker on the ground).

The ground homography can't measure something above the ground, so this is a visual estimate:
Muse Spark reads the overhang against the marker's 1 in squares and the wall, from the sharpest
corner frames, and answers with a range. It is reported as an estimate (method "visual") and a
depth the owner types in always wins. The rules engine treats the range like any other: rules
whose strip depends on the eave become needs-review when the range straddles a limit.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import time
from pathlib import Path

import cv2
from PIL import Image
from pydantic import BaseModel

from .contracts import Range
from .geometry import detect_marker
from .media import extract_frames, normalize
from .media.keyframes import score
from .meta import MetaClient
from .spend import SpendLedger, token_cost

MODEL = os.environ.get("EAVE_MODEL", os.environ.get("AGENT_MODEL", "muse-spark-1.3-contributor"))
MAX_IMAGES = 8
IMAGE_WIDTH = 1024
EST_TOKENS = (6_000, 1_500)  # worst case per request, for the spend check
PLAUSIBLE_FT = (0.25, 6.0)

PROMPT = """These are frames from one or more corners of a building, in time order per corner,
filmed looking along a wall so the roof overhang (eave) shows in profile; the camera may tilt
from the ground up to the roofline. A printed checkerboard of exact 1 inch squares (6 x 8)
may lie flat on the ground against the wall base, for scale.
Estimate how far the eave sticks out horizontally from the wall face, in feet.
Reply with JSON only:
{"overhang": "yes"|"none"|"unclear", "min_ft": number, "max_ft": number,
 "confidence": "low"|"medium", "reason": "one short sentence on what you compared"}
"none": the roofline is clearly visible and the wall rises straight to it (flat roof, parapet,
no projecting eave). "unclear": the roofline is not visible well enough to tell.
For "yes", give an honest range (wider when unsure); if corners differ, cover all of them."""


class EaveEstimate(BaseModel):
    depth_ft: Range
    confidence: str  # "low" | "medium"
    reason: str
    method: str = "visual"
    overhang: str = "yes"  # "yes" | "none" (flat roof or parapet: no eave strip)
    frames: list[str] = []  # evidence images, relative to the scan dir
    model: str = MODEL


def _pick_frames(clip: Path, work: Path, n: int) -> list[Path]:
    """n sharp frames spread across the clip (the camera tilts from the marker up to the roof),
    with the first one swapped for a marker frame when the marker is visible, for scale."""
    normalize(clip, work / "corner.mp4", 720)
    frames = extract_frames(work / "corner.mp4", work / "frames", fps=2.0)
    if not frames:
        return []
    scored = score(frames)
    n = max(1, min(n, len(scored)))
    size = len(scored) / n
    picks = [
        max(
            scored[int(i * size) : max(int((i + 1) * size), int(i * size) + 1)],
            key=lambda s: s.sharpness,
        ).frame.path
        for i in range(n)
    ]
    if n > 1:
        for s in sorted(scored[: len(scored) // 2], key=lambda s: s.sharpness, reverse=True)[:6]:
            img = cv2.imread(str(s.frame.path))
            if img is not None and detect_marker(img) is not None:
                picks[0] = s.frame.path
                break
    return picks


def _data_url(path: Path) -> str:
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > IMAGE_WIDTH:
            im = im.resize((IMAGE_WIDTH, round(im.height * IMAGE_WIDTH / im.width)))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def parse_answer(text: str) -> EaveEstimate | None:
    """Pull the JSON object out of the model's reply and sanity-check it."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        overhang = d.get("overhang", "yes" if d.get("visible") else "unclear")
        if overhang == "none":
            return EaveEstimate(
                depth_ft=Range(min=0.0, max=0.0),
                confidence="medium",
                reason=str(d.get("reason", ""))[:200]
                or "No roof overhang: walls rise to the roofline.",
                overhang="none",
            )
        if overhang != "yes":
            return None
        lo, hi = sorted((float(d["min_ft"]), float(d["max_ft"])))
    except (ValueError, KeyError, TypeError):
        return None
    lo, hi = max(lo, PLAUSIBLE_FT[0]), min(hi, PLAUSIBLE_FT[1])
    if hi < lo:
        return None
    conf = "medium" if d.get("confidence") == "medium" and hi - lo <= 1.0 else "low"
    return EaveEstimate(
        depth_ft=Range(min=round(lo, 2), max=round(hi, 2)),
        confidence=conf,
        reason=str(d.get("reason", ""))[:200],
    )


def _output_text(resp: dict) -> str:
    parts = []
    for item in resp.get("output", []):
        for c in item.get("content", []) or []:
            if c.get("type") in ("output_text", "text"):
                parts.append(c.get("text", ""))
    return "".join(parts) or str(resp.get("output_text", ""))


async def estimate_eave(
    client: MetaClient, ledger: SpendLedger, corners: list[Path], scan_dir: Path
) -> EaveEstimate | None:
    """Estimate eave depth from corner clips; None when it can't be seen."""
    per_clip = max(2, MAX_IMAGES // max(len(corners), 1))  # ground + roofline
    picked: list[Path] = []
    for i, clip in enumerate(corners[:MAX_IMAGES]):
        work = scan_dir / "corners" / f"c{i}"
        picked += await asyncio.to_thread(_pick_frames, clip, work, per_clip)
    if not picked:
        return None
    content: list[dict] = [{"type": "input_text", "text": PROMPT}]
    content += [{"type": "input_image", "image_url": _data_url(p)} for p in picked]
    ledger.check("eave", token_cost(MODEL, *EST_TOKENS))
    t0 = time.monotonic()
    resp = await client.create_response(
        {
            "model": MODEL,
            "input": [{"role": "user", "content": content}],
            "reasoning": {"effort": "low"},
            "max_output_tokens": 1500,
        }
    )
    usage = resp.get("usage") or {}
    ledger.record(
        "eave",
        MODEL,
        token_cost(MODEL, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))),
        {k: usage.get(k, 0) for k in ("input_tokens", "output_tokens")},
        time.monotonic() - t0,
    )
    est = parse_answer(_output_text(resp))
    if est is not None:
        est.frames = [p.relative_to(scan_dir).as_posix() for p in picked]
    return est
