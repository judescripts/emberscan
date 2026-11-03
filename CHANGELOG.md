# Changelog

All work happened during the hackathon (Oct 26 – Nov 4, 2026). The git history has the full detail.

## Day 1: Mon Oct 26

**Groundwork**
- Repository created: README, MIT license, `.gitignore`, `.env.example`, third-party license register.
- Model integration notes from the official Meta and partner docs (`docs/model-integration-notes.md`).
- California rules reference re-verified from official sources as of Oct 26 (`docs/rules/defensible-space.md`), and the `us-ca` rule pack for the engine (`docs/rules/us-ca.json`, 39 rules). Zone 0 is still proposed; the Board of Forestry votes Nov 5 to resubmit it.
- Hazard taxonomy mapped to the us-ca rules, a filming shot list, seven ADRs and the judging map.
- App skeleton: Next.js web app (`apps/web`), Python workers package (`workers`) with a validated rule-pack loader, and GitHub Actions CI (lint, typecheck, build, tests).
- Confirmed Meta Model API access. The first Muse Spark call worked. One note: `max_output_tokens` includes reasoning tokens.

**Pipeline**
- Spend tracking: a Meta price table, cost functions (tokens, SAM frames with the 50-frame minimum, audio seconds, images), and a per-run ledger that blocks a call before it would exceed `SPEND_LIMIT_USD_PER_RUN`.
- Video pipeline: ffprobe/ffmpeg wrappers to probe a clip, normalize it to H.264 720p, extract frames with timestamps, and extract 16 kHz mono WAV for Voice Transcribe.
- Keyframe selection: drops blurry frames (variance of Laplacian) and near-duplicates (dHash).
- SAM 3.1 tracking:
  - Meta API client with file upload and streamed Responses.
  - Spend checks before each call.
  - A Node helper running Meta's official SAM parser, about 70x faster than the Python build.
  - First live run: bark mulch tracked as one object across all 24 frames, $0.01.
- Measurement:
  - Scale-marker detection and a ground homography with Monte Carlo uncertainty.
  - Wall distance per hazard track, and zone assignment that flags boundary cases.
  - Annotated evidence images.
  - A printable marker PDF. A synthetic hazard at 3.0 ft measured 2.8–3.2 ft.
  - Explained in `docs/how-measurement-works.md`.
- Rules engine: deterministic evaluation of the us-ca pack against measured hazards (distance ranges, zone uncertainty, unobserved sides), returning pass / fail / needs-review per rule and a score.
- Muse Spark fix-plan agent: reads rule results, hazards and narration through tool calls and submits a plan. A code verifier rejects plans that cite unknown rules or leave a failed rule uncovered. It allows one retry, then falls back to a deterministic plan. Every step is kept for the report's trace.
- Scan pipeline and FastAPI worker service with live stage progress. First end-to-end scan: 8 objects tracked, 39 rules checked, 5 fixes, $0.12.

**Web app**
- Communities, buildings, scans with live progress, reports and fix tracking.
- Commercial community type, with commercial wording in reports and plans.
- Account-wide spend caps (24 h, total, concurrent scans) and an optional scan passcode.
- Address research agent: Muse Spark looks up a building's address with tool calls (US Census geocoder, Fire Hazard Severity Zones, CAL FIRE fire perimeters, our rule reference) and writes a cited note. Code drops any fact citing a source the agent never looked up. A run costs about $0.001.
- Multi-clip scans: several walkaround clips joined into one SAM 3.1 run, with sides tagged per clip or from narration.
- Report:
  - Evidence with "hover for why".
  - A zone map: zoomed to the hazards, phone-friendly, crowded walls grouped.
  - A sticky section bar, with evidence linked to the fixes that cover it.
  - One card per building with its scan history.
- First real-footage scan (an office building, 3 takes, 48 s): 16 objects tracked, 7 of 15 hazards measured with the marker, first real fail (dry leaves 1.0–1.3 ft from the wall), score 78, $0.35. Fixes it needed:
  - portrait video size
  - marker detection at full resolution
  - looser marker-fit limits for real sheets on uneven ground
  - a budget-aware SAM frame rate

## Day 2: Tue Oct 27

- **Muse Spark Open:**
  - The fix-plan agent now runs on Meta's open-weight model on Baseten (`meta-models/muse-spark-open-1026`), with the same tools, verifier and trace.
  - It falls back to hosted Muse Spark if Spark Open fails, gives no valid plan, or would pass the scan's spend limit. The report shows which model planned.
  - Benchmark: 3 of 3 valid plans on each model, median 64 s (open) vs 68 s (hosted) (`docs/benchmarks.md`).
  - Loop guards added after a run where Spark Open repeated a tool call until it ran out of turns.
- **Muse Image fix previews:**
  - The top fixes get the frame of their closest measured hazard edited to show only that fix done, shown as Now / After.
  - Labelled on the picture itself as an AI-generated preview, never evidence.
  - Muse Spark checks each pair and drops a preview that shows no change or misrepresents its fix.
  - About $0.01 each. A failed preview never fails the scan.
- **Privacy guard:**
  - SAM 3.1 also looks for people and license plates in the same upload, and every box where one was seen is pixelated and blurred in all frames before any evidence or preview is made.
  - Raw and intermediate video and audio are deleted when the scan ends.
  - It fails closed, and it shows as the first step of the agent trace.
- **Coverage, not false passes:** the rules engine knows how far out the walkaround covered. A rule whose area lies beyond that is "Not covered by this video, check on site" and doesn't move the score. The zone map hatches the ground the video didn't cover.
- **Eave depth:** corner clips were removed. Each building now has No overhang / I know it (ft) / Not sure, and "Not sure" makes the two eave rules needs-review.
- **California only, said plainly:** an address outside California is flagged on the building, the New scan form and the report.
- **Hazard-zone lookup:** now statewide, from CAL FIRE / State Fire Marshal maps (SRA and the 2025 LRA map).
- **Building photos:** aerial cover photos for buildings (USGS NAIP, public domain).
- **Distance check:** EmberScan vs Muse Spark guessing by eye, on the same frames (`workers/scripts/distance_check.py`, results in `docs/benchmarks.md`).

## Day 3: Wed Oct 28

- **Measurement:** each hazard is measured from the frames nearest the marker, and an unmeasured hazard says why.
- **Long videos:** uploads go in slices: the browser sends 4 MB slices through the web app to the worker, which appends them, so long walkarounds get past Vercel's request limit.
- **Deployment:**
  - The worker runs as a Modal app; the web app is on Vercel, with Neon Postgres.
  - Deploy runbook in `docs/deploy.md`.
- **Branding:** ember flame favicon and Apple icon.
- **Local dev:** `SEED_SAMPLE=0` starts the local app empty.

## Day 4: Thu Oct 29

- **Gutter false positives:** gutter and roof debris seen low in the frame is dropped, because it was dry leaves on the ground.
- **No guessed zones:** an unmeasured hazard is no longer placed in zones the video didn't cover.
- **Scattered leaves:** leaves seen together are reported as one finding ("Dry leaves (N spots)", nearest distance) with every leaf outlined in one evidence frame, instead of one finding per leaf.

## Day 8: Mon Nov 2

- **Address privacy:** the address field's placeholder is a generic hint, and the docs no longer name the test building's address.
- **Docs:** README and docs updated to match what was built.
