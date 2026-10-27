"""Muse Spark Open on Baseten (story D4; ADR 0006).

Baseten serves Meta's open-weight model behind an OpenAI-compatible Chat Completions API.
Only what the agent needs: one non-streamed completion with tools. The key comes from
BASETEN_API_KEY and is never logged.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://inference.baseten.co/v1"
# The hackathon key only works with this model id (Baseten email, Oct 26).
DEFAULT_MODEL = "meta-models/muse-spark-open-1026"
PRICE_KEY = "muse-spark-open"  # TOKEN_PRICES entry for spend tracking
LABEL = "Muse Spark Open (open weights, on Baseten)"


class OpenWeightError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"Baseten {status}: {message}")
        self.status = status


def open_weight_enabled() -> bool:
    """The open-weight path runs when a key is set, unless AGENT_PROVIDER=meta."""
    return bool(os.environ.get("BASETEN_API_KEY")) and os.environ.get(
        "AGENT_PROVIDER", "baseten"
    ).lower() not in ("meta", "hosted")


class OpenWeightClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = 180.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        key = api_key or os.environ.get("BASETEN_API_KEY", "")
        if not key:
            raise OpenWeightError(0, "BASETEN_API_KEY is not set")
        base = (base_url or os.environ.get("BASETEN_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("BASETEN_MODEL_ID") or DEFAULT_MODEL
        self._http = httpx.AsyncClient(
            base_url=base,
            headers={"Authorization": f"Bearer {key}"},
            timeout=httpx.Timeout(timeout_s, connect=20.0),
            transport=transport,
        )

    async def __aenter__(self) -> OpenWeightClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def chat(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /chat/completions (non-streaming) and return the completion object."""
        resp = await self._http.post("/chat/completions", json={"model": self.model, **body})
        if resp.status_code >= 400:
            raise OpenWeightError(resp.status_code, resp.text[:500])
        return resp.json()
