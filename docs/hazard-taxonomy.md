# Hazard taxonomy

What the vision step must find, and which rules in [`rules/us-ca.json`](rules/us-ca.json) each class feeds. SAM 3.1 takes **one text concept per request** (see [model notes](model-integration-notes.md)), so each concept below is one segmentation call per video. Concepts are starting points to tune on real footage (Day 2).

**Rule status matters:** every `Z0-*` rule is *proposed* today, so it produces "needs review / would not meet the proposed rule", never a fail.

## Structure and scale classes

These aren't hazards. Distances are measured from them.

| Class | SAM concept | Role |
|---|---|---|
| `wall` | "exterior wall of a house" | Distance origin: where wall meets ground |
| `eave` | "roof eave overhang" | Eave depth sets the Z0-08 strip width |
| `roof` | "roof" | Roof debris (ALL-02), branch clearance (Z0-06) |
| `chimney` | "chimney" | 10 ft branch clearance (ALL-01) |
| `gutter` | "rain gutter" | Locates gutter debris (Z1-02) |
| `window`, `door` | "window", "door" | 2 ft clearance (Z0-09); a door also gives a fallback scale |
| `deck` | "wooden deck or stairs" | Under-deck and 5 ft rules (Z1-05, Z0-02, Z0-10) |
| `scale_marker` | detected with OpenCV (chessboard), not SAM | Sets real-world scale and the ground plane |

## Hazard classes

| Class | SAM concept | Rules | Measurable from video |
|---|---|---|---|
| `wood_mulch` | "wood chip or bark mulch" | Z0-01 | Yes: distance from wall |
| `leaf_litter` | "dry leaves and pine needles on the ground" | Z1-01, Z2-02, Z0-01 | Distance yes; depth (Z2-02) no, so review |
| `dead_vegetation` | "dead brown plant" | ALL-03, Z1-01, Z1-03, Z1-05, Z2-01, Z0-01, Z0-02 | Partly: "dying" is a judgment, often review |
| `shrub` | "shrub or bush" | ALL-03, Z2-05, Z2-06, Z2-07, Z0-14 | Distance yes; height approximate |
| `tree` | "tree trunk" | ALL-01, Z2-05, Z2-06, Z0-18 | Distance yes; "newly planted" no |
| `tree_branch` | "tree branch near the roof" | ALL-01, ALL-03, Z1-03, Z0-04, Z0-05, Z0-06, Z0-07, Z2-07 | Vertical clearance is hard; review unless clearly touching |
| `ladder_fuel` | "low branches near the ground under a tree" | Z2-05, Z2-07, Z0-05 | Approximate height with scale |
| `grass_tall` | "tall dry grass" | Z2-03, Z0-11 | Height approximate (3–4 in thresholds), often review |
| `herbaceous_planting` | "flower bed" | Z0-11, Z0-12 | Spacing approximate |
| `potted_plant` | "potted plant" | Z0-13 | Count and distance yes; pot size approximate |
| `vegetation_any` | "plant" | ALL-04, Z1-05, Z2-04, Z12-01, Z12-02, Z0-02, Z0-08, Z0-09, Z0-10 | Distance yes (catch-all for clearance rules) |
| `roof_debris` | "leaves on a roof" | ALL-02 | Only if visible from the ground |
| `gutter_debris` | "leaves in a rain gutter" | Z1-02 | Only if visible from the ground |
| `woodpile` | "stacked firewood" | Z1-04, Z1-05, Z2-04, Z0-02, Z0-03 | Yes: distance |
| `fence_attached` | "wooden fence" + touches `wall` | Z0-15 | Yes: contact with the wall and the first 5 ft |
| `combustible_fence` | "wooden fence" | Z0-15, Z0-16 | Distance yes; "new" no, so review |
| `combustible_furniture` | "outdoor cushion", "trash bin", "doormat" | Z1-05, Z0-02, Z0-19 | Yes: distance |
| `propane_tank` | "propane tank" | Z12-01 | Yes: clearance |
| `outbuilding` | "garden shed" | Z12-02, Z0-17 | Distance yes; material is a review |
| `vehicle_or_boat` | "car", "boat" | Z0-20 | Yes. **Blur license plates before storage** |
| `open_vent` | "house vent" | ALL-05 | Mesh size not measurable; always review |

## Coverage check

- Every hazard class maps to at least one rule (table above, generated from `us-ca.json` on Oct 26).
- Rules that video can't settle are `manual_review` in the rule pack and show as "check on site" items.

## Privacy classes (detect to blur, never report)

`person`, `face`, `license_plate`, and anything seen through a window. Detected only to build blur masks before frames are stored; never saved as hazards. **VERIFY on Day 2** that SAM 3.1 handles "person" and "license plate" concepts well enough for this.
