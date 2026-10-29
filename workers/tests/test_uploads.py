"""Sliced uploads: PUT /uploads/{id}/{clip}?offset= then POST /uploads/{id}/scan."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from emberscan_workers import service


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(service, "UPLOADS_DIR", tmp_path / "_uploads")
    monkeypatch.delenv("WORKER_TOKEN", raising=False)
    started = []
    monkeypatch.setattr(service.BUDGET, "reserve", lambda *a, **k: None)
    monkeypatch.setattr(service, "_start", lambda *a: started.append(a) or {"scan_id": a[0]})
    c = TestClient(service.app)
    c.started = started
    return c


def test_slices_append_and_start_a_scan(client, tmp_path):
    up = str(uuid.uuid4())
    assert client.put(f"/uploads/{up}/0?offset=0", content=b"abc").json() == {"size": 3}
    assert client.put(f"/uploads/{up}/0?offset=3", content=b"def").json() == {"size": 6}
    assert client.put(f"/uploads/{up}/1?offset=0", content=b"xy").status_code == 200
    r = client.post(
        f"/uploads/{up}/scan",
        json={"names": ["north.MOV", "east.mp4"], "building_label": "B1", "clip_sides": "N,E"},
    )
    assert r.status_code == 202
    scan_id, d, walks = client.started[0][:3]
    assert [w.name for w in walks] == ["upload.mov", "upload01.mp4"]
    assert walks[0].read_bytes() == b"abcdef"
    assert d == tmp_path / scan_id
    assert not (tmp_path / "_uploads" / up).exists()


def test_wrong_offset_says_what_is_stored(client):
    up = str(uuid.uuid4())
    client.put(f"/uploads/{up}/0?offset=0", content=b"abc")
    r = client.put(f"/uploads/{up}/0?offset=0", content=b"abc")  # a retry of a slice that landed
    assert r.status_code == 409 and r.json()["have"] == 3


def test_incomplete_upload_is_refused(client):
    up = str(uuid.uuid4())
    client.put(f"/uploads/{up}/0?offset=0", content=b"abc")
    r = client.post(
        f"/uploads/{up}/scan", json={"names": ["a.mp4", "b.mp4"], "building_label": "B"}
    )
    assert r.status_code == 400 and not client.started


def test_bad_upload_id_is_rejected(client):
    assert client.put("/uploads/..%2F..%2Fx/0?offset=0", content=b"a").status_code == 404
