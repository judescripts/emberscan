"""SAM 3.1 parsing, replayed from a recorded response (no API calls in tests).

Fixture: one real `sam-3.1` response for the concept "bark mulch" on an 8-second,
3 fps AI-generated example clip (24 frames), recorded Oct 26, 2026.
"""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from emberscan_workers.meta import MetaClient
from emberscan_workers.meta.sam import build_request, collect_tracks, segment_video
from emberscan_workers.spend import SpendLedger, SpendLimitExceeded

FIXTURE = Path(__file__).parent / "fixtures" / "sam_bark_mulch_events.json"


def _events() -> list[dict]:
    return json.loads(FIXTURE.read_text())


async def _aiter(items):
    for x in items:
        yield x


def test_build_request_shape() -> None:
    body = build_request("  bark mulch ", "file-1")
    content = body["input"][0]["content"]
    assert body["model"] == "sam-3.1"
    assert content[0] == {"type": "input_text", "text": "bark mulch"}
    assert content[1] == {"type": "input_video", "file_id": "file-1"}
    assert body["metadata"] == {"mask_encoding": "one_bit", "include_confidence": "true"}
    with pytest.raises(ValueError):
        build_request("  ", "file-1")


def test_recorded_response_tracks_one_object_across_all_frames() -> None:
    tracks, complete = asyncio.run(collect_tracks(_aiter(_events()), "bark mulch"))
    assert complete
    assert list(tracks) == ["0"]
    t = tracks["0"]
    assert t.frames == list(range(24))
    assert 0.5 < (t.mean_confidence or 0) <= 1
    m = t.masks[0]
    left, top, right, bottom = m["bounds"]
    assert (left, top, right, bottom) == (0, 272, 1280, 720)
    assert m["rle"]["size"][0] > 0 and isinstance(m["rle"]["counts"], str)


class _FakeAPI:
    """Serves upload, SSE replay of the fixture, and delete through an httpx MockTransport."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(f"{request.method} {request.url.path}")
        if request.method == "POST" and request.url.path.endswith("/files"):
            return httpx.Response(200, json={"id": "file-test", "status": "uploaded"})
        if request.method == "DELETE":
            return httpx.Response(200, json={"deleted": True})
        body = "".join(f"data: {json.dumps(e)}\n\n" for e in _events())
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})


def test_segment_video_records_billed_frames(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    api = _FakeAPI()
    ledger = SpendLedger(run_id="t", limit_usd=1.0)

    async def run():
        async with MetaClient(api_key="test", transport=httpx.MockTransport(api.handler)) as c:
            return await segment_video(c, ledger, video, "bark mulch", frame_count=24)

    res = asyncio.run(run())
    assert res.frames_billed == 50  # usage.video_frames_processed in the recording
    assert res.cost_usd == pytest.approx(0.01)
    assert ledger.spent_usd == pytest.approx(0.01)
    assert [c.split()[0] for c in api.calls] == ["POST", "POST", "DELETE"]


def test_segment_video_refuses_over_budget(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    api = _FakeAPI()
    ledger = SpendLedger(run_id="t", limit_usd=0.005)

    async def run():
        async with MetaClient(api_key="test", transport=httpx.MockTransport(api.handler)) as c:
            await segment_video(c, ledger, video, "bark mulch", frame_count=24)

    with pytest.raises(SpendLimitExceeded):
        asyncio.run(run())
    assert api.calls == []  # nothing uploaded or billed
