# ADR 0003: Distance estimation

**Status:** Accepted (2026-10-26)

## Context
"Measured, not looks close" is what separates EmberScan from an image analyzer. Zone 0 is 5 ft deep, so 4 ft vs 6 ft decides the result. A phone camera has no scale; false precision would destroy trust.

## Options
1. **Known-size reference in frame** + segmentation masks + ground-plane geometry.
2. Monocular metric depth model (no setup; error grows with distance).
3. Phone LiDAR (native app only; out of scope, roadmap).
4. Structure-from-motion (too heavy for 10 days).

## Decision
- **v1 (Day 3): Option 1 with a printed scale marker** (story C5): a US Letter checkerboard of 1 in squares, **laid flat on the ground with one edge touching the base of the wall**.
  - Flat on the ground gives the ground plane directly (pose of a planar target via standard chessboard detection), which is the plane distances are measured along.
  - The edge at the wall pins the wall/ground line, so "distance from the wall" is measured from a known line.
  - Hazard distance = gap along the ground plane between the wall line and the hazard's nearest ground-contact point (from its SAM mask), in feet.
- **Uncertainty:** propagate marker size in pixels, viewing angle and mask-edge uncertainty into a **min–max range** and a confidence (high / medium / low). Ranges, never single numbers.
- **Fallbacks:** tape measure on the ground (scale only), standard door (scale only, lower confidence). Frames without any reference are low confidence, never guessed.
- **Upgrade (Day 7, if time):** monocular depth on Modal GPU for frames without a reference, always labeled low confidence and never the sole basis for a fail.
- **Eave depth** (sets the Z0-08 strip width): measured from the corner profile shot as a range, or entered by the user; if neither exists, eave-based findings are needs-review.
- **Output contract:** `distance_min_ft`, `distance_max_ft`, `confidence`, `method` (`marker` | `tape` | `door` | `depth`), `frame_refs`.
- **Rules interaction:** a range that straddles a threshold becomes needs-review (ADR 0004).

## Consequences
- Users must print and place a marker: the app explains it with a diagram and a download.
- Accuracy is testable against tape-measured ground truth (target: true value inside the range for ≥80% of hazards).
