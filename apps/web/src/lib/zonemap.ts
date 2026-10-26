import type { Hazard, Side } from "./report-types";

// Schematic zone map: a piecewise scale so Zone 0 (0–5 ft) stays readable next to Zone 2 (to 100 ft).
// Breakpoints in feet and the share of the drawing radius each one reaches.
export const ZONE_BREAKS_FT = [0, 5, 30, 100] as const;
export const ZONE_BREAKS_FRAC = [0, 0.26, 0.66, 1] as const;

/** Feet from the wall -> fraction (0..1) of the radius between the wall and the 100 ft line. */
export function zoneScale(ft: number): number {
  if (!Number.isFinite(ft) || ft <= 0) return 0;
  const last = ZONE_BREAKS_FT.length - 1;
  if (ft >= ZONE_BREAKS_FT[last]) return 1;
  for (let i = 1; i <= last; i++) {
    if (ft <= ZONE_BREAKS_FT[i]) {
      const f0 = ZONE_BREAKS_FT[i - 1];
      const f1 = ZONE_BREAKS_FT[i];
      const p0 = ZONE_BREAKS_FRAC[i - 1];
      const p1 = ZONE_BREAKS_FRAC[i];
      return p0 + ((ft - f0) / (f1 - f0)) * (p1 - p0);
    }
  }
  return 1;
}

export interface MapGeometry {
  size: number; // square viewBox side
  buildingW: number;
  buildingH: number;
  radius: number; // drawing distance from the wall to the 100 ft line
}

export const DEFAULT_GEOMETRY: MapGeometry = { size: 420, buildingW: 120, buildingH: 76, radius: 140 };

export interface Pin {
  hazardId: string;
  n: number; // 1-based number shown on the pin
  x: number;
  y: number;
}

export function buildingRect(g: MapGeometry = DEFAULT_GEOMETRY) {
  const x = (g.size - g.buildingW) / 2;
  const y = (g.size - g.buildingH) / 2;
  return { x, y, w: g.buildingW, h: g.buildingH };
}

/** Rectangle of a band's outer edge at `ft` from the wall. */
export function bandRect(ft: number, g: MapGeometry = DEFAULT_GEOMETRY) {
  const b = buildingRect(g);
  const d = zoneScale(ft) * g.radius;
  return { x: b.x - d, y: b.y - d, w: b.w + 2 * d, h: b.h + 2 * d, r: d };
}

const MAPPABLE: Side[] = ["N", "E", "S", "W", "roof"];

/**
 * Place numbered pins: each hazard sits on its side at the middle of its measured distance range,
 * spread evenly along that side. Hazards with no side are left off the map (listed instead).
 */
export function layoutPins(hazards: readonly Hazard[], g: MapGeometry = DEFAULT_GEOMETRY): Pin[] {
  const b = buildingRect(g);
  const bySide = new Map<Side, Hazard[]>();
  hazards.forEach((h) => {
    if (!MAPPABLE.includes(h.side)) return;
    bySide.set(h.side, [...(bySide.get(h.side) ?? []), h]);
  });
  const number = new Map(hazards.map((h, i) => [h.id, i + 1]));
  const pins: Pin[] = [];
  for (const [side, list] of bySide) {
    list.forEach((h, i) => {
      const along = (i + 1) / (list.length + 1);
      const range = h.distance_ft;
      const mid = range ? (range.min + range.max) / 2 : 2.5;
      // keep pins just off the wall so they don't sit on the outline
      const d = Math.max(zoneScale(mid) * g.radius, 9);
      let x: number;
      let y: number;
      switch (side) {
        case "N":
          x = b.x + b.w * along;
          y = b.y - d;
          break;
        case "S":
          x = b.x + b.w * along;
          y = b.y + b.h + d;
          break;
        case "E":
          x = b.x + b.w + d;
          y = b.y + b.h * along;
          break;
        case "W":
          x = b.x - d;
          y = b.y + b.h * along;
          break;
        default: // roof
          x = b.x + b.w * along;
          y = b.y + b.h / 2;
      }
      pins.push({ hazardId: h.id, n: number.get(h.id) ?? 0, x, y });
    });
  }
  return pins.sort((a, b2) => a.n - b2.n);
}
