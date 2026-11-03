# ADR 0002: Video and voice pipeline

**Status:** Accepted (2026-10-26)

## Context
Users upload 1–3 minute phone videos (MOV/MP4, often HEVC), optionally narrated. Model calls drive cost, and spend is on a personal card until credits post. Facts from the model notes (Oct 26): SAM 3.1 takes MP4/MOV up to 15,000 frames, one text concept per request, stable object IDs within a request, **minimum 50 frames billed per video request**, $0.20 per 1,000 frames. Voice Transcribe takes **WAV only**, up to 10 min / 32 MB, with turn-level timestamps.

## Decision
1. **Upload** directly to object storage with a pre-signed URL; the API stores metadata only. Limit 500 MB / 5 min.
2. **Normalize** with ffmpeg: H.264 MP4 at 720p, rotation applied, so frame indices are stable.
3. **Audio:** ffmpeg extracts a mono 16 kHz WAV for Voice Transcribe when the video has an audio track.
4. **Frames:** sample at a configurable rate (default 2 fps); store JPEGs with `frame_index` and `timestamp_ms`.
5. **Keyframes:** drop blurry (variance of Laplacian) and near-duplicate (perceptual hash) frames for anything that runs per frame (geometry, evidence images). Cap 150 per walkaround.
6. **Segmentation:** send the **whole normalized clip** to SAM 3.1 once per concept (it tracks with stable IDs). Short clips are wasteful because of the 50-frame minimum. Fall back to 20–30 s segments only if a limit is hit, stitching IDs at boundaries (track dedup handles the rest).
7. **Caching and idempotency:** every stage writes outputs keyed by `(scan_id, stage, params_hash)`; retries never re-pay for finished model calls.
8. **Spend guard:** each stage estimates cost before calling a model and stops if the run would exceed `SPEND_LIMIT_USD_PER_RUN`.
9. **Privacy:** person / license-plate masks are used to blur frames before they are stored.

## Consequences
- Cost per scan is predictable: roughly (concepts × frames) for SAM plus a few cents for voice and the agent.
- Turn-level timestamps are coarse; narration is linked to the findings seen during that turn, not to a single frame.

## Re-check
- SAM 3.1 max resolution and latency (not published); whether a whole 3-minute clip per concept stays within rate limits.

## As built (Nov 2)
- Uploads arrive in 4 MB slices through the web app (not pre-signed URLs); up to 40 clips per scan, joined into one SAM 3.1 run with tracks split at cuts.
- SAM 3.1 gets up to 3 frames per second (`SAM_FPS`), lowered automatically to fit the scan's budget; 12 concepts run concurrently against one upload.
- The privacy guard is its own stage after segmentation and fails closed; raw and intermediate media are deleted when the scan ends.
- Stages: `upload`, `normalize`, `frames`, `narration` (alongside `segment`), `segment`, `privacy`, `measure`, `rules`, `agent`, `report`.
