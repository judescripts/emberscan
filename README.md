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
5. **Plan:** a Muse Spark agent calls tools (hazards, measurements, rules, cost), verifies, and builds the fix plan. It can never override a rule result.
6. **Fix and rescan:** track fixes; a rescan verifies them and updates the score.

## Meta models used (planned)

| Model | Where | Why |
|---|---|---|
| SAM 3.1 | Vision pipeline | Segment and track hazards across the whole video |
| Muse Spark | Agent | Plans the assessment, calls tools, explains and prioritizes fixes |
| Muse Voice Transcribe | Narration | Ties spoken notes to locations in the video |
| Muse Image | Report | "After" illustrations of top fixes |
| Muse Spark Open | Open-weight path | Runs a core agent path on Baseten/Modal/Fireworks |

## Setup

Coming soon. See [`.env.example`](.env.example) for configuration. Never commit `.env`.

## License

[MIT](LICENSE). Third-party licenses are tracked in [THIRD_PARTY.md](THIRD_PARTY.md).
