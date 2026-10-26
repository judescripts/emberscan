# Third-party licenses

Every library, model, dataset and asset used by EmberScan, with its license. Updated whenever a dependency is added (rule: only use what we have the rights to).

## Models and APIs

| Name | Used for | License / terms | Attribution required |
|---|---|---|---|
| Meta Model API (Muse Spark, SAM 3.1, Voice Transcribe, Muse Image) | Agent, vision, narration, illustrations | Meta Model API terms | — |
| Muse Spark Open | Open-weight agent path | Muse Spark Open license | Yes: "Built with Muse Spark Open" |

## Libraries

| Name | Version | License | Used for |
|---|---|---|---|
| Next.js | 16.4.3 | MIT | Web app framework |
| React, React DOM | 19.3.0 | MIT | UI |
| Tailwind CSS | 4.x | MIT | Styling |
| TypeScript | 5.x | Apache-2.0 | Type checking |
| ESLint, eslint-config-next | 9.x / 16.4.3 | MIT | Linting |
| Drizzle ORM | 0.45.4 | Apache-2.0 | Database access |
| drizzle-kit | 0.31.11 | MIT | Migrations (dev) |
| PGlite (@electric-sql/pglite) | 0.5.8 | Apache-2.0 | Local embedded Postgres (dev/demo) |
| @neondatabase/serverless | 1.2.0 | MIT | Hosted Postgres driver |
| Vitest | 4.1.11 | MIT | Web tests |
| tsx | 4.23.15 | MIT | Running TS scripts (dev) |
| Geist, Geist Mono (via next/font) | — | SIL Open Font License 1.1 | UI fonts |
| Pydantic | 2.x | MIT | Rule pack and output schemas |
| NumPy | 2.x | BSD-3-Clause | Image math (sharpness, hashing) |
| Pillow | 11-12.x | MIT-CMU (HPND) | Image loading and resizing |
| HTTPX | 0.x | BSD-3-Clause | Meta Model API client |
| OpenCV (opencv-python-headless) | 4.x | Apache-2.0 | Marker detection, homography |
| FastAPI | 0.x | MIT | Worker HTTP service |
| Uvicorn | 0.x | BSD-3-Clause | Worker ASGI server |
| python-multipart | 0.x | Apache-2.0 | Video upload parsing |
| @meta-sam/parser | 0.1.0 | SAM License (royalty-free use and redistribution) | Parsing SAM 3.1 segmentation responses (Node helper) |
| FFmpeg (system tool, not bundled) | 9.x | LGPL/GPL (invoked as a separate program) | Video normalization, frames, audio |
| pytest | 8.x | MIT | Tests |
| Ruff | 0.x | MIT | Python lint |
| Hatchling | 1.x | MIT | Python packaging |

## Data and content

| Name | Source | License / status | Used for |
|---|---|---|---|
| California defensible-space rules | CAL FIRE, PRC 4291, 14 CCR, Board of Forestry | Public law / government publications, cited per rule | Rules engine |

## Assets

| Name | Source | License |
|---|---|---|
| Test footage | Filmed by the author (building exteriors only) | Author's own |
