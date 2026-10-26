import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from emberscan_workers.media import MediaError, extract_audio, extract_frames, normalize, probe

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _make_clip(path: Path, seconds: float = 3, audio: bool = True, size: str = "640x360") -> Path:
    """Synthetic test clip (no real footage in tests)."""
    args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=30"]
    if audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100"]
    args += ["-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    args += ["-c:a", "aac"] if audio else []
    args += [str(path)]
    subprocess.run(args, check=True)
    return path


@pytest.fixture
def clip(tmp_path: Path) -> Path:
    return _make_clip(tmp_path / "walk.mp4")


def test_probe(clip: Path) -> None:
    info = probe(clip)
    assert info.width == 640 and info.height == 360
    assert info.fps == pytest.approx(30)
    assert info.duration_s == pytest.approx(3, abs=0.1)
    assert info.has_audio
    assert info.frame_count == pytest.approx(90, abs=3)


def test_normalize_to_720p(clip: Path, tmp_path: Path) -> None:
    out = normalize(clip, tmp_path / "norm.mp4")
    assert out.height == 720 and out.width == 1280
    assert out.codec == "h264"


def test_normalize_rejects_long_videos(clip: Path, tmp_path: Path) -> None:
    with pytest.raises(MediaError, match="limit"):
        normalize(clip, tmp_path / "norm.mp4", max_duration_s=1)


def test_extract_frames_with_timestamps(clip: Path, tmp_path: Path) -> None:
    frames = extract_frames(clip, tmp_path / "frames", fps=2)
    assert len(frames) in (6, 7)  # 3 s at 2 fps (ffmpeg may emit a final frame)
    assert [f.timestamp_ms for f in frames[:3]] == [0, 500, 1000]
    assert all(f.path.exists() for f in frames)


def test_extract_frames_clears_old_output(clip: Path, tmp_path: Path) -> None:
    out = tmp_path / "frames"
    extract_frames(clip, out, fps=4)
    frames = extract_frames(clip, out, fps=1)
    assert len(list(out.glob("frame_*.jpg"))) == len(frames)


def test_extract_audio_wav_16k_mono(clip: Path, tmp_path: Path) -> None:
    wav = extract_audio(clip, tmp_path / "audio.wav")
    assert wav is not None
    with wave.open(str(wav)) as w:
        assert w.getnchannels() == 1
        assert w.getframerate() == 16000
        assert w.getnframes() / w.getframerate() == pytest.approx(3, abs=0.1)


def test_silent_video_has_no_audio(tmp_path: Path) -> None:
    silent = _make_clip(tmp_path / "silent.mp4", audio=False)
    assert extract_audio(silent, tmp_path / "a.wav") is None


def test_not_a_video(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mp4"
    bad.write_text("not a video")
    with pytest.raises(MediaError):
        probe(bad)
