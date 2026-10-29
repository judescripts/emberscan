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
    aggregate,
    assign_zone,
    contact_mode_for,
    detect_marker,
    estimate_focal_px,
    mask_to_frame,
    measure_track,
    scale_pose,
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
MAX_RANGE_FT = 6.0  # wider measured ranges are treated as not measured
# Frames whose contact point is farther than this from the marker extrapolate the ground plane
# too far to trust. When some frames are near, only those count; when none are, not measured.
NEAR_MARKER_FT = 10.0


def trusted(m: DistanceMeasurement | None) -> tuple[DistanceMeasurement | None, str]:
    """Keep a measurement only if it's worth showing: (measurement, "") or (None, why not)."""
    if m is None:
        return None, "no marker in view"
    near = [f for f in m.per_frame if f.marker_dist_ft <= NEAR_MARKER_FT]
    if not near:
        return None, "too far from the marker"
    if len(near) < len(m.per_frame):
        m = aggregate(near)
    if m is None or m.distance_ft.max - m.distance_ft.min > MAX_RANGE_FT:
        return None, "frames disagree; base hidden or marker too far"
    return m, ""


def _detect_all(
    frames: list[Path], hires: list[Path] | None = None
) -> dict[int, MarkerPose | None]:
    """Find the marker in every frame. When full-resolution copies of the same frames are given,
    detect there (a small, slanted marker needs the pixels) and scale the pose down to the
    frame size SAM's masks use."""
    use_hi = hires is not None and len(hires) == len(frames)
    k = 1.0
    if use_hi:
        lo, hi = cv2.imread(str(frames[0])), cv2.imread(str(hires[0]))
        k = lo.shape[1] / hi.shape[1] if lo is not None and hi is not None else 1.0
    poses: dict[int, MarkerPose | None] = {}
    for i, path in enumerate(hires if use_hi else frames):
        img = cv2.imread(str(path))
        pose = detect_marker(img) if img is not None else None
        poses[i] = scale_pose(pose, k) if pose is not None and k != 1.0 else pose
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
    track: Track | list[Track],
    frame: int,
    pose: MarkerPose | None,
    label: str,
) -> bool:
    img = cv2.imread(str(frame_path))
    if img is None:
        return False
    h, w = img.shape[:2]
    tracks = track if isinstance(track, list) else [track]
    mask = np.zeros((h, w), bool)
    for t in tracks:
        mask_dict = t.masks.get(frame)
        if not mask_dict:
            continue
        try:
            mask |= mask_to_frame(mask_dict, w, h)
        except Exception:  # a bad mask shouldn't lose the evidence frame
            log.debug("mask overlay failed for %s frame %s", t.object_id, frame)
    if mask.any():
        overlay = img.copy()
        overlay[mask] = MASK_BGR
        img = cv2.addWeighted(overlay, 0.45, img, 0.55, 0)
        contours, _ = cv2.findContours(
            mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(img, contours, -1, MASK_BGR, 2)
    if len(tracks) == 1 and (box := tracks[0].boxes.get(frame)) is not None:
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
    img = _caption_below(img, label)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(out_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85]))


def _caption_below(img: np.ndarray, text: str) -> np.ndarray:
    """Add the label in a strip under the frame, so it never covers what was captured."""
    w = img.shape[1]
    font, scale = cv2.FONT_HERSHEY_SIMPLEX, max(0.55, 0.75 * w / 1280)
    thick = 2 if scale >= 0.9 else 1
    lines, line = [], ""
    for word in text.split():  # wrap to the frame width
        trial = f"{line} {word}".strip()
        if line and cv2.getTextSize(trial, font, scale, thick)[0][0] > w - 24:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    th = cv2.getTextSize("Ag", font, scale, thick)[0][1]
    pad, gap = 12, 8
    strip = np.full(
        (pad * 2 + len(lines) * th + (len(lines) - 1) * gap, w, 3), (33, 36, 43), np.uint8
    )
    for i, ln in enumerate(lines):
        y = pad + th + i * (th + gap)
        cv2.putText(strip, ln, (12, y), font, scale, (255, 255, 255), thick, cv2.LINE_AA)
    return np.vstack([img, strip])


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
    poses = _detect_all(frames, job.marker_frames or None)
    seen = sum(1 for p in poses.values() if p is not None)
    log.info("marker found in %d/%d frames", seen, len(frames))
    bands = zone_bands([z.model_dump() for z in load_pack("us-ca").zones])

    for h in hazards:
        track = tracks.get(h.id)
        if track is None:
            continue
        m = None
        try:
            m = measure_track(track.masks, poses, contact_mode_for(h.cls))
        except Exception:  # never fail a scan over one track
            log.exception("measuring %s failed", h.id)
        m, why_not = trusted(m)
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
            label = f"{h.label}: not measured ({why_not})"
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
                    timestamp_ms=int(frame * 1000 / job.sam_fps),
                    bbox=bbox,
                    image_path=rel.as_posix(),
                )
            ]
    return merge_scattered(hazards, tracks, frames, poses, job)


# Ground litter comes back from SAM one leaf at a time: a bed of leaves is a dozen tracks, each
# with its own evidence picture of a single leaf. Litter seen together in the same stretch of
# video (tracks sharing a frame) is reported as one finding that outlines every piece.
SCATTERED_CLASSES = {"leaf_litter"}


def _groups(hs: list[Hazard]) -> list[list[Hazard]]:
    """Chain hazards whose frame spans overlap. Tracks split at a clip cut never share a frame,
    so a group stays within one clip."""
    out: list[list[Hazard]] = []
    end = -1
    for h in sorted(hs, key=lambda h: (min(h.frames), h.id)):
        if out and min(h.frames) <= end:
            out[-1].append(h)
            end = max(end, max(h.frames))
        else:
            out.append([h])
            end = max(h.frames)
    return out


def _merge(
    group: list[Hazard],
    tracks: dict[str, Track],
    frames: list[Path],
    poses: dict[int, MarkerPose | None],
    job: ScanJob,
) -> Hazard:
    measured = [h for h in group if h.distance_ft is not None]
    # The rules care about how close the litter comes to the wall: the nearest piece speaks.
    near = min(measured, key=lambda h: h.distance_ft.min) if measured else None  # type: ignore[union-attr]
    lead = near or max(group, key=lambda h: (_RANK[h.confidence], h.sam_confidence or 0))
    members = [tracks[h.id] for h in group if h.id in tracks]
    counts: dict[int, int] = {}
    for t in members:
        for f in t.masks:
            if f < len(frames):
                counts[f] = counts.get(f, 0) + 1
    lead_frame = lead.evidence[0].frame_index if lead.evidence else None
    frame = max(counts, key=lambda f: (counts[f], f == lead_frame), default=lead_frame)

    label = f"{lead.label} ({len(group)} spots)"
    merged = lead.model_copy(
        update={
            "label": label,
            "frames": sorted({f for h in group for f in h.frames}),
            "sam_confidence": max((h.sam_confidence or 0) for h in group) or None,
            "narration": None,
        }
    )
    if frame is None:
        return merged
    r = lead.distance_ft
    caption = (
        f"{label}: nearest {_ft(r.min, r.max)} ft from wall ({lead.confidence})"
        if r is not None
        else f"{label}: not measured"
    )
    rel = Path("evidence") / f"{merged.id}.jpg"
    if _render(frames[frame], job.dir / rel, members, frame, poses.get(frame), caption):
        boxes = [t.boxes[frame] for t in members if frame in t.boxes]
        bbox = (
            BBox(
                left=min(b.left for b in boxes),
                top=min(b.top for b in boxes),
                right=max(b.right for b in boxes),
                bottom=max(b.bottom for b in boxes),
            )
            if boxes
            else BBox(left=0, top=0, right=0, bottom=0)
        )
        merged.evidence = [
            Evidence(
                frame_index=frame,
                timestamp_ms=int(frame * 1000 / job.sam_fps),
                bbox=bbox,
                image_path=rel.as_posix(),
            )
        ]
    return merged


def merge_scattered(
    hazards: list[Hazard],
    tracks: dict[str, Track],
    frames: list[Path],
    poses: dict[int, MarkerPose | None],
    job: ScanJob,
) -> list[Hazard]:
    out = [h for h in hazards if h.cls not in SCATTERED_CLASSES or not h.frames]
    for cls in sorted(SCATTERED_CLASSES):
        for group in _groups([h for h in hazards if h.cls == cls and h.frames]):
            if len(group) == 1:
                out.extend(group)
                continue
            merged = _merge(group, tracks, frames, poses, job)
            for h in group:  # the single-leaf pictures are superseded by the merged one
                if h.id != merged.id and h.evidence and h.evidence[0].image_path:
                    (job.dir / h.evidence[0].image_path).unlink(missing_ok=True)
            out.append(merged)
    return out
