"""Thin, typed wrappers around ffmpeg / ffprobe.

Pipeline order (ADR 0002): probe -> normalize (H.264 MP4, rotation applied, 720p) ->
extract_frames (fixed rate, with timestamps) and extract_audio (16 kHz mono WAV for
Muse Voice Transcribe). Normalizing first keeps frame indices stable across stages.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

MAX_DURATION_S = 5 * 60  # upload limit (ADR 0002)


class MediaError(RuntimeError):
    """A video couldn't be read or processed."""


@dataclass(frozen=True)
class VideoInfo:
    duration_s: float
    width: int
    height: int
    fps: float
    rotation: int
    has_audio: bool
    codec: str

    @property
    def frame_count(self) -> int:
        return round(self.duration_s * self.fps)


@dataclass(frozen=True)
class FrameRef:
    index: int
    timestamp_ms: int
    path: Path


def _bin(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise MediaError(f"{name} not found on PATH")
    return path


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise MediaError(f"{Path(args[0]).name} failed: {proc.stderr.strip()[-500:]}")
    return proc


def probe(video: Path) -> VideoInfo:
    out = _run([
        _bin("ffprobe"), "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", str(video),
    ]).stdout
    data = json.loads(out)
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if v is None:
        raise MediaError(f"no video stream in {video.name}")
    rotation = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = int(sd["rotation"]) % 360
    if "rotate" in (v.get("tags") or {}):
        rotation = int(v["tags"]["rotate"]) % 360
    duration = float(v.get("duration") or data.get("format", {}).get("duration") or 0)
    return VideoInfo(
        duration_s=duration,
        width=int(v["width"]),
        height=int(v["height"]),
        fps=float(Fraction(v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1")),
        rotation=rotation,
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
        codec=v.get("codec_name", ""),
    )


def normalize(
    src: Path,
    dst: Path,
    height: int = 720,
    max_duration_s: float = MAX_DURATION_S,
    fps: float | None = None,
) -> VideoInfo:
    """Re-encode to H.264 MP4 at `height` px with rotation baked in; keep audio as AAC.

    `fps` lowers the frame rate. SAM 3.1 bills per frame and has no stride parameter, so
    the copy sent to SAM is normalized at a low rate (e.g. 3 fps).
    """
    info = probe(src)
    if info.duration_s > max_duration_s:
        raise MediaError(f"video is {info.duration_s:.0f}s; the limit is {max_duration_s:.0f}s")
    if fps is not None and fps <= 0:
        raise ValueError("fps must be > 0")
    dst.parent.mkdir(parents=True, exist_ok=True)
    # ffmpeg auto-rotates by default; scale keeps aspect and an even width.
    vf = f"scale=-2:{height}" if fps is None else f"fps={fps},scale=-2:{height}"
    _run([
        _bin("ffmpeg"), "-v", "error", "-y", "-i", str(src),
        "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
        str(dst),
    ])
    return probe(dst)


def extract_frames(
    video: Path, out_dir: Path, fps: float = 2.0, quality: int = 3
) -> list[FrameRef]:
    """Sample frames at a fixed rate. Frame i is taken at t = i / fps seconds."""
    if fps <= 0:
        raise ValueError("fps must be > 0")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("frame_*.jpg"):
        old.unlink()
    _run([
        _bin("ffmpeg"), "-v", "error", "-y", "-i", str(video),
        "-vf", f"fps={fps}", "-q:v", str(quality), str(out_dir / "frame_%06d.jpg"),
    ])
    paths = sorted(out_dir.glob("frame_*.jpg"))
    return [FrameRef(i, round(i * 1000 / fps), p) for i, p in enumerate(paths)]


def extract_audio(video: Path, out_wav: Path) -> Path | None:
    """16 kHz mono PCM WAV for Muse Voice Transcribe. Returns None for silent videos."""
    if not probe(video).has_audio:
        return None
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    _run([
        _bin("ffmpeg"), "-v", "error", "-y", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(out_wav),
    ])
    return out_wav
