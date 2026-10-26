import type { Hazard, RuleResult } from "@/lib/report-types";
import { hazardStatus } from "@/lib/score";
import { zoneScale } from "@/lib/zonemap";

const FILL = { fail: "var(--fail)", "needs-review": "var(--review)", pass: "var(--pass)" } as const;
const BANDS = [
  { from: 0, to: 5, fill: "var(--zone0)", label: "Zone 0 · 0–5 ft" },
  { from: 5, to: 30, fill: "var(--zone1)", label: "Zone 1 · 5–30 ft" },
  { from: 30, to: 100, fill: "var(--zone2)", label: "Zone 2 · 30–100 ft" },
];

/**
 * Distance view for when the scan doesn't know which side of the building each hazard is on:
 * the wall at the left, zone bands outward, and every measured hazard as its distance range
 * with a numbered pin. Same stretched scale as the zone map, so Zone 0 stays readable.
 */
export function WallProfile({ hazards, all, results }: { hazards: Hazard[]; all: Hazard[]; results: RuleResult[] }) {
  const W = 420;
  const left = 34; // wall line
  const span = W - left - 14;
  const top = 48;
  const row = 26;
  const H = top + Math.max(hazards.length, 1) * row + 12;
  const x = (ft: number) => left + zoneScale(ft) * span;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mx-auto w-full max-w-md" role="img" aria-labelledby="wallprofile-title">
      <title id="wallprofile-title">{`Distance from the wall for ${hazards.length} measured hazards`}</title>
      {BANDS.map((b) => (
        <g key={b.from}>
          <rect x={x(b.from)} y={top - 22} width={x(b.to) - x(b.from)} height={H - top + 18} fill={b.fill} stroke="var(--zone-line)" strokeWidth={0.6} />
          <text x={x(b.from) + 5} y={top - 9} fontSize={10} fontWeight={600} fill="var(--muted)">
            {b.label}
          </text>
        </g>
      ))}
      <rect x={left - 10} y={top - 22} width={10} height={H - top + 18} fill="var(--text)" />
      <text x={left - 10} y={top - 30} fontSize={10} fontWeight={700} fill="var(--text)">
        Wall
      </text>
      {hazards.map((h, i) => {
        const n = all.indexOf(h) + 1;
        const status = hazardStatus(h.id, results);
        const fill = status ? FILL[status] : "var(--muted)";
        const r = h.distance_ft!;
        const y = top + i * row + row / 2;
        const x0 = x(r.min);
        const x1 = Math.max(x(r.max), x0 + 2);
        const mid = (x0 + x1) / 2;
        return (
          <a key={h.id} href={`#${h.id}`} aria-label={`${n}. ${h.label}: ${r.min}–${r.max} ft from the wall. Go to evidence.`}>
            <title>{`${n}. ${h.label}: ${r.min}–${r.max} ft`}</title>
            <line x1={x0} y1={y} x2={x1} y2={y} stroke={fill} strokeWidth={4} strokeLinecap="round" opacity={0.55} />
            {h.zone_uncertain && <circle cx={mid} cy={y} r={13} fill="none" stroke={fill} strokeWidth={1.5} strokeDasharray="3 2.5" />}
            <circle cx={mid} cy={y} r={10} fill={fill} stroke="var(--surface)" strokeWidth={2} />
            <text x={mid} y={y + 4} textAnchor="middle" fontSize={10.5} fontWeight={700} fill="var(--surface)">
              {n}
            </text>
            <text x={Math.min(x1 + 14, W - 4)} y={y + 4} fontSize={10} fill="var(--text)" textAnchor={x1 + 14 > W - 90 ? "end" : "start"}>
              {h.label}
            </text>
          </a>
        );
      })}
    </svg>
  );
}
