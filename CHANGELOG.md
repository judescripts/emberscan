# Changelog

All work happens during the hackathon (Oct 26 – Nov 4, 2026).

## Day 1 — Mon Oct 26
- Repository created: README, MIT license, `.gitignore`, `.env.example`, third-party license register.
- Model integration notes from the official Meta and partner docs (`docs/model-integration-notes.md`).
- California rules reference re-verified from official sources as of Oct 26 (`docs/rules/defensible-space.md`) and the `us-ca` rule pack for the engine (`docs/rules/us-ca.json`): 39 rules. Zone 0 is still proposed; the Board of Forestry votes Nov 5 to resubmit it.
- Hazard taxonomy mapped to the us-ca rules (`docs/hazard-taxonomy.md`), footage shot list with narration prompts (`docs/footage-shot-list.md`), seven ADRs (`docs/adr/`) and the judging map (`docs/judging-map.md`).
- App skeleton: Next.js web app (`apps/web`), Python workers package (`workers`) with a validated rule-pack loader and 7 tests, GitHub Actions CI (lint, typecheck, build, tests), third-party license list.
- Confirmed Meta Model API access: all planned models listed for our key; first Muse Spark call succeeded (note: `max_output_tokens` includes reasoning tokens).
