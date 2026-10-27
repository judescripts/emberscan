# EmberScan

**Turn a short phone video into a measured, rule-by-rule wildfire defensible-space assessment for homes and HOA communities.**

A resident or HOA manager films a walkaround of a building. EmberScan tracks every hazard across the video with SAM 3.1, measures how far each one is from the wall, checks it against California's defensible-space rules with a deterministic rules engine (with citations), and a Muse Spark agent builds a prioritized fix plan: what to do, how hard, rough cost, and whether it's the owner's or the HOA's job. Rescans verify fixes.

> EmberScan flags likely wildfire hazards and suggests fixes. It is not an inspection and does not certify that any property is safe or compliant.

Entry for the **Meta Global AI Developer Hackathon** (Startup track, problem statement: *Build for Your World*).

## Status

🚧 Building. Day 1 of 10 (Oct 26, 2026).

## Built during the hackathon

All code, data and assets in this repository were created during the hackathon, **Oct 26 – Nov 4, 2026**. The git history is the record. Nothing was imported from earlier work.

## How it works

1. **Film** a walkaround (optionally narrate: "north side, mulch bed against the wall").
2. **Track:** SAM 3.1 segments and tracks hazards and walls across the video.
3. **Protect:** a privacy guard blurs any people and license plates (found by SAM 3.1 in the same pass) in every frame before evidence or pictures are made, and deletes the raw video when the scan ends. It's code, not a model choice, and the agent trace shows it.
4. **Measure:** a printed scale marker on the ground sets real-world scale; each hazard gets a distance range and a zone.
5. **Check:** a deterministic rules engine returns pass / fail / needs-review per rule, with citations.
6. **Plan:** a Muse Spark Open agent (open weights, on Baseten; hosted Muse Spark as backup) calls tools (hazards, measurements, rules, cost), a code verifier checks every claim, and it builds the fix plan. It can never override a rule result. Then Muse Image draws an AI preview of each top fix (see below).
7. **Fix and rescan:** track fixes; a rescan verifies them and updates the score.

## Scope: California only, for now

- **Rules:** California's defensible-space rules only (`docs/rules/us-ca.json`: PRC 4291, Gov. Code 51182, 14 CCR 1299.03, the proposed Zone 0 rules and Board guidance, checked Oct 26, 2026). Local ordinances aren't included.
- **Other states** need their own rule pack. The rules engine is state-agnostic; the work is the legal research and each state's hazard-zone data.
- **Addresses outside California** are flagged on the building, the New scan form and the report.
- **Hazard-zone lookup** reads Los Angeles County's Fire Hazard Severity Zone map; elsewhere in California the research note points to CAL FIRE's zone viewer instead.

## AI previews of the fix

A fix like "clear the first 5 ft of combustibles" is abstract. EmberScan shows it on your own building: Muse Image edits the real video frame to show only that fix done, next to the frame as it is now.

- **A preview, never evidence.** It is marked on the picture itself ("AI-generated preview" badge, dashed frame) and in the caption. It is never measured, and the score never changes because of it. Only a rescan updates the score; the caption shows the projected score for that fix.
- **Checked before it is shown.** Muse Spark compares each pair and drops a preview that shows no change or misrepresents the fix (an inspection fix pictured as removal).
- **Easy to read.** Orange outlines mark what the scan found; dashed outlines mark the same spot in the preview.
- **Private.** Previews are drawn from frames that already passed the privacy guard and never add people.
- **Useful to hand over.** Most fixes belong to someone else (the property manager, a landscaper); a picture of the goal is easier to pass on than a rule citation.

## Meta models used

| Model | Where | Why |
|---|---|---|
| SAM 3.1 | Vision pipeline, privacy guard | Segment and track hazards across the whole video; find people and plates to blur |
| Muse Spark Open | Fix-plan agent (primary) | Meta's open-weight model on Baseten plans the fixes with tool calls; same verifier and trace ([benchmarks](docs/benchmarks.md)) |
| Muse Spark | Agent fallback, address research, preview check | Hosted backup for the fix plan; researches the address; checks each AI preview shows its fix |
| Muse Voice Transcribe | Narration | Ties spoken notes to locations in the video |
| Muse Image | Fix previews | AI preview of what each top fix should look like, edited from your own (blurred) video frame |

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
