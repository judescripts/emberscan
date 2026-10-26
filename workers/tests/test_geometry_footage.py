"""Local-only: run marker detection on the AI-generated how-to-film clip.

Skipped when the footage (kept outside the repo) or ffmpeg is missing, e.g. in CI.

Note (Oct 26): the current AI clip shows an 8 x 7 square board laid landscape (7 x 6 inner
corners), not the printed 6 x 8 spec, so it cannot match. The test then xfails with that
reason instead of passing on a partial-grid match; regenerate the clip from
docs/filming/emberscan-scale-marker.pdf and it becomes a real check.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import pytest

from emberscan_workers.geometry import detect_marker

CLIP = Path(r"C:\Users\judes\EmberScan-footage\how-to-film\1-place-the-marker.mp4")

pytestmark = [
    pytest.mark.skipif(not CLIP.exists(), reason="local footage not available"),
    pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed"),
]


def test_marker_found_in_place_the_marker_clip(tmp_path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(CLIP), "-vf", "fps=3",
         str(tmp_path / "f_%03d.png")],
        check=True,
    )
    frames = sorted(tmp_path.glob("f_*.png"))
    assert frames
    found = []
    for f in frames:
        pose = detect_marker(cv2.imread(str(f)))
        if pose is not None:
            found.append((f.name, round(pose.reproj_rms_px, 3), round(pose.square_px, 1)))
    rate = len(found) / len(frames)
    print(f"\nmarker detected in {len(found)}/{len(frames)} frames ({rate:.0%}): {found}")
    if not found:
        flags = cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_EXHAUSTIVE
        other = sum(
            cv2.findChessboardCornersSB(cv2.imread(str(f), 0), (7, 6), flags=flags)[0]
            for f in frames
        )
        if other:
            pytest.xfail(f"clip shows a 7x6-inner-corner board ({other} frames), not the 6x8 spec")
    assert found, "marker not found in any frame"
