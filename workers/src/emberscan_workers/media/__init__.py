"""Video and audio handling with ffmpeg (story B1, ADR 0002)."""

from .ffmpeg import (
    ClipSpan,
    FrameRef,
    MediaError,
    VideoInfo,
    extract_audio,
    extract_frames,
    join_clips,
    normalize,
    probe,
)

__all__ = [
    "ClipSpan",
    "FrameRef",
    "MediaError",
    "VideoInfo",
    "extract_audio",
    "extract_frames",
    "join_clips",
    "normalize",
    "probe",
]
