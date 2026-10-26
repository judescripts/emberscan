"""COCO run-length-encoded masks, and placing SAM's box-local masks into frames.

SAM returns each mask as ``{"rle": {"size": [h, w], "counts": str}, "bounds": [l, t, r, b]}``:
a COCO *compressed* RLE (the pycocotools string format) of a mask that covers only the
object's box, usually at lower resolution than the frame. Runs alternate 0, 1, 0, ... and
pixels are in column-major (Fortran) order.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

BoolArray = NDArray[np.bool_]


class RleError(ValueError):
    """The RLE is malformed or does not match its declared size."""


def decode_counts_string(counts: str) -> list[int]:
    """Decode a pycocotools compressed counts string into run lengths.

    Each run is a little-endian sequence of 5-bit groups stored as ``chr(48 + group)``,
    with bit 0x20 meaning "more groups follow" and bit 0x10 of the last group the sign.
    From the fourth run on, values are stored as deltas from the run two places back.
    """
    runs: list[int] = []
    data = counts.encode("ascii")
    p, n = 0, len(data)
    while p < n:
        x, k, more = 0, 0, True
        while more:
            if p >= n:
                raise RleError("truncated RLE counts string")
            c = data[p] - 48
            if c < 0 or c > 63:
                raise RleError(f"invalid RLE character {chr(data[p])!r}")
            x |= (c & 0x1F) << (5 * k)
            more = bool(c & 0x20)
            p += 1
            k += 1
            if not more and (c & 0x10):
                x |= -1 << (5 * k)
        if len(runs) > 2:
            x += runs[-2]
        runs.append(x)
    return runs


def decode_rle(rle: Mapping[str, Any]) -> BoolArray:
    """Decode a COCO RLE (compressed string or uncompressed int list) to a bool (h, w) array."""
    try:
        h, w = (int(v) for v in rle["size"])
        counts = rle["counts"]
    except (KeyError, TypeError, ValueError) as e:
        raise RleError(f"not a COCO RLE: {e}") from e
    if isinstance(counts, bytes):
        counts = counts.decode("ascii")
    runs = decode_counts_string(counts) if isinstance(counts, str) else [int(c) for c in counts]
    arr = np.asarray(runs, dtype=np.int64)
    if (arr < 0).any():
        raise RleError("negative run length")
    if int(arr.sum()) != h * w:
        raise RleError(f"runs sum to {int(arr.sum())}, expected {h}x{w}={h * w}")
    values = (np.arange(len(arr)) % 2).astype(bool)  # runs alternate 0, 1, 0, ...
    flat = np.repeat(values, arr)
    return flat.reshape((h, w), order="F")


def _bounds(mask_dict: Mapping[str, Any]) -> tuple[float, float, float, float]:
    b = mask_dict.get("bounds")
    if not isinstance(b, Sequence) or len(b) != 4:
        raise RleError("mask dict needs 'bounds': [left, top, right, bottom]")
    left, top, right, bottom = (float(v) for v in b)
    return left, top, right, bottom


def box_local_mask(mask_dict: Mapping[str, Any]) -> tuple[BoolArray, tuple[int, int]]:
    """Decode a SAM mask and resize it (nearest neighbour) to its box size in frame pixels.

    Returns ``(mask, (left, top))``: the mask covers frame pixels ``top:top+h, left:left+w``.
    Box edges are rounded to whole pixels.
    """
    small = decode_rle(mask_dict["rle"])
    left, top, right, bottom = _bounds(mask_dict)
    x0, y0 = int(round(left)), int(round(top))
    bw = max(1, int(round(right)) - x0)
    bh = max(1, int(round(bottom)) - y0)
    if small.shape != (bh, bw):
        small = cv2.resize(small.view(np.uint8), (bw, bh), interpolation=cv2.INTER_NEAREST)
        small = small.astype(bool)
    return small, (x0, y0)


def mask_scale(mask_dict: Mapping[str, Any]) -> tuple[float, float]:
    """Frame pixels per mask pixel, (sx, sy), for a box-local SAM mask."""
    h, w = (int(v) for v in mask_dict["rle"]["size"])
    left, top, right, bottom = _bounds(mask_dict)
    return max(right - left, 1.0) / max(w, 1), max(bottom - top, 1.0) / max(h, 1)


def mask_to_frame(mask_dict: Mapping[str, Any], frame_w: int, frame_h: int) -> BoolArray:
    """Place a box-local SAM mask into a full-frame (frame_h, frame_w) bool array.

    The mask is resized to its box with nearest-neighbour sampling and pasted at the box's
    top-left corner; parts of the box outside the frame are clipped.
    """
    local, (x0, y0) = box_local_mask(mask_dict)
    out = np.zeros((frame_h, frame_w), dtype=bool)
    bh, bw = local.shape
    fx0, fy0 = max(x0, 0), max(y0, 0)
    fx1, fy1 = min(x0 + bw, frame_w), min(y0 + bh, frame_h)
    if fx1 > fx0 and fy1 > fy0:
        out[fy0:fy1, fx0:fx1] = local[fy0 - y0 : fy1 - y0, fx0 - x0 : fx1 - x0]
    return out
