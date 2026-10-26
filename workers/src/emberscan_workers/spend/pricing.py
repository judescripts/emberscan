"""Meta Model API price table and cost functions.

The API returns usage but no cost, so cost is computed here. Prices from
https://dev.meta.ai/docs/pricing-rate-limits (see docs/model-integration-notes.md).
Update PRICES_CHECKED_ON whenever the table changes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

PRICES_CHECKED_ON = "2026-10-26"


@dataclass(frozen=True)
class TokenPrice:
    """USD per 1M tokens."""

    input: float
    cached_input: float
    output: float


_STANDARD = TokenPrice(input=1.25, cached_input=0.15, output=4.25)
_CONTRIBUTOR = TokenPrice(input=0.10, cached_input=0.002, output=0.20)

TOKEN_PRICES: dict[str, TokenPrice] = {
    "muse-spark-1.3": _STANDARD,
    "muse-spark-1.3-contributor": _CONTRIBUTOR,
    "muse-spark-1.2": _STANDARD,
    "muse-spark-1.2-contributor": _CONTRIBUTOR,
    "muse-spark-1.1": _STANDARD,
    "muse-wonder-1.0": TokenPrice(input=4.00, cached_input=0.20, output=20.00),
    # Open-weight path (Baseten / Modal / Fireworks list the same serverless price).
    "muse-spark-open": _STANDARD,
}

SAM_USD_PER_1K_FRAMES = 0.20
SAM_MIN_FRAMES_PER_VIDEO_REQUEST = 50
SAM_USD_PER_1K_IMAGES = 2.50
VOICE_USD_PER_HOUR = 0.18
IMAGE_USD_EACH = 0.01


def token_cost(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
    """Cost of a token-billed call. `input_tokens` includes cached tokens; `output_tokens`
    includes reasoning tokens (as reported by the API's `usage`)."""
    try:
        p = TOKEN_PRICES[model]
    except KeyError as e:
        raise KeyError(f"no price for model {model!r}; add it to TOKEN_PRICES") from e
    if min(input_tokens, output_tokens, cached_tokens) < 0 or cached_tokens > input_tokens:
        raise ValueError("token counts must be >= 0 and cached_tokens <= input_tokens")
    uncached = input_tokens - cached_tokens
    return (uncached * p.input + cached_tokens * p.cached_input + output_tokens * p.output) / 1e6


def sam_video_cost(frames: int, requests: int = 1) -> float:
    """SAM 3.1 video segmentation. Each request bills at least 50 frames.
    `frames` is the frame count of one request's video; `requests` is how many
    requests (one per text concept) send that same video."""
    if frames < 0 or requests < 0:
        raise ValueError("frames and requests must be >= 0")
    billed = max(frames, SAM_MIN_FRAMES_PER_VIDEO_REQUEST) if requests else 0
    return billed * requests * SAM_USD_PER_1K_FRAMES / 1000


def voice_cost(seconds: float) -> float:
    """Muse Voice Transcribe, billed per whole second (rounded down)."""
    if seconds < 0:
        raise ValueError("seconds must be >= 0")
    return math.floor(seconds) * VOICE_USD_PER_HOUR / 3600


def image_cost(images: int) -> float:
    """Muse Image, flat per returned image."""
    if images < 0:
        raise ValueError("images must be >= 0")
    return images * IMAGE_USD_EACH
