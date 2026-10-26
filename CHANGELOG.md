# Changelog

All work happens during the hackathon (Oct 26 – Nov 4, 2026).

## Day 1 — Mon Oct 26
- Repository created: README, MIT license, `.gitignore`, `.env.example`, third-party license register.
- Model integration notes from the official Meta and partner docs (`docs/model-integration-notes.md`).
- California rules reference re-verified from official sources as of Oct 26 (`docs/rules/defensible-space.md`) and the `us-ca` rule pack for the engine (`docs/rules/us-ca.json`): 39 rules. Zone 0 is still proposed; the Board of Forestry votes Nov 5 to resubmit it.
- Hazard taxonomy mapped to the us-ca rules (`docs/hazard-taxonomy.md`), footage shot list with narration prompts (`docs/footage-shot-list.md`), seven ADRs (`docs/adr/`) and the judging map (`docs/judging-map.md`).
- App skeleton: Next.js web app (`apps/web`), Python workers package (`workers`) with a validated rule-pack loader and 7 tests, GitHub Actions CI (lint, typecheck, build, tests), third-party license list.
- Confirmed Meta Model API access: all planned models listed for our key; first Muse Spark call succeeded (note: `max_output_tokens` includes reasoning tokens).

## Day 1 (continued)
- Spend tracking (F3, part 1): Meta price table, cost functions for tokens, SAM frames (50-frame minimum), audio seconds and images, and a per-run ledger that blocks a call before it would exceed `SPEND_LIMIT_USD_PER_RUN`. 10 tests.
- `docs/how-measurement-works.md`: how the printed marker, homography and uncertainty ranges turn video into feet.
- Video pipeline (B1): ffprobe/ffmpeg wrappers to probe, normalize to H.264 720p, extract frames with timestamps, and extract 16 kHz mono WAV for Voice Transcribe. Tests use synthetic clips only; CI installs ffmpeg.
- Keyframe selection (B2): drop blurry frames (variance of Laplacian) and near-duplicates (dHash), cap the count while keeping coverage. Checked on a real clip: 16 frames to 8 keyframes in about a second.
- SAM 3.1 tracking (C1): Meta API client (file upload, streamed Responses), segment_video with spend checks and billed-frame recording, and a Node helper running Meta's official SAM parser (about 70x faster than the Python build: 0.7 s vs 46 s for 24 frames). First live run: bark mulch tracked as one object across all 24 frames, 0.78 confidence, 50 frames billed ($0.01). Replay tests from the recorded response; `normalize` can lower fps to cut SAM cost.
- Rules engine (D1): deterministic evaluation of the us-ca pack against measured hazards (distance ranges, zone uncertainty, unobserved sides), with pass / fail / needs-review per rule and a score. 45 tests.
- Scan pipeline and worker service: normalize, frames, SAM 3.1 (12 hazard concepts in parallel, one upload), measure, rules, narration (Voice Transcribe), agent, report. FastAPI service with live stage progress. First live end-to-end scan: 8 objects tracked, 39 rules checked, 5 fixes, $0.12.
- Muse Spark agent (D2/D3): reads rule results, hazards and narration through tool calls, submits a fix plan, and a code-side verifier rejects plans that cite unknown rules or leave a failed rule uncovered (one retry, then a deterministic fallback plan). Every step is kept for the report's trace.
- Measurement (C2/C3/C5): scale-marker detection and ground homography with Monte Carlo uncertainty, focal-length estimate across frames, wall distance per hazard track, zone assignment that flags boundary cases, and annotated evidence images (mask, wall line, distance). Printable 6x8 marker PDF. 3.0 ft synthetic hazard measured as 2.8-3.2 ft.
- Address research agent: add a street address to a building and Muse Spark looks it up with tool calls (US Census geocoder, LA County 2025 Fire Hazard Severity Zones, CAL FIRE fire perimeters, our rule reference) and writes a cited note: jurisdiction, hazard zone, which law applies, recent fires, what to confirm. Code drops any fact citing a source the agent never looked up. First run: 28422 Constellation Rd, Very High LRA, Gov. Code 51182, Hughes Fire 2025 within 5 miles, $0.0008. Account-wide spend caps (24 h, total, concurrency) and an optional scan passcode guard the Meta account.
