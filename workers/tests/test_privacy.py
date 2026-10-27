"""Privacy guard: people and plates blurred in every frame they're seen; raw video deleted."""

from pathlib import Path

import cv2
import numpy as np

from emberscan_workers.meta.sam import Box, SegmentationResult, Track
from emberscan_workers.privacy import (
    blur_boxes,
    delete_raw,
    guard_frames,
    split_privacy,
    track_boxes,
)
from emberscan_workers.spend import SpendLedger


def box(x0: float, y0: float, x1: float, y1: float) -> Box:
    return Box(left=x0, top=y0, right=x1, bottom=y1, confidence=0.9)


def result(prompt: str, tracks: dict[str, Track]) -> SegmentationResult:
    return SegmentationResult(
        prompt, tracks, frames_billed=0, cost_usd=0.0, latency_s=0.0, complete=True
    )


def track(concept: str, boxes: dict[int, Box]) -> Track:
    return Track(object_id="1", concept=concept, boxes=boxes)


def test_short_gaps_in_a_track_are_filled_long_ones_are_not() -> None:
    b1, b2 = box(0, 0, 10, 10), box(20, 0, 30, 10)
    filled = track_boxes(track("person", {0: b1, 3: b2, 20: b1}), max_gap=6)
    assert set(filled) == {0, 1, 2, 3, 20}  # 1-2 filled, 4-19 is too long a gap
    assert filled[1] is b1 and filled[2] is b2  # nearer box


def test_blur_changes_the_box_and_nothing_far_outside_it() -> None:
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (100, 100, 3), dtype=np.uint8)
    before = img.copy()
    assert blur_boxes(img, [box(40, 40, 60, 60)]) == 1
    assert np.abs(img[45:55, 45:55].astype(int) - before[45:55, 45:55]).mean() > 20
    assert np.array_equal(img[:30, :30], before[:30, :30])


def _frames(d: Path, n: int, size: tuple[int, int]) -> list[Path]:
    d.mkdir()
    rng = np.random.default_rng(1)
    paths = []
    for i in range(n):
        p = d / f"frame_{i + 1:06d}.jpg"
        cv2.imwrite(str(p), rng.integers(0, 255, (*size, 3), dtype=np.uint8))
        paths.append(p)
    return paths


def test_guard_blurs_low_and_high_res_frames_and_counts(tmp_path: Path) -> None:
    lo = _frames(tmp_path / "frames", 4, (64, 36))
    hi = _frames(tmp_path / "frames_hi", 4, (128, 72))
    hi_before = cv2.imread(str(hi[1]))
    results = [
        result("shrub", {"1": track("shrub", {0: box(0, 0, 5, 5)})}),
        result("person", {"1": track("person", {1: box(10, 20, 30, 50), 2: box(10, 20, 30, 50)})}),
        result("license plate", {}),
    ]
    hazards, private = split_privacy(results)
    assert [r.concept for r in hazards] == ["shrub"]
    rep = guard_frames(private, lo, hi)
    assert rep.checked and rep.people == 1 and rep.plates == 0
    assert rep.frames_blurred == 2 and "1 person" in rep.summary()
    # the full-resolution twin is blurred at twice the coordinates
    diff = np.abs(cv2.imread(str(hi[1])).astype(int) - hi_before)
    assert diff[45:95, 25:55].mean() > 20


def test_missing_privacy_concept_is_reported_unchecked(tmp_path: Path) -> None:
    lo = _frames(tmp_path / "frames", 2, (64, 36))
    rep = guard_frames([result("person", {})], lo)  # license plate never came back
    assert not rep.checked


def test_delete_raw_keeps_frames_and_report(tmp_path: Path) -> None:
    for name in (
        "upload.mov",
        "upload01.mov",
        "sam.mp4",
        "joined.mp4",
        "audio.wav",
        "report.json",
    ):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "frames").mkdir()
    ups = [tmp_path / "upload.mov", tmp_path / "upload01.mov"]
    gone = delete_raw(tmp_path, ups)
    assert {"upload.mov", "upload01.mov", "sam.mp4", "audio.wav"} <= set(gone)
    assert (tmp_path / "report.json").exists() and (tmp_path / "frames").is_dir()


def test_partner_spend_has_its_own_limit() -> None:
    led = SpendLedger("t", limit_usd=0.10, partner_limit_usd=0.20)
    led.record("sam", "sam-3.1", 0.09, {})
    led.record("agent", "meta-models/muse-spark-open-1026", 0.15, {}, partner=True)
    assert round(led.spent_usd, 2) == 0.09 and round(led.partner_usd, 2) == 0.15
    led.check("agent", 0.04, partner=True)  # 0.19 <= 0.20
    led.check("after_image", 0.01)  # Meta side unaffected by partner spend
