"""Printed scale marker: the spec shared with the PDF, and its detection in frames (C2, C5).

The marker is one US Letter sheet, printed at 100%, laid flat on the ground (portrait) with
its top short edge touching the base of the wall. It carries a checkerboard of
``MARKER_COLS`` x ``MARKER_ROWS`` squares of exactly ``SQUARE_IN`` inches: 6 squares along
the wall edge, 8 squares away from it, so OpenCV sees ``PATTERN_SIZE`` = (5, 7) inner corners.
``scripts/make_marker_pdf.py`` imports these constants, so code and paper cannot drift.

Ground coordinates (inches) used everywhere in this package:

* origin on the wall line, horizontally at the centre of the sheet;
* ``x`` runs along the wall, positive to the right in the image when facing the wall;
* ``y`` runs away from the wall along the ground; the wall line is ``y = 0``.

Orientation: the 6 x 8 asymmetry tells the detector which grid axis runs along the wall
(5 corners) and which runs away from it (7 corners). It does not tell the two ends of the
long axis apart (an even-by-even board looks the same rotated 180 degrees), so we assume the
filming rule: **the wall-edge side is the one farther from the camera**, i.e. the end of the
long axis that is higher in the image (smaller pixel ``y``). That holds whenever the camera
looks at the wall from the yard side, which is how the filming guide asks people to shoot.
It also assumes the sheet is placed as printed (short edge at the wall); a sheet turned
90 degrees would put the wall line 1-2 in off.

Two ground models:

* ``"homography"`` (default): a free 8-DOF homography fitted to the 35 corners. Unbiased,
  but extrapolation far beyond a small marker is noisy (the horizon is poorly pinned).
* ``"pnp"``: when the camera focal length is known (``estimate_focal_px`` over several
  frames, or a value from metadata) the ground plane comes from a calibrated pose fit, which
  extrapolates far better. ``with_focal`` refits a detected pose without re-detecting.

Each pose carries Monte Carlo samples of its homography (corner noise, and focal-length
noise for ``"pnp"``) so measurements can propagate the fit's uncertainty to any ground point.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
from numpy.typing import ArrayLike, NDArray

# --- Marker spec (single source of truth for the printed sheet) -----------------------------
PAGE_W_IN = 8.5  # US Letter, portrait
PAGE_H_IN = 11.0
MARKER_COLS = 6  # squares along the wall edge (the page's short side)
MARKER_ROWS = 8  # squares away from the wall
SQUARE_IN = 1.0  # exact square size when printed at 100%
WALL_EDGE: Literal["top"] = "top"  # the page's top short edge touches the wall
BOARD_TOP_IN = 1.5  # wall edge (page top) to the board's first row of squares
BOARD_LEFT_IN = (PAGE_W_IN - MARKER_COLS * SQUARE_IN) / 2  # board centred across the page
PATTERN_SIZE = (MARKER_COLS - 1, MARKER_ROWS - 1)  # inner corners (along wall, away from wall)
MIN_PAGE_MARGIN_IN = 0.4  # nothing printed closer than this to a page edge

# --- Fit uncertainty ---------------------------------------------------------------------------
N_SAMPLES = 48  # Monte Carlo homography samples per pose
CORNER_SIGMA_FLOOR_PX = 0.1  # corner noise floor (blur, compression) even when the fit is tight
# A good flat sheet fits its model to a small fraction of a square. Larger residuals mean a
# curled/folded sheet or a wrong grid (e.g. a partial match on a different board): reject.
MAX_REPROJ_RMS_PX = (
    2.0  # real sheets on uneven ground, seen at a slant; looser fits get wider ranges
)
MAX_REPROJ_RMS_REL = 0.08  # of one square's size, for markers seen large
FOCAL_MAX_REL_STD = 0.05  # estimate_focal_px rejects estimates noisier than this
_SEED = 20261026

FloatArray = NDArray[np.float64]
GroundModel = Literal["homography", "pnp"]


def marker_object_points() -> FloatArray:
    """Ground coordinates (in) of the inner corners, shape (rows=7, cols=5, 2).

    Row ``j`` is ``BOARD_TOP_IN + (j + 1) * SQUARE_IN`` from the wall; column ``i`` is centred
    on the sheet, so x runs from -2 in to +2 in for the 6-square board.
    """
    nx, ny = PATTERN_SIZE
    xs = (np.arange(nx) + 1) * SQUARE_IN + BOARD_LEFT_IN - PAGE_W_IN / 2
    ys = (np.arange(ny) + 1) * SQUARE_IN + BOARD_TOP_IN
    gx, gy = np.meshgrid(xs, ys)
    return np.stack([gx, gy], axis=-1).astype(np.float64)


def marker_center_in() -> tuple[float, float]:
    """Ground position (in) of the centre of the inner-corner grid."""
    c = marker_object_points().reshape(-1, 2).mean(axis=0)
    return float(c[0]), float(c[1])


def apply_homography(h: FloatArray, pts: ArrayLike) -> FloatArray:
    """Map (N, 2) points through a 3x3 homography; returns (N, 2). Points at infinity -> nan."""
    p = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
    hom = np.hstack([p, np.ones((len(p), 1))]) @ h.T
    w = hom[:, 2:3]
    with np.errstate(divide="ignore", invalid="ignore"):
        out = hom[:, :2] / w
    out[np.abs(w[:, 0]) < 1e-12] = np.nan
    return out


@dataclass(frozen=True)
class MarkerPose:
    """A detected marker in one frame.

    Attributes:
        h: 3x3 homography, image pixels -> ground inches (see module docstring for axes).
        h_inv: inverse homography, ground inches -> image pixels.
        h_samples: (N_SAMPLES, 3, 3) Monte Carlo draws of ``h`` under corner (and focal)
            noise, for uncertainty propagation.
        corners_px: (7, 5, 2) sub-pixel inner corners, ordered like ``marker_object_points``
            (row 0 nearest the wall, column 0 leftmost in the image).
        reproj_rms_px: RMS distance between detected corners and the fitted model, in px.
        reproj_max_px: worst corner's reprojection error, in pixels.
        square_px: marker size in px: the side of a 1 in square, as the geometric mean of
            its foreshortened width and depth (sqrt of grid area per square).
        extent_px: (width, height) of the corner grid's bounding box in pixels.
        image_size: (width, height) of the frame.
        detector: which OpenCV detector found it ("sb" or "classic").
        model: "homography" (free fit) or "pnp" (calibrated pose with ``focal_px``).
        focal_px: focal length used by the "pnp" model, else None.
    """

    h: FloatArray
    h_inv: FloatArray
    h_samples: FloatArray
    corners_px: FloatArray
    reproj_rms_px: float
    reproj_max_px: float
    square_px: float
    extent_px: tuple[float, float]
    image_size: tuple[int, int]
    detector: Literal["sb", "classic"]
    model: GroundModel = "homography"
    focal_px: float | None = None

    def to_ground(self, pts_px: ArrayLike) -> FloatArray:
        """Image pixels (N, 2) -> ground inches (N, 2). Valid only for points on the ground."""
        return apply_homography(self.h, pts_px)

    def to_image(self, pts_in: ArrayLike) -> FloatArray:
        """Ground inches (N, 2) -> image pixels (N, 2)."""
        return apply_homography(self.h_inv, pts_in)

    def ground_samples(self, pt_px: ArrayLike) -> FloatArray:
        """One pixel mapped through every Monte Carlo homography: (N_SAMPLES, 2) inches."""
        p = np.append(np.asarray(pt_px, dtype=np.float64).reshape(2), 1.0)
        hom = self.h_samples @ p
        with np.errstate(divide="ignore", invalid="ignore"):
            return hom[:, :2] / hom[:, 2:3]

    def is_below_horizon(self, pts_px: ArrayLike) -> NDArray[np.bool_]:
        """True for pixels on the ground side of the horizon (same side as the marker)."""
        p = np.asarray(pts_px, dtype=np.float64).reshape(-1, 2)
        w = np.hstack([p, np.ones((len(p), 1))]) @ self.h[2]
        ref = np.append(self.corners_px[3, 2], 1.0) @ self.h[2]
        return np.sign(w) == np.sign(ref)

    def wall_line_ground(self, half_length_in: float = 240.0) -> FloatArray:
        """The wall line ``y = 0`` as two ground points (in), extended along x."""
        return np.array([[-half_length_in, 0.0], [half_length_in, 0.0]])

    def wall_line_image(self, half_length_in: float = 120.0) -> FloatArray:
        """The wall line projected into the image (2 points, px), e.g. for drawing."""
        return self.to_image(self.wall_line_ground(half_length_in))


def _find_corners(gray: NDArray[np.uint8]) -> tuple[FloatArray, Literal["sb", "classic"]] | None:
    """Run the sector-based detector, falling back to the classic one + cornerSubPix."""
    ok, corners = cv2.findChessboardCornersSB(
        gray, PATTERN_SIZE, flags=cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_EXHAUSTIVE
    )
    if ok and corners is not None:
        return corners.reshape(-1, 2).astype(np.float64), "sb"
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_FAST_CHECK
    ok, corners = cv2.findChessboardCorners(gray, PATTERN_SIZE, flags=flags)
    if not ok or corners is None:
        return None
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.01)
    corners = cv2.cornerSubPix(gray, corners.astype(np.float32), (5, 5), (-1, -1), crit)
    return corners.reshape(-1, 2).astype(np.float64), "classic"


def _orient(corners: FloatArray) -> FloatArray:
    """Reshape OpenCV's corner list to (7, 5, 2) with row 0 at the wall, column 0 at left.

    OpenCV returns the (5, 7) pattern row by row (5 corners per row), but the starting corner
    can be any end. The wall row is the end of the long axis that is higher in the image
    (farther from the camera, see the module docstring); x then increases to image right.
    """
    nx, ny = PATTERN_SIZE
    grid = corners.reshape(ny, nx, 2)
    if grid[-1, :, 1].mean() < grid[0, :, 1].mean():
        grid = grid[::-1]
    if grid[:, -1, 0].mean() < grid[:, 0, 0].mean():
        grid = grid[:, ::-1]
    return np.ascontiguousarray(grid)


def _camera_matrix(focal_px: float, image_size: tuple[int, int]) -> FloatArray:
    w, h = image_size
    return np.array([[focal_px, 0, (w - 1) / 2], [0, focal_px, (h - 1) / 2], [0, 0, 1.0]])


def _normalize(h: FloatArray) -> FloatArray:
    return h / h[2, 2]


class _Fitter:
    """Fits image->ground homographies for one model; reused for Monte Carlo refits."""

    def __init__(
        self, model: GroundModel, image_size: tuple[int, int], focal_px: float | None
    ) -> None:
        self.model = model
        self.image_size = image_size
        self.focal_px = focal_px
        obj = marker_object_points().reshape(-1, 2)
        self.obj2 = obj
        self.obj3 = np.column_stack([obj, np.zeros(len(obj))])
        self.guess: tuple[FloatArray, FloatArray] | None = None

    def fit(self, img_pts: FloatArray, focal_px: float | None = None) -> FloatArray | None:
        if self.model == "homography":
            h, _ = cv2.findHomography(img_pts, self.obj2, 0)
            return None if h is None or not np.isfinite(h).all() else _normalize(h)
        k = _camera_matrix(focal_px or self.focal_px or 1.0, self.image_size)
        pts = img_pts.reshape(-1, 1, 2)
        if self.guess is None:
            ok, rv, tv = cv2.solvePnP(self.obj3, pts, k, None, flags=cv2.SOLVEPNP_IPPE)
            if not ok:
                return None
        else:
            rv, tv = (g.copy() for g in self.guess)
        ok, rv, tv = cv2.solvePnP(self.obj3, pts, k, None, rv, tv, True, cv2.SOLVEPNP_ITERATIVE)
        if not ok:
            return None
        if self.guess is None:
            self.guess = (rv, tv)
        r, _ = cv2.Rodrigues(rv)
        g2i = k @ np.column_stack([r[:, 0], r[:, 1], tv.ravel()])
        try:
            return _normalize(np.linalg.inv(g2i))
        except np.linalg.LinAlgError:
            return None


def _build_pose(
    grid: FloatArray,
    image_size: tuple[int, int],
    detector: Literal["sb", "classic"],
    focal_px: float | None = None,
    focal_std_px: float = 0.0,
) -> MarkerPose | None:
    model: GroundModel = "pnp" if focal_px else "homography"
    fitter = _Fitter(model, image_size, focal_px)
    img_pts = grid.reshape(-1, 2)
    h = fitter.fit(img_pts)
    if h is None:
        return None
    try:
        h_inv = _normalize(np.linalg.inv(h))
    except np.linalg.LinAlgError:
        return None
    err = np.linalg.norm(apply_homography(h_inv, fitter.obj2) - img_pts, axis=1)
    rms = float(np.sqrt(np.mean(err**2)))

    outline = np.array([grid[0, 0], grid[0, -1], grid[-1, -1], grid[-1, 0]], np.float32)
    n_squares = (PATTERN_SIZE[0] - 1) * (PATTERN_SIZE[1] - 1)
    square_px = math.sqrt(abs(cv2.contourArea(outline)) / n_squares) / SQUARE_IN
    if rms > max(MAX_REPROJ_RMS_PX, MAX_REPROJ_RMS_REL * square_px):
        return None

    # Monte Carlo: jitter corners by the observed noise (with a floor) and refit.
    dof = 8 if model == "homography" else 6
    sigma = max(rms * math.sqrt(len(err) * 2 / max(len(err) * 2 - dof, 1)), CORNER_SIGMA_FLOOR_PX)
    rng = np.random.default_rng(_SEED)
    samples = []
    for _ in range(N_SAMPLES):
        f = focal_px
        if focal_px and focal_std_px > 0:
            f = focal_px + rng.normal(0, focal_std_px)
        hs = fitter.fit(img_pts + rng.normal(0, sigma, img_pts.shape), f)
        if hs is not None:
            samples.append(hs)
    if len(samples) < N_SAMPLES // 2:
        return None

    lo, hi = img_pts.min(axis=0), img_pts.max(axis=0)
    return MarkerPose(
        h=h,
        h_inv=h_inv,
        h_samples=np.stack(samples),
        corners_px=grid,
        reproj_rms_px=rms,
        reproj_max_px=float(err.max()),
        square_px=float(square_px),
        extent_px=(float(hi[0] - lo[0]), float(hi[1] - lo[1])),
        image_size=image_size,
        detector=detector,
        model=model,
        focal_px=float(focal_px) if focal_px else None,
    )


def detect_marker(
    frame_bgr: NDArray[np.uint8], focal_px: float | None = None, focal_std_px: float = 0.0
) -> MarkerPose | None:
    """Find the scale marker in a BGR (or grayscale) frame and solve its ground homography.

    Args:
        frame_bgr: the frame, BGR uint8 (grayscale also accepted).
        focal_px: camera focal length in pixels, if known: switches to the calibrated "pnp"
            ground model. Leave None for a free homography.
        focal_std_px: uncertainty of ``focal_px``, sampled into ``h_samples``.

    Returns None when the full 5 x 7 inner-corner grid is not found (partly hidden, too
    small, blurred, or not in view). Only frames with a complete grid are trusted.
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY) if frame_bgr.ndim == 3 else frame_bgr
    found = _find_corners(gray)
    if found is None:
        return None
    raw, detector = found
    hgt, wid = gray.shape[:2]
    return _build_pose(_orient(raw), (int(wid), int(hgt)), detector, focal_px, focal_std_px)


def scale_pose(pose: MarkerPose, k: float) -> MarkerPose:
    """The same marker in an image scaled by ``k`` (e.g. detected at full resolution, used on
    a smaller copy of the frame): pixel quantities scale by k, ground inches don't."""
    s = np.diag([k, k, 1.0])
    s_inv = np.diag([1 / k, 1 / k, 1.0])
    w, h = pose.image_size
    return dataclasses.replace(
        pose,
        h=_normalize(pose.h @ s_inv),
        h_inv=_normalize(s @ pose.h_inv),
        h_samples=np.stack([_normalize(m @ s_inv) for m in pose.h_samples]),
        corners_px=pose.corners_px * k,
        reproj_rms_px=pose.reproj_rms_px * k,
        reproj_max_px=pose.reproj_max_px * k,
        square_px=pose.square_px * k,
        extent_px=(pose.extent_px[0] * k, pose.extent_px[1] * k),
        image_size=(round(w * k), round(h * k)),
        focal_px=pose.focal_px * k if pose.focal_px else None,
    )


def with_focal(pose: MarkerPose, focal_px: float, focal_std_px: float = 0.0) -> MarkerPose:
    """Refit a detected pose with the calibrated "pnp" model (no re-detection)."""
    out = _build_pose(pose.corners_px, pose.image_size, pose.detector, focal_px, focal_std_px)
    return out if out is not None else pose


def estimate_focal_px(
    poses: Iterable[MarkerPose | None], min_views: int = 2
) -> tuple[float, float] | None:
    """Estimate the camera focal length (px) from several marker views of the same video.

    Runs a camera calibration over the detected corner grids with the principal point fixed
    at the image centre, square pixels and no lens distortion; only the focal length and
    per-view poses are free. Returns ``(focal_px, std_px)``, or None when there are too few
    views or the estimate is too uncertain (std > 5 %) or implausible. Views should differ
    in angle; near-identical views from far away barely constrain the focal length.
    """
    views = [p for p in poses if p is not None]
    if len(views) < min_views:
        return None
    size = views[0].image_size
    views = [p for p in views if p.image_size == size]
    if len(views) < min_views:
        return None
    obj = np.column_stack(
        [marker_object_points().reshape(-1, 2), np.zeros(PATTERN_SIZE[0] * PATTERN_SIZE[1])]
    ).astype(np.float32)
    k0 = _camera_matrix(0.8 * size[0], size)
    flags = (
        cv2.CALIB_USE_INTRINSIC_GUESS
        | cv2.CALIB_FIX_PRINCIPAL_POINT
        | cv2.CALIB_FIX_ASPECT_RATIO
        | cv2.CALIB_ZERO_TANGENT_DIST
        | cv2.CALIB_FIX_K1
        | cv2.CALIB_FIX_K2
        | cv2.CALIB_FIX_K3
    )
    try:
        res = cv2.calibrateCameraExtended(
            [obj] * len(views),
            [p.corners_px.reshape(-1, 1, 2).astype(np.float32) for p in views],
            size,
            k0,
            np.zeros(5),
            flags=flags,
        )
    except cv2.error:
        return None
    k, std_intr = res[1], res[5].ravel()
    # With a fixed aspect ratio OpenCV reports the focal std in the fx or fy slot.
    f, f_std = float(k[0, 0]), float(max(std_intr[0], std_intr[1]))
    if not (0.3 * size[0] < f < 3.0 * size[0]) or not math.isfinite(f_std):
        return None
    if f_std > FOCAL_MAX_REL_STD * f:
        return None
    return f, f_std
