from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageFilter

from emberscan_workers.media import FrameRef
from emberscan_workers.media.keyframes import dhash, hamming, select_keyframes, sharpness


def _scene(seed: int) -> Image.Image:
    """A distinct, detailed synthetic scene per seed (random blocks + checker)."""
    rng = np.random.default_rng(seed)
    blocks = rng.integers(0, 255, size=(18, 32), dtype=np.uint8)
    img = Image.fromarray(blocks).resize((640, 360), Image.Resampling.NEAREST)
    checker = (np.indices((360, 640)).sum(axis=0) // 20 % 2 * 255).astype(np.uint8)
    return Image.fromarray(((np.asarray(img, dtype=np.uint16) + checker) // 2).astype(np.uint8))


def _save(tmp: Path, i: int, img: Image.Image) -> FrameRef:
    p = tmp / f"frame_{i:06d}.jpg"
    img.convert("RGB").save(p, quality=92)
    return FrameRef(i, i * 500, p)


def _gray(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L"), dtype=np.float32)


def test_blur_lowers_sharpness() -> None:
    img = _scene(1)
    assert sharpness(_gray(img)) > 5 * sharpness(_gray(img.filter(ImageFilter.GaussianBlur(6))))


def test_dhash_similar_vs_different() -> None:
    a, b = _scene(1), _scene(2)
    nudged = Image.fromarray(np.clip(np.asarray(a, dtype=np.int16) + 6, 0, 255).astype(np.uint8))
    assert hamming(dhash(_gray(a)), dhash(_gray(nudged))) <= 5
    assert hamming(dhash(_gray(a)), dhash(_gray(b))) > 10


def test_drops_blurry_and_duplicate_frames(tmp_path: Path) -> None:
    frames = [
        _save(tmp_path, 0, _scene(1)),
        _save(tmp_path, 1, _scene(1)),  # duplicate of 0
        _save(tmp_path, 2, _scene(2).filter(ImageFilter.GaussianBlur(8))),  # blurry
        _save(tmp_path, 3, _scene(3)),
        _save(tmp_path, 4, _scene(4)),
    ]
    kept = [f.index for f in select_keyframes(frames)]
    assert kept == [0, 3, 4]


def test_cap_keeps_coverage_in_time_order(tmp_path: Path) -> None:
    frames = [_save(tmp_path, i, _scene(100 + i)) for i in range(20)]
    kept = select_keyframes(frames, max_frames=5)
    assert len(kept) == 5
    assert kept[0].index == 0 and kept[-1].index == 19
    assert [f.index for f in kept] == sorted(f.index for f in kept)


def test_empty_and_invalid() -> None:
    assert select_keyframes([]) == []
    with pytest.raises(ValueError):
        select_keyframes([], max_frames=0)
