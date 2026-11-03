# Contracts between the web app and the pipeline

## Report JSON

The pipeline produces one `Report` per scan (`workers/src/emberscan_workers/contracts.py`). The web app renders it. [`report.sample.json`](report.sample.json) is a sample for building the UI (illustrative values).

## Worker HTTP API (FastAPI, `workers/src/emberscan_workers/service.py`)

Base URL from `WORKER_URL` (default `http://localhost:8000`). Bearer `WORKER_TOKEN` when set.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| `PUT` | `/uploads/{upload_id}/{clip}?offset=N` | raw bytes: one slice of clip `clip` (the web app sends 4 MB slices); `offset` must equal the bytes already stored, so a retried slice is never written twice | `{ "size": N }`; 409 `{ "error": "offset", "have": N }` on a mismatch |
| `POST` | `/uploads/{upload_id}/scan` | JSON: clip `names` in order, plus the same scan options as `/scans` | `{ "scan_id": "..." }` (202) |
| `POST` | `/scans` | multipart: `video` (one or more walkaround files, joined in order; up to 40 files), `building_label`, `eave_depth_ft` (optional number), `include_proposed` (bool, default true), `concepts` (optional comma list), `clip_sides` (optional), `community_type` (optional). Used locally; the deployment uses the slice upload above | `{ "scan_id": "..." }` (202) |
| `POST` | `/research` | JSON `{ "address": "..." }` | Cited building note (Muse Spark + public map data), synchronous |
| `GET` | `/budget` | | Spend so far, caps, scans left today |
| `GET` | `/scans/{scan_id}` | — | `{ scan_id, status: "queued" \| "processing" \| "done" \| "failed", stage, progress (0–1), stages: [{name, status, detail}], error?, report? }` |
| `GET` | `/scans/{scan_id}/files/{path}` | — | Evidence images (annotated frames) referenced by `Evidence.image_path` |
| `GET` | `/health` | — | `{ ok: true }` |

Stages, in order: `upload`, `normalize`, `frames`, `narration` (Voice Transcribe, if audio; runs alongside segment), `segment` (SAM 3.1, one concept per request, run concurrently), `privacy` (blur people and plates), `measure` (scale marker + ground plane), `rules`, `agent` (Muse Spark Open, hosted Muse Spark fallback; then Muse Image previews), `report`.
