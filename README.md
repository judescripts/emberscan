# EmberScan

**Turn a short phone video into a measured, rule-by-rule wildfire defensible-space assessment for homes and HOA communities.**

A resident or HOA manager films a walkaround of a building. EmberScan tracks every hazard across the video with SAM 3.1, measures how far each one is from the wall, checks it against California's defensible-space rules with a deterministic rules engine (with citations), and a Muse Spark agent builds a prioritized fix plan: what to do, how hard, rough cost, and whether it's the owner's or the HOA's job. Rescans verify fixes.

> EmberScan flags likely wildfire hazards and suggests fixes. It is not an inspection and does not certify that any property is safe or compliant.

Entry for the **Meta Global AI Developer Hackathon** (Startup track, problem statement: *Build for Your World*).

## Status

🚧 Building. Day 1 of 10 (Oct 26, 2026).

## Built during the hackathon

All code, data and assets in this repository were created during the hackathon, **Oct 26 – Nov 4, 2026**. The git history is the record. Nothing was imported from earlier work.

## How it works (planned)

1. **Film** a walkaround (optionally narrate: "north side, mulch bed against the wall").
2. **Track:** SAM 3.1 segments and tracks hazards and walls across the video.
3. **Measure:** a printed scale marker on the ground sets real-world scale; each hazard gets a distance range and a zone.
4. **Check:** a deterministic rules engine returns pass / fail / needs-review per rule, with citations.
5. **Plan:** a Muse Spark Open agent (open weights, on Baseten; hosted Muse Spark as backup) calls tools (hazards, measurements, rules, cost), a code verifier checks every claim, and it builds the fix plan. It can never override a rule result. Muse Image then draws an "after" picture of the top fixes from the real video frame, labelled as an AI illustration.
6. **Fix and rescan:** track fixes; a rescan verifies them and updates the score.

## Meta models used

| Model | Where | Why |
|---|---|---|
| SAM 3.1 | Vision pipeline | Segment and track hazards across the whole video |
| Muse Spark Open | Fix-plan agent (primary) | Meta's open-weight model on Baseten plans the fixes with tool calls; same verifier and trace ([benchmarks](docs/benchmarks.md)) |
| Muse Spark | Agent fallback, eaves, address research | Hosted backup for the fix plan; reads roof overhang from corner clips; researches the address |
| Muse Voice Transcribe | Narration | Ties spoken notes to locations in the video |
| Muse Image | Report | "After" pictures of the top fixes, edited from the real video frame and labelled as AI illustrations |

Built with Muse Spark Open.

## Repository layout

| Path | What |
|---|---|
| `apps/web` | Next.js web app (mobile-first) |
| `workers` | Python pipeline: frames, segmentation, geometry, rules engine, agent |
| `docs/rules` | Rule packs (`us-ca.json`) and the California rules reference |
| `docs/adr` | Architecture decisions |

## Setup

Requires Node.js 24, Python 3.12 and ffmpeg. Copy [`.env.example`](.env.example) to `.env` and fill it in. Never commit `.env`.

```bash
cd apps/web && npm ci && npm run dev
```

```bash
cd workers && python -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest
```

## License

[MIT](LICENSE). Third-party licenses are tracked in [THIRD_PARTY.md](THIRD_PARTY.md).
