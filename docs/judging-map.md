# Judging map

How each piece of EmberScan earns points. Stage 1 (pass/fail): fits a problem statement and genuinely uses Meta's models. Stage 2 scores 0–10 per criterion.

**Problem statement:** *Build for Your World* (lead): the founder lives in a townhome community in a high fire-risk area of Southern California, where HOAs struggle to keep master insurance. *Push the Frontier* (secondary): measuring a physical system from ordinary phone video.

## Criteria

| Criterion | Weight | How EmberScan scores | Stories |
|---|---|---|---|
| **Impact** | 30% | Wildfire ignition mostly starts with embers on what's next to the house; residents and HOA boards can't measure or interpret defensible-space rules; insurers are non-renewing. EmberScan turns a 2-minute video into a cited, prioritized fix plan with owner vs HOA responsibility, then verifies fixes by rescan. | E1, E3, E7, E4, D2 |
| **Use of Meta AI tooling** | 25% | Five Meta models working together: SAM 3.1 (tracking across the walkaround), Muse Spark (tool-calling agent), Muse Voice Transcribe (narration tied to locations), Muse Image ("after" illustrations of fixes), Muse Spark Open (open-weight path on Baseten/Modal). Each has a real job; none is a single description call. | C1, D2, B4, E8, D4 |
| **Demo** | 25% | Live product on a public URL; a 3-minute video that opens with hazards tracked across the video, measured distances, rule citations and the agent's plan, then a rescan that verifies a real fix. Side-by-side with a general chatbot on the same footage. | G1, G2, G3, F2 |
| **Technical depth & execution** | 20% | Ground-plane geometry from a printed marker with uncertainty ranges; deterministic, tested rules engine over versioned rule packs; verifiable agent with a code-level checker and stored trace; cost guardrails; clean dated git history. | C2, C3, C5, D1, D3, F1, F3 |

## Bonus prizes

| Prize | What it needs | How we target it | Stories |
|---|---|---|---|
| Best Agentic Use-Case ($5K) | A real agent that plans, uses tools, verifies, decides | Tool-calling Muse Spark agent with a verifier and a visible trace | D2, D3 |
| Best Build on Meta Open-Weight Models ($10K) | Core path on Muse Spark Open or Glimmer via a partner, verified by the partner | Fix-plan step on Muse Spark Open (Baseten), benchmarked vs hosted | D4 |
| Most Viral on X ($20K) | Engagement on X through Nov 8 | Post the demo right after submitting; a striking before/after clip | G7 |
| Community Vote ($10K) | Public gallery votes (announced Nov 16) | Clear gallery entry with the before/after visual | G7 |

## Anti-project check

| Organizers' "skip these" item | Why EmberScan is different | How we keep it obvious |
|---|---|---|
| Simple image analyzers | Video, tracked objects, measured distances, deterministic rules with citations, agent plan, rescans | Every screen shows at least one of those; the demo shows all four in the first 20 seconds |
| Dashboards as the main feature | The scan-to-fix-plan pipeline is the product; the report is its output | Lead with scanning and the agent; the HOA view is secondary |
| Streamlit apps | Next.js web app | Never Streamlit, not even internally |
| Basic RAG apps | No document Q&A; rules are evaluated by code, not retrieved for a chatbot | Rules engine is deterministic and tested |

## Meta model usage (for the README)

| Model | Where | Why it's essential |
|---|---|---|
| SAM 3.1 | Vision pipeline | Complete hazard inventory with stable IDs across the whole walkaround |
| Muse Spark | Agent | Plans the assessment, calls tools, explains and prioritizes |
| Muse Voice Transcribe | Narration | Adds context the camera can't see ("this woodpile is unit 6's") |
| Muse Image | Report | Shows what the fix looks like on the real building |
| Muse Spark Open | Open-weight path | Production fix-plan step on an open model |
