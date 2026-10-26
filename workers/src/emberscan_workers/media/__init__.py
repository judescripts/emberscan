"""Video and audio handling with ffmpeg (story B1, ADR 0002)."""

from .ffmpeg import (
    FrameRef,
    MediaError,
    VideoInfo,
    extract_audio,
    extract_frames,
    normalize,
    probe,
)

__all__ = [
    "FrameRef",
    "MediaError",
    "VideoInfo",
    "extract_audio",
    "extract_frames",
    "normalize",
    "probe",
]
