"""Minimal async client for the Meta Model API (https://api.meta.ai/v1).

Only what the pipeline needs: file upload/delete and streamed Responses. The key comes
from META_API_KEY and is never logged.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.meta.ai/v1"


class MetaAPIError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"Meta API {status}: {message}")
        self.status = status


class MetaClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 300.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        key = api_key or os.environ.get("META_API_KEY", "")
        if not key:
            raise MetaAPIError(0, "META_API_KEY is not set")
        base = (base_url or os.environ.get("META_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=base,
            headers={"Authorization": f"Bearer {key}"},
            timeout=httpx.Timeout(timeout_s, connect=20.0),
            transport=transport,
        )

    async def __aenter__(self) -> MetaClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    @staticmethod
    def _raise_for(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            raise MetaAPIError(resp.status_code, resp.text[:500])

    async def upload_file(self, path: Path, purpose: str = "user_data") -> str:
        with path.open("rb") as f:
            resp = await self._http.post(
                "/files", data={"purpose": purpose}, files={"file": (path.name, f, "video/mp4")}
            )
        self._raise_for(resp)
        return str(resp.json()["id"])

    async def delete_file(self, file_id: str) -> None:
        resp = await self._http.delete(f"/files/{file_id}")
        if resp.status_code not in (200, 204, 404):
            self._raise_for(resp)

    async def create_response(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /responses (non-streaming) and return the response object."""
        resp = await self._http.post("/responses", json={**body, "stream": False})
        self._raise_for(resp)
        return resp.json()

    async def edit_image(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /images/edits (Muse Image, JSON body with data-URL images)."""
        resp = await self._http.post("/images/edits", json=body)
        self._raise_for(resp)
        return resp.json()

    async def transcribe_wav(self, wav: Path, request: dict[str, Any]) -> dict[str, Any]:
        """POST /asr/transcribe (multipart: JSON `request` part + WAV `audio` part)."""
        with wav.open("rb") as f:
            resp = await self._http.post(
                "/asr/transcribe",
                files={
                    "request": (None, json.dumps(request), "application/json"),
                    "audio": (wav.name, f, "audio/wav"),
                },
            )
        self._raise_for(resp)
        return resp.json()

    async def stream_response(self, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """POST /responses with stream=true and yield each server-sent event as a dict."""
        payload = {**body, "stream": True}
        async with self._http.stream(
            "POST", "/responses", json=payload, headers={"Accept": "text/event-stream"}
        ) as resp:
            if resp.status_code >= 400:
                await resp.aread()
                self._raise_for(resp)
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                yield json.loads(data)
