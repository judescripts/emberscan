# Judging map

This maps EmberScan to the hackathon's judging criteria. Stage 1 is pass/fail: the project fits a problem statement and genuinely uses Meta's models. Stage 2 scores each criterion from 0 to 10.

**Problem statement:** *Build for Your World* (lead): HOA communities and commercial properties in California's high fire-hazard zones have to keep defensible space, but nobody on site can measure it or read the rules. *Push the Frontier* (secondary): measuring a physical system from ordinary phone video.

## Criteria

| Criterion | Weight | How EmberScan scores |
|---|---|---|
| **Impact** | 30% | Most homes lost in wildfires are lit by embers landing on what is next to the walls, and insurers are non-renewing communities in high-hazard zones. EmberScan turns a 2-minute video into a cited, measured, prioritized fix plan with owner vs HOA or property-manager responsibility, tracked as tasks and verified by rescan. |
| **Use of Meta AI tooling** | 25% | Five Meta models, each with a real job: SAM 3.1 tracks hazards (and finds people to blur) across the video; Muse Spark Open runs the tool-calling fix-plan agent on Baseten; Muse Spark researches addresses and checks every AI preview; Muse Voice Transcribe ties narration to the video; Muse Image draws fix previews on the real building. |
| **Demo** | 25% | Live product on a public URL. The video opens with a measured finding, its rule and its fix, then shows the research agent, filming with the marker, the pipeline, the report, the agent trace with an AI preview, and the fix tasks. |
| **Technical depth & execution** | 20% | Ground-plane geometry from a printed marker with uncertainty ranges; a deterministic, tested rules engine over a versioned rule pack; agents with code-side verifiers and stored traces; a privacy guard that fails closed; spend caps; a dated git history. |

## Bonus prizes

| Prize | What it rewards | Where EmberScan fits |
|---|---|---|
| Best Agentic Use-Case ($5K) | Agents that complete meaningful tasks, make decisions or coordinate multi-step work | Two agents: address research (tools for geocoding, hazard zones and fire history, with cited output) and the fix plan (tool calls, code verifier, retry and fallback, visible trace) |
| Best Build on Meta Open Weight Models ($10K) | A project built on Muse Glimmer or Muse Spark Open via partner inference | The fix-plan agent runs on Muse Spark Open on Baseten, benchmarked against hosted Muse Spark ([benchmarks](benchmarks.md)) |
| Best Creative Build ($5K) | Original use of Muse Image or Muse Wonder | Muse Image previews of each fix on the user's own building, checked by Muse Spark and clearly labelled as AI |
| Most Viral Project ($20K) | Engagement on X after the event, through Nov 8 | Demo posted on X after submission |
| Community Vote ($10K) | Votes in the public gallery | Gallery entry with the before/after preview |

## Anti-project check

| Organizers' "avoid" item | Why EmberScan is different |
|---|---|
| Simple image analyzers | Video with tracked objects, measured distances, deterministic rules with citations, an agent plan, fix tasks and rescans. Every screen shows at least one of those. |
| Basic RAG apps | No document Q&A. Rules are evaluated by code, not retrieved for a chatbot. |
| Medical, political or other banned topics | None. |
