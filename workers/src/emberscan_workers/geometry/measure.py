"""Hazard distance from the wall, measured on the ground plane with the scale marker (C2).

For each frame where a hazard has a SAM mask *and* the marker was detected, we pick the
hazard's ground pixels, map them to ground inches with the marker's homography, and take the
point closest to the wall line (``y = 0``). Per-frame uncertainty combines:

* the mask edge: +/- 2 mask pixels (scaled to frame pixels), through the local ground scale;
* the marker fit: the spread of that point under the pose's Monte Carlo homographies (corner
  noise, focal noise). This grows quickly with distance from a small marker;
* ground that is not perfectly flat: a term growing with distance from the marker;
* print scale: 1 %.

Frames are then combined robustly into a ``Range`` in feet with a confidence. See
docs/how-measurement-works.md.

Which pixels touch the ground depends on the hazard's shape (``ContactMode``):

* ``"bottom"`` (default, upright things: shrubs, woodpiles, posts, trunks): the mask's
  bottom boundary, i.e. mask pixels whose pixel below is not mask, taken as the lowest mask
  pixel of each column. Columns where that lower outline is steep (> ``MAX_CONTACT_SLOPE``)
  are dropped: they are the object's sides, which perspective slants, not its base. Columns
  ending on the frame's bottom row are skipped too (the object continues out of view).
  Overhanging parts above the ground project *toward* the wall, which errs on the side of
  flagging, never of passing. For a deep object seen from the front, the visible base is
  its camera side, so the wall-side contact is only seen from oblique / along-wall views.
* ``"footprint"`` (flat things lying on the ground: mulch, leaf litter): every mask pixel is
  on the ground, so the whole mask is used. The bottom boundary of a flat patch is its edge
  nearest the camera, which would overstate its distance from the wall.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

import cv2
import numpy as np

from ..contracts import Confidence, Range
from .marker import MarkerPose, marker_center_in
from .rle import box_local_mask, mask_scale

ContactMode = Literal["bottom", "footprint"]

# Hazard classes (docs/hazard-taxonomy.md) that lie flat on the ground.
FLAT_CLASSES: frozenset[str] = frozenset({"wood_mulch", "leaf_litter"})

IN_PER_FT = 12.0
MASK_EDGE_MASK_PX = 2.0  # SAM mask edge uncertainty, in mask pixels
MIN_EDGE_PX = 1.0  # floor on edge uncertainty in frame pixels
FIT_SIGMAS = 2.0  # marker fit term = this many Monte Carlo standard deviations
EXTRAP_BASE = 0.01  # non-flat ground: relative error growing with distance from marker...
EXTRAP_PER_FT = 0.003  # ...plus this much more per foot
PRINT_SCALE_TOL = 0.01  # printer scaling / paper tolerance (1 %)
MAX_CONTACT_SLOPE = 1.5  # |d row / d col| above this is a side edge, not a base
CONTACT_PERCENTILE = 0.5  # use this percentile of distances, not the raw min (stray pixels)
MAX_RANGE_FT = 150.0  # contacts projecting beyond this are near the horizon: ignored

# Per-frame confidence thresholds.
HIGH_MAX_MARKER_FT = 8.0
LOW_MIN_MARKER_FT = 15.0
HIGH_MAX_REPROJ_PX = 1.5
LOW_MIN_REPROJ_PX = 3.0
HIGH_MAX_HALF_FT = 0.75
LOW_MIN_HALF_FT = 1.5
LOW_MAX_SQUARE_PX = 4.0
SPREAD_DOWNGRADE_FT = 1.0  # frames disagreeing by more than this lose a confidence level
SPREAD_LOW_FT = 3.0

_RANK: dict[Confidence, int] = {"low": 0, "medium": 1, "high": 2}
_BY_RANK: tuple[Confidence, Confidence, Confidence] = ("low", "medium", "high")


@dataclass(frozen=True)
class FrameMeasurement:
    """Distance of one hazard from the wall in one frame (for the report and debugging).

    Uncertainty terms are half-widths in inches; ``min_ft``/``max_ft`` = mid -/+ their
    combination (edge and fit in quadrature, plus ground flatness and print scale).
    """

    frame_index: int
    mid_ft: float
    min_ft: float
    max_ft: float
    confidence: Confidence
    contact_px: tuple[float, float]  # chosen ground-contact pixel (frame coords)
    contact_in: tuple[float, float]  # same point on the ground, inches (x along wall, y out)
    marker_dist_ft: float  # ground distance from the contact point to the marker centre
    reproj_rms_px: float
    edge_in: float
    fit_in: float
    extrap_in: float
    scale_in: float


@dataclass(frozen=True)
class DistanceMeasurement:
    """A hazard's distance from the wall line across a track."""

    distance_ft: Range
    confidence: Confidence
    median_ft: float
    frames_used: list[int]
    per_frame: list[FrameMeasurement] = field(default_factory=list)
    method: Literal["marker"] = "marker"

    @property
    def best_frame(self) -> FrameMeasurement:
        """The most trustworthy frame (highest confidence, then narrowest range): evidence."""
        return max(self.per_frame, key=lambda f: (_RANK[f.confidence], f.min_ft - f.max_ft))


def contact_mode_for(cls: str) -> ContactMode:
    """Contact mode for a hazard class from docs/hazard-taxonomy.md."""
    return "footprint" if cls in FLAT_CLASSES else "bottom"


def _contact_pixels(
    local: np.ndarray, offset: tuple[int, int], frame_h: int, mode: ContactMode, step: int = 2
) -> np.ndarray:
    """Candidate ground pixels in frame coordinates, (N, 2) float as (x, y).

    ``step`` is the column offset (frame px) used to measure the lower outline's slope.
    """
    if local.shape[0] >= 3 and local.shape[1] >= 3:
        opened = cv2.morphologyEx(local.view(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        if opened.any():
            local = opened.astype(bool)
    x0, y0 = offset
    if mode == "footprint":
        rows, cols = np.nonzero(local)
        return np.column_stack([cols + x0, rows + y0]).astype(np.float64)
    h, w = local.shape
    has = local.any(axis=0)
    bottom = (h - 1 - np.argmax(local[::-1], axis=0)).astype(np.float64)
    bottom[~has] = np.nan
    idx = np.arange(w)
    left = bottom[np.clip(idx - step, 0, w - 1)]
    right = bottom[np.clip(idx + step, 0, w - 1)]
    span = np.clip(idx + step, 0, w - 1) - np.clip(idx - step, 0, w - 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        slope = np.abs(right - left) / np.maximum(span, 1)
    keep = has & (slope <= MAX_CONTACT_SLOPE)
    keep &= bottom + y0 < frame_h - 1  # bottom frame row: object leaves the frame
    cols = idx[keep]
    # Contact is at the pixel's lower edge (pixel centres are at integer coordinates).
    return np.column_stack([cols + x0, bottom[keep] + y0 + 0.5]).astype(np.float64)


def _frame_confidence(
    marker_ft: float, rms_px: float, half_ft: float, square_px: float
) -> Confidence:
    if (
        marker_ft > LOW_MIN_MARKER_FT
        or rms_px > LOW_MIN_REPROJ_PX
        or half_ft > LOW_MIN_HALF_FT
        or square_px < LOW_MAX_SQUARE_PX
    ):
        return "low"
    if marker_ft > HIGH_MAX_MARKER_FT or rms_px > HIGH_MAX_REPROJ_PX or half_ft > HIGH_MAX_HALF_FT:
        return "medium"
    return "high"


def measure_frame(
    mask: Mapping[str, Any],
    pose: MarkerPose,
    frame_index: int = 0,
    mode: ContactMode = "bottom",
) -> FrameMeasurement | None:
    """Measure one hazard mask against one detected marker (same frame).

    Args:
        mask: SAM box-local mask dict ``{"rle": {...}, "bounds": [l, t, r, b]}``.
        pose: the marker detected in the same frame.
        frame_index: carried through for the report.
        mode: which mask pixels touch the ground (see module docstring).

    Returns None when no usable ground pixel exists (empty mask, only frame-edge or
    above-horizon pixels).
    """
    local, offset = box_local_mask(mask)
    sx, sy = mask_scale(mask)
    step = max(2, int(round(MASK_EDGE_MASK_PX * sx)))
    px = _contact_pixels(local, offset, pose.image_size[1], mode, step)
    if len(px) == 0:
        return None
    px = px[pose.is_below_horizon(px)]
    if len(px) == 0:
        return None
    ground = pose.to_ground(px)
    ok = np.isfinite(ground).all(axis=1) & (ground[:, 1] < MAX_RANGE_FT * IN_PER_FT)
    px, ground = px[ok], ground[ok]
    if len(px) == 0:
        return None
    k = min(len(px) - 1, int(len(px) * CONTACT_PERCENTILE / 100))
    idx = int(np.argpartition(ground[:, 1], k)[k])
    p, g = px[idx], ground[idx]
    d_in = float(g[1])

    # Local sensitivity of the wall distance to pixel shifts (inches per pixel).
    offsets = np.array([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]])
    probe = pose.to_ground(p + offsets)
    grad = math.hypot((probe[0, 1] - probe[1, 1]) / 2, (probe[2, 1] - probe[3, 1]) / 2)

    edge_px = max(MASK_EDGE_MASK_PX * max(sx, sy), MIN_EDGE_PX)
    edge_in = grad * edge_px
    ys = pose.ground_samples(p)[:, 1]
    ys = ys[np.isfinite(ys)]
    fit_in = FIT_SIGMAS * float(ys.std()) if len(ys) > 1 else float("inf")
    cx, cy = marker_center_in()
    marker_in = math.hypot(g[0] - cx, g[1] - cy)
    marker_ft = marker_in / IN_PER_FT
    extrap_in = marker_in * (EXTRAP_BASE + EXTRAP_PER_FT * marker_ft)
    scale_in = PRINT_SCALE_TOL * abs(d_in)
    half_in = math.hypot(edge_in, fit_in) + extrap_in + scale_in

    mid_ft = max(d_in, 0.0) / IN_PER_FT
    half_ft = half_in / IN_PER_FT
    return FrameMeasurement(
        frame_index=frame_index,
        mid_ft=mid_ft,
        min_ft=max(mid_ft - half_ft, 0.0),
        max_ft=mid_ft + half_ft,
        confidence=_frame_confidence(marker_ft, pose.reproj_rms_px, half_ft, pose.square_px),
        contact_px=(float(p[0]), float(p[1])),
        contact_in=(float(g[0]), float(g[1])),
        marker_dist_ft=marker_ft,
        reproj_rms_px=pose.reproj_rms_px,
        edge_in=edge_in,
        fit_in=fit_in,
        extrap_in=extrap_in,
        scale_in=scale_in,
    )


def aggregate(frames: Iterable[FrameMeasurement]) -> DistanceMeasurement | None:
    """Combine per-frame measurements robustly.

    The centre is the median of per-frame mids and the half-width the median per-frame
    half-width; the range is then widened to cover the spread of mids after dropping the top
    and bottom 20 % of frames (from 5 frames up). It is rounded outward to 0.1 ft and never
    negative. Confidence is the median per-frame confidence (ties go to the lower level),
    capped at "medium" for a single frame and lowered when frames disagree (trimmed mid
    spread > 1 ft: one level; > 3 ft: low).
    """
    fs = sorted(frames, key=lambda f: f.mid_ft)
    if not fs:
        return None
    n = len(fs)
    trim = n // 5 if n >= 5 else 0
    kept = fs[trim : n - trim]
    median = float(np.median([f.mid_ft for f in fs]))
    half = float(np.median([(f.max_ft - f.min_ft) / 2 for f in fs]))
    lo = min(median - half, kept[0].mid_ft)
    hi = max(median + half, kept[-1].mid_ft)
    lo = max(math.floor(lo * 10 + 1e-9) / 10, 0.0)
    hi = max(math.ceil(hi * 10 - 1e-9) / 10, lo)

    ranks = sorted(_RANK[f.confidence] for f in kept)
    rank = ranks[(len(ranks) - 1) // 2]
    if n == 1:
        rank = min(rank, _RANK["medium"])
    spread = kept[-1].mid_ft - kept[0].mid_ft
    if spread > SPREAD_LOW_FT:
        rank = _RANK["low"]
    elif spread > SPREAD_DOWNGRADE_FT:
        rank = max(rank - 1, 0)
    return DistanceMeasurement(
        distance_ft=Range(min=round(lo, 1), max=round(hi, 1)),
        confidence=_BY_RANK[rank],
        median_ft=round(median, 2),
        frames_used=sorted(f.frame_index for f in fs),
        per_frame=sorted(fs, key=lambda f: f.frame_index),
    )


def measure_track(
    masks: Mapping[int, Mapping[str, Any]],
    poses: Mapping[int, MarkerPose | None],
    mode: ContactMode = "bottom",
) -> DistanceMeasurement | None:
    """Measure one hazard track's distance from the wall line across frames.

    Args:
        masks: frame index -> SAM box-local mask dict (``Track.masks``).
        poses: frame index -> detected marker (or None), indexed like ``masks`` (the same
            frames of the same normalized video).
        mode: ground-contact mode; use ``contact_mode_for(hazard.cls)``.

    Returns None when no frame has both a mask and a marker: the caller should fall back to
    a visual estimate and mark the hazard needs-review.
    """
    per_frame: list[FrameMeasurement] = []
    for frame in sorted(masks):
        pose = poses.get(frame)
        if pose is None:
            continue
        m = measure_frame(masks[frame], pose, frame, mode)
        if m is not None:
            per_frame.append(m)
    return aggregate(per_frame)
