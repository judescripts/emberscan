"""Privacy guard: no people or license plates in anything a scan keeps (official rule).

SAM 3.1 looks for "person" and "license plate" in the same video it already tracks hazards in.
Before evidence images or Muse Image "after" pictures are made, every box where one was seen
is blurred in the extracted frames (with a margin, and filled across short gaps in a track).
When the scan ends, the raw and intermediate videos and the corner frames are deleted, so only
blurred frames and the report stay on disk. This is code, not a model decision: the agent
can't skip it, and the report and the agent trace show what it did.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .hazards import Concept
from .meta.sam import Box, SegmentationResult, Track

log = logging.getLogger(__name__)

PRIVACY_CONCEPTS = [
    Concept("person", "person", "Person"),
    Concept("license_plate", "license plate", "License plate"),
]
PRIVACY_PROMPTS = {c.prompt: c.cls for c in PRIVACY_CONCEPTS}
MIN_CONFIDENCE = 0.2  # blur on weak detections too: a missed face costs more than a blurred bush
MARGIN = 0.15  # grow each box by this share of its size on every side
MAX_GAP_FRAMES = 6  # fill a track's missing frames up to this long with the nearer box
# Kept for local debugging only; the default deletes them when the scan ends.
KEEP_RAW_VIDEO = os.environ.get("KEEP_RAW_VIDEO", "0") == "1"
RAW_FILES = ("joined.mp4", "normalized.mp4", "sam.mp4", "marker.mp4", "audio.wav")


@dataclass
class PrivacyReport:
    people: int = 0
    plates: int = 0
    frames_blurred: int = 0
    regions_blurred: int = 0
    raw_deleted: list[str] = field(default_factory=list)
    checked: bool = False  # False when SAM couldn't run the privacy concepts

    def summary(self) -> str:
        if not self.checked:
            return "Couldn't check for people or plates; frames were not blurred."
        found = []
        if self.people:
            found.append(f"{self.people} {'person' if self.people == 1 else 'people'}")
        if self.plates:
            found.append(f"{self.plates} license plate{'s' if self.plates != 1 else ''}")
        if not found:
            return "No people or license plates seen."
        return f"Blurred {' and '.join(found)} in {self.frames_blurred} frames."

    def as_dict(self) -> dict:
        return {
            "people": self.people,
            "plates": self.plates,
            "frames_blurred": self.frames_blurred,
            "regions_blurred": self.regions_blurred,
            "raw_deleted": self.raw_deleted,
            "checked": self.checked,
            "summary": self.summary(),
            "model": "sam-3.1",
        }


def split_privacy(
    results: list[SegmentationResult],
) -> tuple[list[SegmentationResult], list[SegmentationResult]]:
    """(hazard results, privacy results)."""
    hazards = [r for r in results if r.concept not in PRIVACY_PROMPTS]
    private = [r for r in results if r.concept in PRIVACY_PROMPTS]
    return hazards, private


def track_boxes(track: Track, max_gap: int = MAX_GAP_FRAMES) -> dict[int, Box]:
    """A track's box per frame, with short gaps filled by the nearer known box."""
    known = dict(track.boxes)
    if not known:
        return {}
    frames = sorted(known)
    out = dict(known)
    for a, b in zip(frames, frames[1:], strict=False):
        if 1 < b - a <= max_gap + 1:
            for f in range(a + 1, b):
                out[f] = known[a] if f - a <= b - f else known[b]
    return out


def regions_by_frame(private: list[SegmentationResult]) -> tuple[dict[int, list[Box]], int, int]:
    """frame -> boxes to blur, plus how many people and plates were seen."""
    regions: dict[int, list[Box]] = {}
    counts = {"person": 0, "license_plate": 0}
    for res in private:
        cls = PRIVACY_PROMPTS[res.concept]
        for t in res.tracks.values():
            if (t.mean_confidence or 0) < MIN_CONFIDENCE and len(t.frames) < 2:
                continue
            counts[cls] += 1
            for f, box in track_boxes(t).items():
                regions.setdefault(f, []).append(box)
    return regions, counts["person"], counts["license_plate"]


def blur_boxes(img: np.ndarray, boxes: list[Box], scale: float = 1.0) -> int:
    """Blur each box (grown by MARGIN, scaled to this image) in place. Returns how many."""
    h, w = img.shape[:2]
    n = 0
    for b in boxes:
        bw, bh = (b.right - b.left) * scale, (b.bottom - b.top) * scale
        x0 = int(max(0, b.left * scale - MARGIN * bw))
        y0 = int(max(0, b.top * scale - MARGIN * bh))
        x1 = int(min(w, b.right * scale + MARGIN * bw))
        y1 = int(min(h, b.bottom * scale + MARGIN * bh))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        roi = img[y0:y1, x0:x1]
        # Pixelate, then blur: nothing recognizable survives, and it reads as redacted.
        small = cv2.resize(roi, (max(1, (x1 - x0) // 12), max(1, (y1 - y0) // 12)))
        roi[:] = cv2.GaussianBlur(
            cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST), (0, 0), 6
        )
        n += 1
    return n


def blur_frames(
    regions: dict[int, list[Box]], frames: list[Path], hi_frames: list[Path] | None = None
) -> tuple[int, int]:
    """Blur the regions in the SAM-resolution frames and their full-resolution twins, in place.
    Frame index i is frames[i]. Returns (frames changed, regions blurred)."""
    changed = blurred = 0
    for f, boxes in regions.items():
        if f >= len(frames):
            continue
        img = cv2.imread(str(frames[f]))
        if img is None:
            continue
        k = blur_boxes(img, boxes)
        if not k:
            continue
        cv2.imwrite(str(frames[f]), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        changed += 1
        blurred += k
        if hi_frames and f < len(hi_frames):
            hi = cv2.imread(str(hi_frames[f]))
            if hi is not None:
                blur_boxes(hi, boxes, scale=hi.shape[1] / img.shape[1])
                cv2.imwrite(str(hi_frames[f]), hi, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return changed, blurred


def guard_frames(
    private: list[SegmentationResult], frames: list[Path], hi_frames: list[Path] | None = None
) -> PrivacyReport:
    regions, people, plates = regions_by_frame(private)
    changed, blurred = blur_frames(regions, frames, hi_frames)
    return PrivacyReport(
        people=people,
        plates=plates,
        frames_blurred=changed,
        regions_blurred=blurred,
        checked=len(private) == len(PRIVACY_CONCEPTS),
    )


def delete_raw(scan_dir: Path, uploads: list[Path]) -> list[str]:
    """Delete the uploaded clips, intermediate videos, audio and corner frames. Returns names."""
    if KEEP_RAW_VIDEO:
        return []
    gone: list[str] = []
    for p in [*uploads, *(scan_dir / n for n in RAW_FILES)]:
        try:
            if p.is_file() and scan_dir.resolve() in p.resolve().parents:
                p.unlink()
                gone.append(p.name)
        except OSError:
            log.exception("couldn't delete %s", p)
    corners = scan_dir / "corners"
    if corners.is_dir():
        shutil.rmtree(corners, ignore_errors=True)
        gone.append("corners/")
    return gone
