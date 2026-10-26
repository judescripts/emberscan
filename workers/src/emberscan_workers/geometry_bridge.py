"""Connect the geometry package to the scan pipeline.

For each scan: detect the scale marker in every extracted frame, measure each hazard track's
distance from the wall line, assign a zone, and render one annotated evidence image per hazard
(mask overlay, wall line, distance label). Hazards the marker can't measure keep a visual
distance of None (method "visual") so the rules engine marks them needs-review instead
of guessing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from .contracts import BBox, Evidence, Hazard
from .geometry import (
    assign_zone,
    contact_mode_for,
    detect_marker,
    estimate_focal_px,
    mask_to_frame,
    measure_track,
    with_focal,
    zone_bands,
)
from .rules import load_pack

if TYPE_CHECKING:
    from .geometry import DistanceMeasurement, MarkerPose
    from .meta.sam import Track
    from .pipeline import ScanJob

log = logging.getLogger(__name__)

_RANK = {"low": 0, "medium": 1, "high": 2}
MASK_BGR = (30, 84, 217)  # ember, BGR
WALL_BGR = (255, 255, 255)


def _detect_all(frames: list[Path]) -> dict[int, MarkerPose | None]:
    poses: dict[int, MarkerPose | None] = {}
    for i, path in enumerate(frames):
        img = cv2.imread(str(path))
        poses[i] = detect_marker(img) if img is not None else None
    focal = estimate_focal_px(poses.values())
    if focal is not None:
        f, std = focal
        poses = {i: with_focal(p, f, std) if p is not None else None for i, p in poses.items()}
    return poses


def _min_conf(a: str, b: str) -> str:
    return a if _RANK[a] <= _RANK[b] else b


def _render(
    frame_path: Path,
    out_path: Path,
    track: Track,
    frame: int,
    pose: MarkerPose | None,
    label: str,
) -> bool:
    img = cv2.imread(str(frame_path))
    if img is None:
        return False
    h, w = img.shape[:2]
    mask_dict = track.masks.get(frame)
    if mask_dict:
        try:
            mask = mask_to_frame(mask_dict, w, h)
            overlay = img.copy()
            overlay[mask] = MASK_BGR
            img = cv2.addWeighted(overlay, 0.45, img, 0.55, 0)
            contours, _ = cv2.findContours(
                mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(img, contours, -1, MASK_BGR, 2)
        except Exception:  # a bad mask shouldn't lose the evidence frame
            log.debug("mask overlay failed for %s frame %s", track.object_id, frame)
    box = track.boxes.get(frame)
    if box is not None:
        cv2.rectangle(
            img, (int(box.left), int(box.top)), (int(box.right), int(box.bottom)), MASK_BGR, 1
        )
    if pose is not None:
        line = pose.wall_line_image().astype(int)
        cv2.line(img, tuple(line[0]), tuple(line[1]), WALL_BGR, 2, cv2.LINE_AA)
        cv2.polylines(
            img,
            [pose.corners_px.reshape(-1, 2)[[0, 4, 34, 30]].astype(int)],
            True,
            (80, 200, 120),
            1,
            cv2.LINE_AA,
        )
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(img, (8, 8), (20 + tw, 20 + th + 6), (33, 36, 43), -1)
    cv2.putText(
        img, label, (14, 14 + th), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(out_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85]))


def _clearest_frame(track: Track, frames: list[Path]) -> int:
    """Frame where the object is biggest and most confident, preferring it not cut off."""
    img = cv2.imread(str(frames[0]))
    h, w = img.shape[:2] if img is not None else (720, 1280)
    margin = 0.01 * max(w, h)

    def score(i: int) -> float:
        b = track.boxes[i]
        area = max(b.right - b.left, 0) * max(b.bottom - b.top, 0)
        clipped = b.left < margin or b.top < margin or b.right > w - margin or b.bottom > h - margin
        return area * (b.confidence or 0.5) * (0.4 if clipped else 1.0)

    return max((i for i in track.boxes if i < len(frames)), key=score, default=0)


def _ft(lo: float, hi: float) -> str:
    spec = ".1f" if hi - lo < 2 else ".0f"
    return f"{lo:{spec}}-{hi:{spec}}"


def _apply(h: Hazard, m: DistanceMeasurement, bands: list) -> None:
    h.distance_ft = m.distance_ft
    h.method = "marker"
    h.confidence = _min_conf(h.confidence, m.confidence)
    h.zone, h.zone_uncertain = assign_zone(m.distance_ft, bands)


def measure_hazards(
    hazards: list[Hazard], tracks: dict[str, Track], frames: list[Path], job: ScanJob
) -> list[Hazard]:
    """Measure, zone and render evidence for every hazard (in place; returns the list)."""
    if not frames:
        return hazards
    poses = _detect_all(frames)
    seen = sum(1 for p in poses.values() if p is not None)
    log.info("marker found in %d/%d frames", seen, len(frames))
    bands = zone_bands([z.model_dump() for z in load_pack("us-ca").zones])
    from .pipeline import SAM_FPS

    for h in hazards:
        track = tracks.get(h.id)
        if track is None:
            continue
        m = None
        try:
            m = measure_track(track.masks, poses, contact_mode_for(h.cls))
        except Exception:  # never fail a scan over one track
            log.exception("measuring %s failed", h.id)
        if m is not None:
            _apply(h, m, bands)
            frame = m.best_frame.frame_index
            r = m.distance_ft
            label = f"{h.label}: {_ft(r.min, r.max)} ft from wall ({m.confidence})"
        else:
            frame = (
                _clearest_frame(track, frames)
                if track.boxes
                else (h.evidence[0].frame_index if h.evidence else (h.frames[0] if h.frames else 0))
            )
            label = f"{h.label}: not measured (no marker in view)"
        if frame >= len(frames):
            continue
        rel = Path("evidence") / f"{h.id}.jpg"
        if _render(frames[frame], job.dir / rel, track, frame, poses.get(frame), label):
            box = track.boxes.get(frame)
            if box is not None:
                bbox = BBox(left=box.left, top=box.top, right=box.right, bottom=box.bottom)
            elif h.evidence:
                bbox = h.evidence[0].bbox
            else:
                bbox = BBox(left=0, top=0, right=0, bottom=0)
            h.evidence = [
                Evidence(
                    frame_index=frame,
                    timestamp_ms=int(frame * 1000 / SAM_FPS),
                    bbox=bbox,
                    image_path=rel.as_posix(),
                )
            ]
    return hazards
