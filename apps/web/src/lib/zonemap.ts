import type { Hazard, Side } from "./report-types";

// Schematic zone map: a piecewise scale so Zone 0 (0–5 ft) stays readable next to Zone 2 (to 100 ft).
// Breakpoints in feet and the share of the drawing radius each one reaches.
export const ZONE_BREAKS_FT = [0, 5, 30, 100] as const;
export const ZONE_BREAKS_FRAC = [0, 0.26, 0.66, 1] as const;

/** Shares of the radius per band. When every hazard is close to the wall, Zone 0 gets most of it. */
export type ZoneFracs = readonly [number, number, number, number];

/** Feet from the wall -> fraction (0..1) of the radius between the wall and the 100 ft line. */
export function zoneScale(ft: number, fracs: ZoneFracs = ZONE_BREAKS_FRAC): number {
  if (!Number.isFinite(ft) || ft <= 0) return 0;
  const last = ZONE_BREAKS_FT.length - 1;
  if (ft >= ZONE_BREAKS_FT[last]) return 1;
  for (let i = 1; i <= last; i++) {
    if (ft <= ZONE_BREAKS_FT[i]) {
      const f0 = ZONE_BREAKS_FT[i - 1];
      const f1 = ZONE_BREAKS_FT[i];
      return fracs[i - 1] + ((ft - f0) / (f1 - f0)) * (fracs[i] - fracs[i - 1]);
    }
  }
  return 1;
}

/** Hazard distance used for placing it: middle of its range, or "near the wall" when unmeasured. */
export function placeFt(h: Hazard): number {
  return h.distance_ft ? (h.distance_ft.min + h.distance_ft.max) / 2 : 2.5;
}

/** Pick band shares that give room to where the hazards actually are. */
export function fracsFor(hazards: readonly Hazard[]): ZoneFracs {
  const far = Math.max(0, ...hazards.map(placeFt));
  if (far <= 5) return [0, 0.6, 0.86, 1];
  if (far <= 30) return [0, 0.4, 0.82, 1];
  return ZONE_BREAKS_FRAC;
}

export interface MapGeometry {
  size: number; // square viewBox side
  buildingW: number;
  buildingH: number;
  radius: number; // drawing distance from the wall to the 100 ft line
}

export const DEFAULT_GEOMETRY: MapGeometry = { size: 440, buildingW: 150, buildingH: 120, radius: 140 };

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
export function bandRect(ft: number, g: MapGeometry = DEFAULT_GEOMETRY, fracs: ZoneFracs = ZONE_BREAKS_FRAC) {
  const b = buildingRect(g);
  const d = zoneScale(ft, fracs) * g.radius;
  return { x: b.x - d, y: b.y - d, w: b.w + 2 * d, h: b.h + 2 * d, r: d };
}

const MAPPABLE: Side[] = ["N", "E", "S", "W", "roof"];
export const PIN_R = 13; // pin radius in map units (the map is ~440 units wide)
export const PIN_GAP = 31; // centre-to-centre spacing: pins never touch

/** Several hazards on one wall in one zone, shown as a single tappable marker when they don't fit. */
export interface Cluster {
  side: Side;
  band: number; // 0 = Zone 0, 1 = Zone 1, 2 = Zone 2
  hazardIds: string[];
  x: number;
  y: number;
}

function sidePoint(side: Side, b: ReturnType<typeof buildingRect>, t: number, d: number, line: number, lines: number) {
  switch (side) {
    case "N":
      return { x: b.x + b.w / 2 + t, y: b.y - d };
    case "S":
      return { x: b.x + b.w / 2 + t, y: b.y + b.h + d };
    case "E":
      return { x: b.x + b.w + d, y: b.y + b.h / 2 + t };
    case "W":
      return { x: b.x - d, y: b.y + b.h / 2 + t };
    default: // roof
      return { x: b.x + b.w / 2 + t, y: b.y + b.h / 2 + (line - (lines - 1) / 2) * PIN_GAP };
  }
}

/**
 * Place numbered pins without overlaps. Each hazard goes on its side, at a depth inside its own
 * zone band (so a pin never looks like it's in the wrong zone), spread along the wall, in extra
 * lines further out when needed. When a wall's band can't hold its hazards with full spacing,
 * they become one cluster marker instead (tap it to get the wall's list). Hazards with no side
 * are left off the map (listed instead).
 */
export function layoutMap(
  hazards: readonly Hazard[],
  g: MapGeometry = DEFAULT_GEOMETRY,
  fracs: ZoneFracs = fracsFor(hazards),
): { pins: Pin[]; clusters: Cluster[] } {
  const b = buildingRect(g);
  const number = new Map(hazards.map((h, i) => [h.id, i + 1]));
  const pins: Pin[] = [];
  const clusters: Cluster[] = [];
  for (const side of MAPPABLE) {
    const onSide = hazards.filter((h) => h.side === side);
    if (!onSide.length) continue;
    const along = side === "N" || side === "S" || side === "roof" ? b.w : b.h;
    for (let band = 0; band < 3; band++) {
      const list = onSide
        .filter((h) => {
          const ft = placeFt(h);
          return band === 0 ? ft < 5 : band === 1 ? ft >= 5 && ft < 30 : ft >= 30;
        })
        .sort((a, c) => placeFt(a) - placeFt(c));
      if (!list.length) continue;
      const inner = fracs[band] * g.radius + PIN_R + 2;
      const outer = Math.max(fracs[band + 1] * g.radius - PIN_R - 2, inner);
      const perLine = Math.max(1, Math.floor((along + 2 * Math.min(inner, 20)) / PIN_GAP) + 1);
      const maxLines = side === "roof" ? 1 : Math.floor((outer - inner) / PIN_GAP) + 1;
      if (list.length > perLine * maxLines) {
        const mid = (inner + outer) / 2;
        clusters.push({ side, band, hazardIds: list.map((h) => h.id), ...sidePoint(side, b, 0, mid, 0, 1) });
        continue;
      }
      const lines = Math.ceil(list.length / perLine);
      list.forEach((h, i) => {
        const line = Math.floor(i / perLine);
        const inLine = Math.min(perLine, list.length - line * perLine);
        const t = -((inLine - 1) * PIN_GAP) / 2 + (i % perLine) * PIN_GAP;
        // one line sits at the hazard's own distance; several lines step out by a full gap
        const d =
          lines === 1
            ? Math.min(Math.max(zoneScale(placeFt(h), fracs) * g.radius, inner), outer)
            : inner + line * PIN_GAP;
        pins.push({ hazardId: h.id, n: number.get(h.id) ?? 0, ...sidePoint(side, b, t, d, line, lines) });
      });
    }
  }
  return { pins: pins.sort((a, b2) => a.n - b2.n), clusters };
}

/** Pins only (hazards that fit individually); see layoutMap for clusters. */
export function layoutPins(hazards: readonly Hazard[], g: MapGeometry = DEFAULT_GEOMETRY, fracs?: ZoneFracs): Pin[] {
  return layoutMap(hazards, g, fracs).pins;
}