# Test footage shot list

Real footage for building the pipeline (SAM 3.1 runs on it on Day 2) and for the demo. Shoot as early as possible.

## Privacy rules (non-negotiable)

- **Building exteriors and landscaping only.** No people, faces, license plates you don't own, or the inside of anyone's unit. Don't film through windows or open doors.
- Film when common areas are quiet. If someone walks into frame, stop and redo that part.
- Only film buildings and shared areas you or the HOA may document. Get the HOA manager's OK for shared landscaping in the demo.
- Anything caught by accident is **blurred before the file is stored**. Raw clips stay on the phone until reviewed.
- Raw video and audio never go into git (`*.mp4`, `*.mov`, `*.wav` and `footage/` are ignored).

## Camera settings

| Setting | Value | Why |
|---|---|---|
| Resolution | 1080p | Enough detail; keeps uploads small (SAM 3.1 takes up to 15,000 frames) |
| Frame rate | 30 fps | Smooth tracking; frames are sampled down later |
| Lens | Main 1x, no ultrawide, no zoom | Ultrawide distortion and zoom changes break distances |
| Orientation | Landscape | More wall base and ground in frame |
| Stabilization | On | Fewer blurry frames |
| Pace | Slow walk, about 1 step per second | Better tracking |
| Light | Overcast, or morning / late afternoon | No harsh shadows or backlit walls |

## Scale marker

A printed sheet with a black-and-white checkerboard of exact 1-inch squares. **Lay it flat on the ground, checkerboard up, with one edge touching the base of the wall** (one per side, or move it at each corner). It gives the camera real-world scale and the ground plane that distances are measured along.

- Print at 100% / Actual size, never "Fit to page". Check a square with a ruler: exactly 1 in.
- The printable EmberScan marker is built in this repo on Day 3 (story C5). For today's test footage, any checkerboard printout with squares you've measured works; write the square size in the shot log.
- No printer: lay a tape measure on the ground from the wall out to 10 ft. Last resort: a standard door (record its real width and height).

## Ground truth

Tape-measure the real distance from the wall to at least 5 hazards per building (mulch edge, nearest shrub, fence join, woodpile, propane tank). Also measure the **eave depth** once: along the ground from the wall to the point directly under the gutter edge. This is how we'll check the distance estimates (target: the true value is inside the reported range for 80% or more of hazards).

## Shots per building

| # | Shot | How | Length |
|---|---|---|---|
| 1 | Full walkaround | One loop about 8–12 ft from the wall at chest height; wall base and ground out to ~15 ft in frame | 1–3 min |
| 2 | Wide context | Slow pan from ~30 ft out on each side (Zone 1 and the start of Zone 2) | 15 s per side |
| 3 | Corner profile | At one or two corners, stand 6–10 ft out and film along the wall so the roof overhang shows in profile, with the marker in frame | 3–5 s per corner |
| 4 | Eaves and soffits | Tilt up slowly along each side | 10–15 s per side |
| 5 | Vents | Each foundation, gable and soffit vent, close enough to see the mesh | 3–5 s each |
| 6 | Gutters and roof edge | From the ground, showing any debris | 10 s per side |
| 7 | Fence joins | Where a fence meets the wall, close and medium | 5 s each |
| 8 | Zone 0 strip | Slow walk aimed at the ground 0–5 ft from the wall | 30–60 s per side |
| 9 | Specific hazards | Mulch beds, woodpiles, shrubs under windows, branches over the roof, stored items, propane tanks | 5 s each |
| 10 | Rescan pair | After one real fix (e.g. clear a mulch strip), reshoot shots 1 and 8 on that side | Same as above |

## Narration (for Muse Voice Transcribe)

Narrate while filming the walkaround. Short, factual phrases help the agent tie findings to places:

- Where you are: "North side, starting at the garage corner."
- What you see: "Bark mulch bed against the wall under the kitchen window."
- Context the camera can't get: "This woodpile belongs to unit 6." "The HOA landscaper trims these shrubs." "Vent screens were replaced last year."
- What you already fixed: "We cleared this gutter on Saturday."

Avoid names of neighbors or anything personal. Narration is optional; the pipeline must also work on silent video.

## Shot log

| Date | Building | Clip file | Shots | Marker / scale used | Ground-truth distances (hazard: ft) | Eave depth (ft) | Narrated? | Blur needed |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |

## Minimum set for Day 2

- One building: shots 1, 3, 5, 8 and 9 with the marker, at least 5 ground-truth distances and the eave depth, narrated.
- One more walkaround of a second building (tests generalization).
- A backup copy of the best walkaround for the demo.
