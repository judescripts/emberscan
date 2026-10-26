# ADR 0006: Open-weight serving (Muse Spark Open)

**Status:** Proposed (2026-10-26). Depends on partner credit approval and the Baseten model ID.

## Context
The Best Build on Meta Open-Weight Models prize ($10K) requires a core path on an open-weight model, verified by the infra partner. Options from the model notes (Oct 26): Muse Spark Open on Baseten (hackathon ID per handoff `meta-models/muse-spark-open-1026`, **VERIFY**: public pages show `meta-models/muse-spark-open`), Modal (self-deployed, dedicated GPUs), Fireworks (Glimmer serverless ended Sept 25; dedicated only). Baseten accepts a JSON schema for Spark Open but **doesn't enforce it**. Muse Spark Open's license requires the credit "Built with Muse Spark Open".

## Options
1. **Baseten** hosted Muse Spark Open (OpenAI-compatible endpoint, credits + 2M TPM requested).
2. Modal self-deploy (more control; more setup; uses our Modal workspace).
3. Fireworks dedicated deployment (pay per GPU hour).

## Decision (proposed)
- **Baseten first**, Modal as fallback.
- **Which path:** the **fix explanation and prioritization step** of the agent (ADR 0005) runs on Muse Spark Open in production, behind a provider switch (`AGENT_PROVIDER=meta|baseten|modal`). Tool-heavy planning can stay on hosted Muse Spark if Spark Open's tool calling is weaker.
- **Same guardrails:** our own JSON-schema validation (since Baseten doesn't enforce it), the same verifier, the same trace.
- **Benchmark (D4):** p50/p95 latency and cost per scan, hosted vs open-weight, in `docs/benchmarks.md`.
- **Attribution:** "Built with Muse Spark Open" in the README and the app footer.

## Re-check
- Exact Baseten model ID (ask in Discord #baseten); prize verification steps (ask in #meta / #office-hours); credit approval status.
