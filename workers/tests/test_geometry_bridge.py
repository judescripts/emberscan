"""geometry_bridge: synthetic marker scenes -> measured, zoned hazards with evidence images."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from test_geometry_synthetic import POSES, UPRIGHT, camera, project, render, sam_mask

from emberscan_workers.contracts import BBox, Evidence, Hazard
from emberscan_workers.geometry_bridge import measure_hazards
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
