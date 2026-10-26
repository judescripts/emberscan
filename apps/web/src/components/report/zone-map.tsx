import { sideWords } from "@/lib/format";
import type { Hazard, RuleResult } from "@/lib/report-types";
import { hazardStatus } from "@/lib/score";
import { bandRect, buildingRect, DEFAULT_GEOMETRY, layoutPins } from "@/lib/zonemap";
import { WallProfile } from "./wall-profile";

const PIN_FILL = { fail: "var(--fail)", "needs-review": "var(--review)", pass: "var(--pass)" } as const;

const BANDS = [
  { ft: 100, fill: "var(--zone2)", label: "Zone 2 · 30–100 ft" },
  { ft: 30, fill: "var(--zone1)", label: "Zone 1 · 5–30 ft" },
  { ft: 5, fill: "var(--zone0)", label: "Zone 0 · 0–5 ft" },
];

/** Top-down schematic. Not to scale: distances are stretched near the house so Zone 0 is readable. */
export function ZoneMap({ hazards, results, buildingLabel }: { hazards: Hazard[]; results: RuleResult[]; buildingLabel: string }) {
  const g = DEFAULT_GEOMETRY;
  const b = buildingRect(g);
  const pins = layoutPins(hazards, g);
  const unmapped = hazards.filter((h) => !pins.some((p) => p.hazardId === h.id));
  const byId = new Map(hazards.map((h) => [h.id, h]));

  if (pins.length === 0) {
    // No sides recorded: a top-down map would be empty, so show distance from the wall instead.
    const measured = hazards.filter((h) => h.distance_ft);
    const rest = hazards.filter((h) => !h.distance_ft);
    return (
      <div className="flex flex-col gap-3">
        <p className="text-sm text-muted">
          This scan didn&apos;t record which side of the building each hazard is on, so here&apos;s each measured hazard&apos;s
          distance from the wall. Tag clips with their side when you upload (or say “north side…” while filming) to get the
          top-down map.
        </p>
        {measured.length > 0 ? (
          <WallProfile hazards={measured} all={hazards} results={results} />
        ) : (
          <p className="text-sm text-muted">No hazards were measured with the marker in this scan.</p>
        )}
        <p className="text-center text-xs text-muted">Not to scale: the first 5 ft are stretched so Zone 0 is readable.</p>
        {rest.length > 0 && (
          <p className="text-xs text-muted">
            Not measured:{" "}
            {rest.map((h, i) => (
              <span key={h.id}>
                {i > 0 && ", "}
                <a className="underline" href={`#${h.id}`}>
                  {hazards.indexOf(h) + 1}. {h.label}
                </a>
              </span>
            ))}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <svg
        viewBox={`0 0 ${g.size} ${g.size}`}
        className="mx-auto w-full max-w-md"
        role="img"
        aria-labelledby="zonemap-title zonemap-desc"
      >
        <title id="zonemap-title">{`Zone map for ${buildingLabel}`}</title>
        <desc id="zonemap-desc">
          Top-down sketch of the building with Zone 0, 1 and 2 bands and {pins.length} numbered hazard pins. Each pin links to its
          evidence below.
        </desc>
        {BANDS.map((band) => {
          const r = bandRect(band.ft, g);
          return (
            <g key={band.ft}>
              <rect x={r.x} y={r.y} width={r.w} height={r.h} rx={Math.min(r.r, 40)} fill={band.fill} stroke="var(--zone-line)" strokeWidth={0.8} />
              <text x={r.x + 8} y={r.y + 13} fontSize={10.5} fill="var(--muted)" fontWeight={600}>
                {band.label}
              </text>
            </g>
          );
        })}
        <rect x={b.x} y={b.y} width={b.w} height={b.h} rx={3} fill="var(--surface)" stroke="var(--text)" strokeWidth={1.6} />
        <text x={g.size / 2} y={g.size / 2 + 4} textAnchor="middle" fontSize={11} fill="var(--muted)" fontWeight={600}>
          Building
        </text>
        <g aria-hidden>
          <text x={g.size - 16} y={20} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--text)">
            N
          </text>
          <path d={`M${g.size - 16} 24 l-4 9 h8 z`} fill="var(--text)" />
        </g>
        {pins.map((p) => {
          const h = byId.get(p.hazardId)!;
          const status = hazardStatus(h.id, results);
          const fill = status ? PIN_FILL[status] : "var(--muted)";
          return (
            <a key={p.hazardId} href={`#${p.hazardId}`} aria-label={`Pin ${p.n}: ${h.label}. Go to evidence.`}>
              <title>{`${p.n}. ${h.label}`}</title>
              {h.zone_uncertain && (
                <circle cx={p.x} cy={p.y} r={15} fill="none" stroke={fill} strokeWidth={1.5} strokeDasharray="3 2.5" />
              )}
              <circle cx={p.x} cy={p.y} r={11} fill={fill} stroke="var(--surface)" strokeWidth={2} />
              <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={11.5} fontWeight={700} fill="var(--surface)">
                {p.n}
              </text>
            </a>
          );
        })}
      </svg>
      <ul className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs text-muted" aria-label="Legend">
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-fail" aria-hidden /> Fails a rule in force
        </li>
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-review" aria-hidden /> Needs review
        </li>
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-pass" aria-hidden /> Passes
        </li>
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full border border-dashed border-muted" aria-hidden /> Near a zone line
        </li>
      </ul>
      <p className="text-center text-xs text-muted">Sketch, not to scale: the first 5 ft are stretched so Zone 0 is readable.</p>
      {unmapped.length > 0 && (
        <p className="text-xs text-muted">
          Side not known:{" "}
          {unmapped.map((h, i) => (
            <span key={h.id}>
              {i > 0 && ", "}
              <a className="underline" href={`#${h.id}`}>
                {hazards.indexOf(h) + 1}. {h.label}
              </a>
            </span>
          ))}{" "}
          ({sideWords("unknown")})
        </p>
      )}
    </div>
  );
}
