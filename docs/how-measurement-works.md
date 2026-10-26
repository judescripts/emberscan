# How EmberScan measures distance from a phone video

A phone video is flat: it has pixels, not feet. Something 2 ft from the wall and something 6 ft from the wall can look almost the same, because how big things appear depends on how far they are from the camera and the angle you're filming at. To measure in feet, the camera needs a **ruler it can see**. That's the printed scale marker.

## 1. The marker is a known shape on the ground

The marker is one sheet of paper with a checkerboard of **exact 1-inch squares**. Its inner corners (where four squares meet) form a grid whose real-world positions we know exactly: (0 in, 0 in), (1 in, 0 in), (2 in, 0 in) … because we printed it.

It lies **flat on the ground**, with one edge touching the base of the wall. So we know three things for certain:
- the corners are 1 inch apart,
- they all lie on the ground,
- one edge of the grid is exactly where the wall meets the ground.

## 2. Finding the corners in the video

In each frame, standard computer-vision code (OpenCV's chessboard detector) finds the checkerboard and locates every inner corner to a fraction of a pixel. A checkerboard is used because its corners are high-contrast "X" points that are easy to find precisely, even at an angle, and the slightly uneven grid (6 × 8 squares) tells us which way the sheet is facing.

Now we have pairs: *this pixel* in the image is *that point in inches* on the ground.

## 3. From pixels to the ground: the homography

Here's the key idea. When you photograph a **flat surface** (like the ground) from any angle, the way it's distorted in the image follows one exact mathematical rule: a **homography**, a 3 × 3 transform that maps points on the plane to pixels and back. It's the same math that lets a phone "scan" a document and flatten it into a rectangle.

With four or more matching points we can solve for that transform. The checkerboard gives us dozens, so the solution is very stable. Once we have it, **any pixel that lies on the ground can be converted to a real position on the ground, in inches.** In effect, we "un-tilt" the camera view into a top-down map of the ground near the marker.

```
 Phone frame (tilted view)              Top-down ground map (after the homography)
 ┌──────────────────────────┐            wall line (marker edge) ───────────────
 │   wall                   │            ▓▓ marker                ● shrub base
 │▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁│                                     ↕ 3.2 ft
 │  ▓▓ marker      🌿 shrub │                                      
 │ (looks like a trapezoid) │
 └──────────────────────────┘
```

## 4. Measuring a hazard

1. **SAM 3.1** outlines the hazard (say, a shrub) in the frame and tracks it through the video.
2. We take the point where the shrub **touches the ground** that's **closest to the wall**: the lowest edge of its outline on the wall side.
3. The homography turns that pixel into a ground position in inches.
4. The distance to the **wall line** (the marker's wall edge, extended along the wall) is the hazard's distance from the house.
5. Because the shrub is tracked across many frames, we measure it in each frame where it and the marker are both visible, and combine the results.

## 5. Why a range, not one number

Every step has a little error: the outline's edge is a few pixels uncertain, the ground isn't perfectly flat, things farther from the marker are seen at a steeper angle. We carry those uncertainties through and report a **range with a confidence**, e.g. "2.5–3.5 ft · confident". The rules engine then treats it honestly:
- whole range inside the limit (e.g. all of it under 5 ft) → it breaks the rule,
- whole range outside → it's fine,
- range crosses the limit → **needs review** (go check with a tape measure).

It never pretends to know 4.0 ft vs 6.0 ft when it can't.

## 6. Why the placement rules matter

| Rule | Why |
|---|---|
| Flat on the ground, not leaned on the wall | The homography only works for the plane the marker lies on. We measure along the ground, so the marker must be on the ground. A sheet leaning on the wall would describe the wall's plane instead. |
| One edge touching the wall | It marks exactly where the wall meets the ground, so "distance from the wall" starts from a known line instead of a guess from the wall's outline. |
| One per side (or move it) | The ground-plane map is accurate near the marker and gets worse farther away, and the ground slopes differently around a building. |
| Print at 100% | If the printer shrinks the page to 97%, every distance comes out 3% wrong. The 1-inch check catches that. |
| Flat and uncreased | A curled or folded sheet isn't a plane, which bends the measurements. |

## 7. Limits (stated honestly)

- **Only things that touch the ground** can be measured this way (mulch edge, shrub base, woodpile, fence post). For things in the air, like branches near a roof, the measurement is approximate or a "check on site" item.
- **Sloped or uneven ground** adds error; that widens the range or lowers confidence.
- **Far from the marker** (more than ~15 ft), accuracy drops, which is fine because the strictest rules are within 5 ft.
- **No marker in view:** we fall back to a tape measure on the ground (scale only) or a standard door (about 6 ft 8 in tall), with lower confidence.

We check all of this against **tape-measured ground truth** from test footage; the target is that the true distance falls inside our range for at least 80% of hazards.
