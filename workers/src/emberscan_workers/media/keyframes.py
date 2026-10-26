"""Keyframe selection (story B2): skip blurry and near-duplicate frames, cap the count.

Used for anything that runs per frame (geometry, evidence images, Muse Image). SAM 3.1
gets the whole normalized clip instead (ADR 0002).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .ffmpeg import FrameRef

_ANALYSIS_WIDTH = 320


@dataclass(frozen=True)
class FrameScore:
    frame: FrameRef
    sharpness: float
    dhash: int


def _gray(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        im = im.convert("L")
        h = round(im.height * _ANALYSIS_WIDTH / im.width)
        im = im.resize((_ANALYSIS_WIDTH, max(h, 1)), Image.Resampling.BILINEAR)
        return np.asarray(im, dtype=np.float32)


def sharpness(gray: np.ndarray) -> float:
    """Variance of the Laplacian: low for blurry frames."""
    lap = (
        -4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    )
    return float(lap.var())


def dhash(gray: np.ndarray, size: int = 8) -> int:
    """64-bit difference hash: similar images have hashes a few bits apart."""
    small = np.asarray(
        Image.fromarray(gray.astype(np.uint8)).resize((size + 1, size), Image.Resampling.BILINEAR),
        dtype=np.int16,
    )
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def score(frames: Sequence[FrameRef]) -> list[FrameScore]:
    out = []
    for f in frames:
        g = _gray(f.path)
        out.append(FrameScore(f, sharpness(g), dhash(g)))
    return out


def select_keyframes(
    frames: Sequence[FrameRef],
    max_frames: int = 150,
    blur_ratio: float = 0.35,
    dup_bits: int = 5,
) -> list[FrameRef]:
    """Keep sharp, non-duplicate frames in time order, at most `max_frames`.

    - Blurry: sharpness below `blur_ratio` x the median sharpness of the clip.
    - Duplicate: dHash within `dup_bits` bits of the last kept frame.
    - Cap: evenly spaced over what's left, so the whole walkaround stays covered.
    """
    if max_frames < 1:
        raise ValueError("max_frames must be >= 1")
    scored = score(frames)
    if not scored:
        return []
    median = float(np.median([s.sharpness for s in scored]))
    sharp = [s for s in scored if s.sharpness >= blur_ratio * median] or scored

    kept: list[FrameScore] = []
    for s in sharp:
        if kept and hamming(s.dhash, kept[-1].dhash) <= dup_bits:
            continue
        kept.append(s)

    if len(kept) > max_frames:
        idx = np.linspace(0, len(kept) - 1, max_frames).round().astype(int)
        kept = [kept[i] for i in sorted(set(idx.tolist()))]
    return [s.frame for s in kept]
