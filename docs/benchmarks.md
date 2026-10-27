# Benchmarks

## Fix-plan agent: hosted Muse Spark vs Muse Spark Open (story D4)

Same scan, same tools, same instructions, same code verifier. Replayed with
`workers/scripts/bench_agent.py` on the real 28422 Constellation Rd scan (3 takes, 20 hazards,
39 rules, 1 fail, commercial wording), 3 runs per model, Oct 27, 2026.

| | Hosted Muse Spark | Muse Spark Open |
|---|---|---|
| Model | `muse-spark-1.3-contributor` (Meta Model API) | `meta-models/muse-spark-open-1026` (Baseten) |
| Valid plans (verifier accepted, every failed rule covered) | 3 of 3 | 3 of 3 |
| Fixes per plan | 4, 4, 4 | 3, 5, 4 |
| Fixes dropped by the verifier | 0 | 0 |
| Latency, median (max) | 68 s (85 s) | 64 s (75 s) |
| Model turns | 4-5 | 4-7 |
| Tokens per plan (in / out) | about 21-28k / 3-5k | about 23-44k / 7-21k |
| Cost per plan | about $0.002 | about $0.08 (list price, from Baseten credits) |

Takeaways:

- Muse Spark Open handles the whole tool-calling agent, not just the explanation step: it
  calls the same tools, submits through `submit_plan`, and passed the verifier every time.
- It reasons longer (more output tokens), so it is slower per turn but needs no retries.
- Hosted Muse Spark at the contributor price is about 40x cheaper per plan. EmberScan plans
  on Muse Spark Open first and falls back to hosted Muse Spark if Spark Open fails, gives no
  valid plan, or would push the scan past its spend limit. The report says which model planned.

Re-run: `cd workers && python scripts/bench_agent.py .data/scans/<scan>/report.json --runs 3`.
Each run calls both models for real.
