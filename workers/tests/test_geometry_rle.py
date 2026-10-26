"""COCO compressed RLE decoding and placing SAM's box-local masks into frames."""

from __future__ import annotations

import numpy as np
import pytest

from emberscan_workers.geometry import RleError, decode_rle, mask_to_frame
from emberscan_workers.geometry.rle import box_local_mask, decode_counts_string, mask_scale


def encode_rle(mask: np.ndarray) -> dict:
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


@pytest.mark.parametrize(
    ("counts", "runs"),
    [
        ("9", [9]),  # 3x3 all zero
        ("324", [3, 2, 4]),
        ("11104", [1, 1, 1, 1, 5]),  # 4th run stored as delta 0, 5th as delta 4
        ("152L", [1, 5, 2, 1]),  # 4th run is delta -4: sign bit set
        ("0Q11", [0, 33, 1]),  # 33 needs two 5-bit groups: "Q1"
    ],
)
def test_known_vectors(counts: str, runs: list[int]) -> None:
    assert decode_counts_string(counts) == runs


def test_column_major_order() -> None:
    m = decode_rle({"size": [3, 3], "counts": "324"})
    expected = np.zeros((3, 3), bool)
    expected[0:2, 1] = True  # second column, first two rows
    assert (m == expected).all()


def test_uncompressed_counts_and_leading_one() -> None:
    m = decode_rle({"size": [2, 2], "counts": [0, 2, 2]})
    assert m.tolist() == [[True, False], [True, False]]


@pytest.mark.parametrize("shape", [(1, 1), (7, 3), (40, 55), (128, 96)])
def test_round_trip_random(shape: tuple[int, int]) -> None:
    rng = np.random.default_rng(sum(shape))
    for density in (0.0, 0.03, 0.5, 1.0):
        m = rng.random(shape) < density
        rle = encode_rle(m)
        assert (decode_rle(rle) == m).all()


def test_round_trip_large_runs() -> None:
    m = np.zeros((300, 500), bool)
    m[50:250, 100:400] = True  # long runs exercise multi-group values and big deltas
    m[10, 10] = True
    assert (decode_rle(encode_rle(m)) == m).all()


def test_malformed() -> None:
    with pytest.raises(RleError):
        decode_rle({"size": [3, 3], "counts": "32"})  # sums to 5, not 9
    with pytest.raises(RleError):
        decode_rle({"size": [3, 3], "counts": "3 4"})  # invalid character
    with pytest.raises(RleError):
        decode_rle({"counts": "9"})
    with pytest.raises(RleError):
        decode_rle({"size": [1, 1], "counts": "Q"})  # continuation bit, then nothing


def test_mask_to_frame_scales_box_local_mask() -> None:
    small = np.zeros((4, 5), bool)
    small[1:3, 1:4] = True  # 3 wide, 2 tall in mask px
    md = {"rle": encode_rle(small), "bounds": [100, 50, 110, 58]}  # box 10 x 8 -> 2x scale
    assert mask_scale(md) == (2.0, 2.0)
    local, off = box_local_mask(md)
    assert local.shape == (8, 10) and off == (100, 50)
    frame = mask_to_frame(md, 200, 100)
    ys, xs = np.nonzero(frame)
    assert (xs.min(), xs.max(), ys.min(), ys.max()) == (102, 107, 52, 55)
    assert frame.sum() == 6 * 4


def test_mask_to_frame_clips_to_frame() -> None:
    md = {"rle": encode_rle(np.ones((4, 4), bool)), "bounds": [-2, -2, 2, 2]}
    frame = mask_to_frame(md, 3, 3)
    assert frame.sum() == 4 and frame[:2, :2].all()
    md = {"rle": encode_rle(np.ones((2, 2), bool)), "bounds": [10, 10, 12, 12]}
    assert mask_to_frame(md, 5, 5).sum() == 0
