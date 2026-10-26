# Contracts between the web app and the pipeline

## Report JSON

The pipeline produces one `Report` per scan (`workers/src/emberscan_workers/contracts.py`). The web app renders it. [`report.sample.json`](report.sample.json) is a sample for building the UI (illustrative values).

## Worker HTTP API (FastAPI, `workers/src/emberscan_workers/service.py`)

Base URL from `WORKER_URL` (default `http://localhost:8000`). Bearer `WORKER_TOKEN` when set.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| `POST` | `/scans` | multipart: `video` (file), `building_label`, `eave_depth_ft` (optional number), `include_proposed` (bool, default true), `concepts` (optional comma list) | `{ "scan_id": "..." }` (202) |
| `GET` | `/scans/{scan_id}` | — | `{ scan_id, status: "queued" \| "processing" \| "done" \| "failed", stage, progress (0–1), stages: [{name, status, detail}], error?, report? }` |
| `GET` | `/scans/{scan_id}/files/{path}` | — | Evidence images (annotated frames) referenced by `Evidence.image_path` |
| `GET` | `/health` | — | `{ ok: true }` |

Stages, in order: `upload`, `normalize`, `frames`, `segment` (SAM 3.1, one concept per request, run concurrently), `measure` (scale marker + ground plane), `rules`, `narration` (Voice Transcribe, if audio), `agent` (Muse Spark), `report`.
