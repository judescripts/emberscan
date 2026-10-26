"""Marker detection and hazard distance on synthetic ground-plane scenes (no real footage).

A pinhole camera (1080p phone-like, ~65 deg horizontal FOV) stands ~10 ft from the wall at
chest height and looks down at the marker. The printed sheet is rendered from the marker spec
onto a textured mulch background with cv2.warpPerspective using the exact ground->image
homography, so recovered geometry can be checked against ground truth.

World frame (inches): X along the wall, Y away from the wall (wall line Y = 0), Z up. The
camera faces the wall, so image-right is -X; the marker's ground frame (x to image-right,
y away from the wall) is therefore x = -X, y = Y.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np
import pytest

from emberscan_workers.geometry import (
    detect_marker,
    estimate_focal_px,
    measure_frame,
    measure_track,
    with_focal,
)
from emberscan_workers.geometry.marker import (
    BOARD_LEFT_IN,
    BOARD_TOP_IN,
    MARKER_COLS,
    MARKER_ROWS,
    PAGE_H_IN,
    PAGE_W_IN,
    SQUARE_IN,
    MarkerPose,
)

W, H, F = 1920, 1080, 1500.0
SS = 2  # supersampling factor for anti-aliased rendering
PAPER_PX_PER_IN = 40


def encode_rle(mask: np.ndarray) -> dict[str, Any]:
    """Tiny pycocotools-compatible compressed RLE encoder (column-major)."""
    h, w = mask.shape
    flat = mask.flatten(order="F").astype(np.int8)
    change = np.flatnonzero(np.diff(flat)) + 1
    runs = np.diff(np.concatenate([[0], change, [flat.size]])).tolist()
    if flat[0] == 1:
        runs = [0, *runs]
    out = []
    for i, x in enumerate(runs):
        if i > 2:
            x -= runs[i - 2]
        more = True
        while more:
            c = x & 0x1F
            x >>= 5
            more = (x != -1) if (c & 0x10) else (x != 0)
            if more:
                c |= 0x20
            out.append(chr(c + 48))
    return {"size": [h, w], "counts": "".join(out)}


def camera(cam: tuple[float, float, float], look: tuple[float, float, float], roll_deg: float = 0):
    """3x4 projection matrix for a pinhole camera at `cam` looking at `look`."""
    k = np.array([[F, 0, (W - 1) / 2], [0, F, (H - 1) / 2], [0, 0, 1]])
    c = np.asarray(cam, float)
    fwd = np.asarray(look, float) - c
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    r = np.stack([right, down, fwd])
    a = np.deg2rad(roll_deg)
    roll = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    r = roll @ r
    return k @ np.hstack([r, (-r @ c)[:, None]])


def ground_to_image(p: np.ndarray) -> np.ndarray:
    """Homography for world ground points (X, Y, 1) -> image pixels."""
    return p[:, [0, 1, 3]]


def project(p: np.ndarray, pts_xyz: np.ndarray) -> np.ndarray:
    hom = np.hstack([pts_xyz, np.ones((len(pts_xyz), 1))]) @ p.T
    return hom[:, :2] / hom[:, 2:3]


def marker_to_world(xy_m: np.ndarray) -> np.ndarray:
    return np.column_stack([-xy_m[:, 0], xy_m[:, 1]])


def paper_image() -> np.ndarray:
    s = PAPER_PX_PER_IN
    img = np.full((int(PAGE_H_IN * s), int(PAGE_W_IN * s), 3), 235, np.uint8)
    img[int(0.4 * s) : int(0.82 * s), int(0.4 * s) : int((PAGE_W_IN - 0.4) * s)] = (0, 110, 255)
    for r in range(MARKER_ROWS):
        for c in range(MARKER_COLS):
            if (r + c) % 2 == 0:
                y0 = int(round((BOARD_TOP_IN + r * SQUARE_IN) * s))
                x0 = int(round((BOARD_LEFT_IN + c * SQUARE_IN) * s))
                img[y0 : y0 + int(SQUARE_IN * s), x0 : x0 + int(SQUARE_IN * s)] = 25
    return img


def paper_px_to_world() -> np.ndarray:
    """Paper pixel (pu, pv) -> world ground (X, Y): u = (pu + .5)/s, X = -(u - W/2), Y = v."""
    s = PAPER_PX_PER_IN
    return np.array(
        [
            [-1 / s, 0, PAGE_W_IN / 2 - 0.5 / s],
            [0, 1 / s, 0.5 / s],
            [0, 0, 1],
        ]
    )


def render(p: np.ndarray, seed: int = 0, hazard_poly: np.ndarray | None = None) -> np.ndarray:
    """Render a frame: mulch texture, stucco wall above the wall line, the sheet, a hazard."""
    rng = np.random.default_rng(seed)
    big_w, big_h = W * SS, H * SS
    noise = rng.normal(0, 1, (H // 4, W // 4)).astype(np.float32)
    noise = cv2.resize(cv2.GaussianBlur(noise, (0, 0), 1.2), (big_w, big_h))
    base = np.array([60, 95, 135], np.float32)  # brown mulch (BGR)
    img = np.clip(base + noise[..., None] * 35, 0, 255).astype(np.uint8)
    up = np.diag([SS, SS, 1.0]) @ np.array(
        [[1, 0, 0.5 * (1 - 1 / SS)], [0, 1, 0.5 * (1 - 1 / SS)], [0, 0, 1]]
    )
    pp = up @ p
    wall = project(
        pp, np.array([[x, 0.0, 0.0] for x in (-400, 400)] + [[400, 0, 300], [-400, 0, 300]])
    )
    cv2.fillPoly(img, [np.round(wall).astype(np.int32)], (170, 200, 215))
    hmat = ground_to_image(pp) @ paper_px_to_world()
    paper = paper_image()
    warped = cv2.warpPerspective(paper, hmat, (big_w, big_h), flags=cv2.INTER_LINEAR)
    cover = cv2.warpPerspective(np.full(paper.shape[:2], 255, np.uint8), hmat, (big_w, big_h))
    img = np.where(cover[..., None] > 127, warped, img)
    if hazard_poly is not None:
        poly = np.round(project(pp, hazard_poly)).astype(np.int32)
        cv2.fillPoly(img, [poly], (40, 70, 50))
    img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
    img = img.astype(np.float32) + rng.normal(0, 2.0, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def sam_mask(p: np.ndarray, poly_xyz: np.ndarray, down: int = 2) -> dict[str, Any]:
    """SAM-style box-local mask of a projected polygon, at 1/`down` resolution."""
    full = np.zeros((H, W), np.uint8)
    cv2.fillPoly(full, [np.round(project(p, poly_xyz)).astype(np.int32)], 1)
    ys, xs = np.nonzero(full)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    crop = full[y0:y1, x0:x1].astype(np.float32)
    small = (
        cv2.resize(
            crop,
            (max(1, (x1 - x0) // down), max(1, (y1 - y0) // down)),
            interpolation=cv2.INTER_AREA,
        )
        > 0.5
    )
    return {"rle": encode_rle(small), "bounds": [float(x0), float(y0), float(x1), float(y1)]}


# Camera poses: ~10 ft from the wall at chest height (52-57 in), varied position/aim/roll.
POSES = [
    ((0.0, 120.0, 54.0), (0.0, 25.0, 0.0), 0.0),
    ((12.0, 115.0, 52.0), (-5.0, 24.0, 0.0), 2.0),
    ((-15.0, 125.0, 57.0), (-10.0, 26.0, 0.0), -3.0),
    ((6.0, 110.0, 55.0), (-8.0, 22.0, 0.0), 1.0),
]

# A thin upright hazard (e.g. a plank or post row) standing on the ground 36 in from the wall,
# 10-25 in to the right of the marker centre (marker x), 20 in tall.
UPRIGHT = np.array([[-10, 36, 0], [-25, 36, 0], [-25, 36, 20], [-10, 36, 20]], float)
# A flat patch (mulch) on the ground from 36 to 54 in out.
FLAT = np.array([[-8, 36, 0], [-28, 36, 0], [-28, 54, 0], [-8, 54, 0]], float)


@pytest.fixture(scope="module")
def scenes() -> list[tuple[np.ndarray, np.ndarray, MarkerPose | None]]:
    out = []
    for i, (cam, look, roll) in enumerate(POSES):
        p = camera(cam, look, roll)
        frame = render(p, seed=i, hazard_poly=UPRIGHT)
        out.append((p, frame, detect_marker(frame)))
    return out


def test_detects_marker_in_every_oblique_view(scenes) -> None:
    for _, _, pose in scenes:
        assert pose is not None
        assert pose.reproj_rms_px < 0.5
        assert 5 < pose.square_px < 40


PTS_NEAR = np.array([[-2.0, 2.5], [2.0, 8.5], [0.0, 0.0], [-6.0, 0.0], [6.0, 12.0]])
PTS_FAR = np.array([[15.0, 36.0], [-10.0, 36.0], [24.0, 24.0], [0.0, 60.0]])  # 2-5 ft out


def _ground_error(p: np.ndarray, pose: MarkerPose, pts_m: np.ndarray) -> np.ndarray:
    px = project(p, np.column_stack([marker_to_world(pts_m), np.zeros(len(pts_m))]))
    return np.linalg.norm(pose.to_ground(px) - pts_m, axis=1)


def test_free_homography_is_accurate_near_the_marker(scenes) -> None:
    for p, _, pose in scenes:
        assert pose is not None and pose.model == "homography"
        assert _ground_error(p, pose, PTS_NEAR).max() < 0.5


def test_free_homography_error_is_covered_by_its_samples(scenes) -> None:
    """Far from a small marker the free fit is noisy; its Monte Carlo spread must say so."""
    for p, _, pose in scenes:
        assert pose is not None
        px = project(p, np.column_stack([marker_to_world(PTS_FAR), np.zeros(len(PTS_FAR))]))
        for q, truth in zip(px, PTS_FAR, strict=True):
            ys = pose.ground_samples(q)[:, 1]
            assert abs(pose.to_ground(q)[0, 1] - truth[1]) < 3.5 * ys.std() + 0.25


def test_focal_estimate_and_calibrated_pose_within_half_inch(scenes) -> None:
    poses = [pose for _, _, pose in scenes]
    est = estimate_focal_px(poses)
    assert est is not None
    f, f_std = est
    assert abs(f - F) / F < 0.06 and 0 < f_std < 0.05 * f
    assert estimate_focal_px(poses[:1]) is None  # needs >= 2 views
    for (p, _, _), pose in zip(scenes, poses, strict=True):
        assert pose is not None
        cal = with_focal(pose, f, f_std)
        assert cal.model == "pnp" and cal.focal_px == pytest.approx(f)
        assert _ground_error(p, cal, PTS_NEAR).max() < 0.5
        err = _ground_error(p, cal, PTS_FAR)
        assert err[:3].max() < 0.5, err  # out to 3 ft
        assert err[3] < 1.0, err  # 5 ft


def test_wall_side_is_row_zero_and_x_points_right(scenes) -> None:
    _, _, pose = scenes[0]
    assert pose is not None
    g = pose.corners_px
    assert g[0, :, 1].mean() < g[-1, :, 1].mean()  # wall row is higher in the image
    assert g[:, 0, 0].mean() < g[:, -1, 0].mean()  # x increases to image right
    wall = pose.wall_line_image(60)
    assert wall.shape == (2, 2) and np.isfinite(wall).all()


def test_no_marker_returns_none() -> None:
    frame = render(camera(*POSES[0][:2]), seed=4)
    frame[300:700, 700:1300] = 120  # cover the sheet
    assert detect_marker(frame) is None
    assert detect_marker(np.zeros((H, W, 3), np.uint8)) is None


def test_upright_hazard_at_3ft(scenes) -> None:
    masks = {i: sam_mask(p, UPRIGHT) for i, (p, _, _) in enumerate(scenes)}
    poses = {i: pose for i, (_, _, pose) in enumerate(scenes)}
    m = measure_track(masks, poses, mode="bottom")
    assert m is not None
    r = m.distance_ft
    assert r.min <= 3.0 <= r.max, r
    assert r.max - r.min < 1.0, r
    assert m.confidence == "high"
    assert m.method == "marker"
    assert m.frames_used == [0, 1, 2, 3]
    assert abs(m.median_ft - 3.0) < 0.15
    for f in m.per_frame:
        assert 8 < f.contact_in[0] < 27  # contact on the hazard, right of the marker


def test_upright_hazard_at_3ft_calibrated(scenes) -> None:
    est = estimate_focal_px([pose for _, _, pose in scenes])
    assert est is not None
    masks = {i: sam_mask(p, UPRIGHT) for i, (p, _, _) in enumerate(scenes)}
    poses = {i: with_focal(pose, *est) for i, (_, _, pose) in enumerate(scenes) if pose}
    m = measure_track(masks, poses)
    assert m is not None
    assert m.distance_ft.min <= 3.0 <= m.distance_ft.max
    assert m.distance_ft.max - m.distance_ft.min <= 0.5
    assert m.confidence == "high"


def test_flat_patch_footprint_mode(scenes) -> None:
    masks = {i: sam_mask(p, FLAT) for i, (p, _, _) in enumerate(scenes)}
    poses = {i: pose for i, (_, _, pose) in enumerate(scenes)}
    m = measure_track(masks, poses, mode="footprint")
    assert m is not None
    assert m.distance_ft.min <= 3.0 <= m.distance_ft.max
    # The bottom boundary of a flat patch is its near edge (54 in = 4.5 ft): wrong for mulch.
    b = measure_track(masks, poses, mode="bottom")
    assert b is not None and b.median_ft > 4.2


def test_no_marker_frames_returns_none(scenes) -> None:
    p = scenes[0][0]
    assert measure_track({0: sam_mask(p, UPRIGHT)}, {0: None}) is None
    assert measure_track({0: sam_mask(p, UPRIGHT)}, {5: scenes[0][2]}) is None


def test_single_frame_is_capped_at_medium(scenes) -> None:
    p, _, pose = scenes[0]
    assert pose is not None
    m = measure_track({0: sam_mask(p, UPRIGHT)}, {0: pose})
    assert m is not None and m.confidence == "medium"
    f = measure_frame(sam_mask(p, UPRIGHT), pose, 0)
    assert f is not None and f.confidence == "high"


def test_far_hazard_is_low_confidence() -> None:
    # Filming along the wall: the marker is near, the hazard ~17 ft further along the wall.
    far = UPRIGHT + np.array([-185.0, 0.0, 0.0])
    p = camera((60.0, 60.0, 54.0), (-60.0, 10.0, 0.0))
    frame = render(p, seed=7, hazard_poly=far)
    pose = detect_marker(frame)
    assert pose is not None
    m = measure_frame(sam_mask(p, far), pose, 0)
    assert m is not None
    assert m.marker_dist_ft > 15
    assert m.confidence == "low"
    assert m.min_ft <= 3.0 <= m.max_ft
