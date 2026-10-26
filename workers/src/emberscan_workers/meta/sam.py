"""SAM 3.1 video segmentation and tracking (story C1).

One request per text concept over the whole (low-fps) clip. SAM returns per-frame boxes
and masks with object IDs that are stable within the response, which is what turns a
walkaround into a complete, tracked hazard inventory.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..spend import SpendLedger, sam_video_cost
from ..spend.pricing import SAM_USD_PER_1K_FRAMES
from .client import MetaClient

MODEL = "sam-3.1"

# Meta's official parser, run in Node: the pure-Python build decodes the arithmetic-coded
# masks ~70x slower (46 s vs 0.7 s for a 24-frame clip), too slow for full walkarounds.
SAM_PARSER = Path(
    os.environ.get("SAM_PARSER_PATH")
    or Path(__file__).resolve().parents[3] / "sam-parser" / "index.mjs"
)


class SamParseError(RuntimeError):
    pass


@dataclass(frozen=True)
class Box:
    left: float
    top: float
    right: float
    bottom: float
    confidence: float | None


@dataclass
class Track:
    """One object followed across the video."""

    object_id: str
    concept: str
    boxes: dict[int, Box] = field(default_factory=dict)  # frame index -> box
    # frame index -> {"rle": COCO RLE of a box-local mask, "bounds": [left, top, right, bottom]}.
    # SAM masks cover only the object's box, at lower resolution: scale the mask to the box
    # size and place it at (left, top) to get frame pixels.
    masks: dict[int, dict[str, Any]] = field(default_factory=dict)

    @property
    def frames(self) -> list[int]:
        return sorted(set(self.boxes) | set(self.masks))

    @property
    def mean_confidence(self) -> float | None:
        cs = [b.confidence for b in self.boxes.values() if b.confidence is not None]
        return sum(cs) / len(cs) if cs else None


@dataclass
class SegmentationResult:
    concept: str
    tracks: dict[str, Track]
    frames_billed: int
    cost_usd: float
    latency_s: float
    complete: bool


def build_request(concept: str, file_id: str, include_confidence: bool = True) -> dict[str, Any]:
    if not concept.strip():
        raise ValueError("concept must be a short noun phrase")
    metadata = {"mask_encoding": "one_bit"}
    if include_confidence:
        metadata["include_confidence"] = "true"
    return {
        "model": MODEL,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": concept.strip()},
                    {"type": "input_video", "file_id": file_id},
                ],
            }
        ],
        "metadata": metadata,
    }


async def parse_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the Node SAM parser on a complete event list; returns its JSON output."""
    node = shutil.which("node")
    if not node:
        raise SamParseError("node not found on PATH (needed for the SAM parser)")
    if not SAM_PARSER.exists():
        raise SamParseError(f"SAM parser not found at {SAM_PARSER}; run npm ci in sam-parser")
    proc = await asyncio.create_subprocess_exec(
        node,
        str(SAM_PARSER),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(json.dumps(events).encode())
    if proc.returncode != 0:
        raise SamParseError(err.decode(errors="replace")[-800:])
    return json.loads(out)


async def collect_tracks(
    events: AsyncIterator[dict[str, Any]], concept: str
) -> tuple[dict[str, Track], bool]:
    """Collect a SAM Responses event stream and parse it into tracks keyed by object id."""
    parsed = await parse_events([e async for e in events])
    tracks: dict[str, Track] = {}
    for object_id, raw in parsed["tracks"].items():
        t = Track(object_id, concept)
        for frame, (left, top, right, bottom, conf) in raw["boxes"].items():
            t.boxes[int(frame)] = Box(left, top, right, bottom, conf)
        for frame, mask in raw["masks"].items():
            t.masks[int(frame)] = mask
        tracks[object_id] = t
    return tracks, bool(parsed["complete"])


async def segment_video(
    client: MetaClient,
    ledger: SpendLedger,
    video: Path,
    concept: str,
    frame_count: int,
    file_id: str | None = None,
) -> SegmentationResult:
    """Segment and track one concept across a normalized video.

    Checks the spend limit before calling (worst case = frame_count, min 50 billed).
    Pass `file_id` to reuse an upload across concepts.
    """
    estimate = sam_video_cost(frame_count)
    ledger.check(f"sam:{concept}", estimate)
    fid = file_id or await client.upload_file(video)
    usage: dict[str, Any] = {}

    async def tap() -> AsyncIterator[dict[str, Any]]:
        async for event in client.stream_response(build_request(concept, fid)):
            if event.get("type") == "response.completed":
                usage.update((event.get("response") or {}).get("usage") or {})
            yield event

    t0 = time.monotonic()
    try:
        tracks, complete = await collect_tracks(tap(), concept)
    finally:
        if file_id is None:
            await client.delete_file(fid)
    latency = time.monotonic() - t0
    # The API reports billed frames (minimum 50 per request); fall back to our estimate.
    billed = int(usage.get("video_frames_processed") or max(frame_count, 50))
    cost = billed * SAM_USD_PER_1K_FRAMES / 1000
    ledger.record(f"sam:{concept}", MODEL, cost, {"frames": billed}, latency)
    return SegmentationResult(concept, tracks, billed, cost, latency, complete)
