"""Narration with Muse Voice Transcribe (story B4).

The resident can narrate while filming ("north side, mulch bed against the wall"). Turns
carry start/end times, so each narration turn maps to a range of video frames and can be
attached to the hazards seen at that moment. Narration adds context; it never overrides
measurements or rule results.
"""

from __future__ import annotations

import time
import wave
from dataclasses import dataclass
from pathlib import Path

from ..spend import SpendLedger, voice_cost
from .client import MetaClient

MODEL = "muse-voice-transcribe-1.0"
KEYWORDS = [
    "defensible space",
    "Zone 0",
    "Zone 1",
    "Zone 2",
    "mulch",
    "bark mulch",
    "juniper",
    "woodpile",
    "firewood",
    "gutter",
    "eave",
    "vent",
    "propane",
    "HOA",
    "unit",
]
MAX_SECONDS = 10 * 60  # API limit per file


@dataclass(frozen=True)
class Turn:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class Transcript:
    turns: list[Turn]
    text: str
    duration_ms: int

    def near(self, start_ms: int, end_ms: int, pad_ms: int = 1500) -> list[Turn]:
        """Turns overlapping [start_ms - pad, end_ms + pad]."""
        return [
            t for t in self.turns if t.end_ms >= start_ms - pad_ms and t.start_ms <= end_ms + pad_ms
        ]


def wav_seconds(wav: Path) -> float:
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


async def transcribe(client: MetaClient, ledger: SpendLedger, wav: Path) -> Transcript:
    seconds = wav_seconds(wav)
    if seconds > MAX_SECONDS:
        raise ValueError(f"narration is {seconds:.0f}s; the limit is {MAX_SECONDS}s")
    ledger.check("narration", voice_cost(seconds))
    t0 = time.monotonic()
    data = await client.transcribe_wav(
        wav,
        {"model": MODEL, "mode": "ENDPOINTING", "audioEncoding": "WAV", "keywords": KEYWORDS},
    )
    duration_ms = int(data.get("audioDurationMs") or seconds * 1000)
    ledger.record(
        "narration",
        MODEL,
        voice_cost(duration_ms / 1000),
        {"seconds": duration_ms // 1000},
        time.monotonic() - t0,
    )
    turns = [
        Turn(int(t["startMs"]), int(t["endMs"]), str(t.get("transcript", "")).strip())
        for t in data.get("turns") or []
        if str(t.get("transcript", "")).strip()
    ]
    return Transcript(turns, str(data.get("transcript", "")).strip(), duration_ms)
