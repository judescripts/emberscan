"""geometry_bridge: synthetic marker scenes -> measured, zoned hazards with evidence images."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from test_geometry_synthetic import POSES, UPRIGHT, camera, project, render, sam_mask

from emberscan_workers.contracts import BBox, Evidence, Hazard
from emberscan_workers.geometry import FrameMeasurement, aggregate
from emberscan_workers.geometry_bridge import measure_hazards, trusted
from emberscan_workers.meta.sam import Box, Track
from emberscan_workers.pipeline import ScanJob


def _scene(tmp_path: Path, with_marker: bool = True) -> tuple[list[Path], Track]:
    frames: list[Path] = []
    track = Track(object_id="0", concept="shrub")
    for i, (cam, look, roll) in enumerate(POSES):
        p = camera(cam, look, roll)
        img = render(p, seed=i, hazard_poly=UPRIGHT)
        if not with_marker:
            img[:, :] = cv2.GaussianBlur(img, (0, 0), 25)
        path = tmp_path / "frames" / f"{i:05d}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        frames.append(path)
        track.masks[i] = sam_mask(p, UPRIGHT)
        pts = project(p, UPRIGHT)
        track.boxes[i] = Box(
            left=float(pts[:, 0].min()),
            top=float(pts[:, 1].min()),
            right=float(pts[:, 0].max()),
            bottom=float(pts[:, 1].max()),
            confidence=0.9,
        )
    return frames, track


def _hazard() -> Hazard:
    return Hazard(
        id="h-shrub-0",
        cls="shrub",
        concept="shrub",
        track_id="0",
        label="Shrub",
        frames=[0, 1, 2, 3],
        confidence="high",
        evidence=[
            Evidence(frame_index=0, timestamp_ms=0, bbox=BBox(left=0, top=0, right=1, bottom=1))
        ],
    )


def _job(tmp_path: Path) -> ScanJob:
    return ScanJob(scan_id="t", dir=tmp_path, video_path=tmp_path / "v.mp4", building_label="A")


def test_measures_zones_and_renders_evidence(tmp_path: Path) -> None:
    frames, track = _scene(tmp_path)
    [h] = measure_hazards([_hazard()], {"h-shrub-0": track}, frames, _job(tmp_path))
    assert h.method == "marker"
    assert h.distance_ft is not None and h.distance_ft.min <= 3.0 <= h.distance_ft.max
    assert h.zone == "Z0" and not h.zone_uncertain
    assert h.evidence[0].image_path == "evidence/h-shrub-0.jpg"
    assert (tmp_path / "evidence" / "h-shrub-0.jpg").stat().st_size > 10_000
    assert h.evidence[0].bbox.right > h.evidence[0].bbox.left > 0


def test_no_marker_keeps_visual_and_still_renders(tmp_path: Path) -> None:
    frames, track = _scene(tmp_path, with_marker=False)
    [h] = measure_hazards([_hazard()], {"h-shrub-0": track}, frames, _job(tmp_path))
    assert h.method == "visual" and h.distance_ft is None and h.zone is None
    assert h.evidence and (tmp_path / h.evidence[0].image_path).exists()
    assert np.isfinite(h.evidence[0].bbox.left)


def _frame(i: int, mid: float, marker_ft: float, half: float = 0.3) -> FrameMeasurement:
    return FrameMeasurement(
        frame_index=i,
        mid_ft=mid,
        min_ft=max(mid - half, 0.0),
        max_ft=mid + half,
        confidence="high",
        contact_px=(0.0, 0.0),
        contact_in=(0.0, mid * 12),
        marker_dist_ft=marker_ft,
        reproj_rms_px=0.5,
        edge_in=1.0,
        fit_in=1.0,
        extrap_in=1.0,
        scale_in=0.1,
    )


def test_trusted_drops_far_frames_when_near_ones_exist() -> None:
    # Near the marker the base reads 0.5 ft; far frames (base hidden by grass) read 9 ft.
    m = aggregate([_frame(i, 0.5, 2.0) for i in range(4)] + [_frame(9, 9.0, 14.0)])
    kept, why = trusted(m)
    assert why == "" and kept is not None
    assert kept.distance_ft.max < 1.5
    assert 9 not in kept.frames_used


def test_trusted_says_why_not() -> None:
    assert trusted(None) == (None, "no marker in view")
    far = aggregate([_frame(i, 9.0, 12.0) for i in range(3)])
    assert trusted(far) == (None, "too far from the marker")
    split = aggregate([_frame(1, 0.2, 3.0), _frame(2, 8.0, 9.0)])
    assert trusted(split)[0] is None
    assert "disagree" in trusted(split)[1]
