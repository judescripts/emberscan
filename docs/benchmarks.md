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

### Follow-up: a bigger scan (Oct 27, 23 hazards)

In a live scan with 23 hazards, Muse Spark Open called `estimate_cost` 12 times for the same 3
fix types and ran out of turns, so hosted Muse Spark planned instead. Two loop guards were
added: a repeated tool call gets "already answered, call submit_plan now", and with two turns
left the agent is told to submit. Replayed on the same scan, 2 runs each:

| | Hosted Muse Spark | Muse Spark Open |
|---|---|---|
| Valid plans | 2 of 2 | 2 of 2 |
| Fixes per plan | 2, 2 | 3, 3 |
| Latency, median | 90 s | 36 s |

Re-run: `cd workers && python scripts/bench_agent.py .data/scans/<scan>/report.json --runs 3`.
Each run calls both models for real.

## Distance: EmberScan vs a vision model's guess vs a tape

Could a vision model just read the distance off a photo with the marker in it? `scripts/distance_check.py` asks Muse Spark (`muse-spark-1.3-contributor`, medium reasoning) for the distance of each marker-measured hazard, on the same frame EmberScan measured from, with the hazard boxed in orange and the marker's exact size in the prompt. So the model has the same scale reference; it judges by eye instead of with the homography. About $0.016 for 26 hazards.

### Run 1 (Oct 27): four saved scans, no tape yet

21 distinct hazards (two scans were the same video), from the Valencia buildings. Almost everything is within 2 ft of the wall.

| | Count |
|---|---|
| Model's range overlaps EmberScan's range | 15 / 21 |
| Model's single number falls inside EmberScan's range | 7 / 21 |
| Same side of the 5 ft Zone 0 line | 19 / 21 |

What it says:

- **Near the wall, both get it roughly right.** A shrub against the wall is easy by eye; this is the case where measurement adds the least.
- **The one real disagreement is ours to explain.** `h-leaf_litter-0` (a single dry leaf caught in a shrub) was measured at 4.8–9.5 ft, low confidence, zone uncertain. Muse Spark said about 1.2 ft, and looking at the frame the leaf is roughly 2 ft out. The marker was about 5 ft to the side and the leaf sits on foliage above the ground, so the homography was extrapolating from a raised point far from the sheet. EmberScan flagged it as low confidence and uncertain, but its range likely misses the truth. Fixes on the filming side: lay several markers along each side so every hazard has one nearby.
- **Without a tape, neither column can be scored.** That needs the staged test below.

### Run 2 (planned): staged test across the 5 ft line, with tape

Movable objects placed at taped distances on both sides of the Zone 0 line (for example a bin at 3 ft, a chair at 4.5 ft, a pot at 6 ft, a box at 8 ft), filmed with markers laid along the wall every ~10 ft, then `distance_check.py` with `tape_ft` filled in. Target from the shot list: the tape value inside EmberScan's range for 80% or more of hazards. This is a staged accuracy test, not a real property's hazards, and it's reported that way.
