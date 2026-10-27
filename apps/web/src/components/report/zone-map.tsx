import { sideWords } from "@/lib/format";
import type { Hazard, RuleResult } from "@/lib/report-types";
import { hazardStatus } from "@/lib/score";
import { bandRect, buildingRect, DEFAULT_GEOMETRY, fracsFor, layoutMap, PIN_R } from "@/lib/zonemap";
import { WallProfile } from "./wall-profile";
import { ZoomableMap } from "./zoomable-map";

const PIN_FILL = { fail: "var(--fail)", "needs-review": "var(--review)", pass: "var(--pass)" } as const;

const BANDS = [
  { ft: 100, fill: "var(--zone2)", label: "Zone 2 · 30–100 ft" },
  { ft: 30, fill: "var(--zone1)", label: "Zone 1 · 5–30 ft" },
  { ft: 5, fill: "var(--zone0)", label: "Zone 0 · 0–5 ft" },
];

/** Top-down schematic. Not to scale: distances are stretched near the house so Zone 0 is readable. */
export function ZoneMap({ hazards: all, results, buildingLabel }: { hazards: Hazard[]; results: RuleResult[]; buildingLabel: string }) {
  // Only what needs attention goes on the map; hazards that pass every rule are just counted.
  const hazards = all.filter((h) => {
    const s = hazardStatus(h.id, results);
    return s === "fail" || s === "needs-review";
  });
  const okCount = all.length - hazards.length;
  const g = DEFAULT_GEOMETRY;
  const b = buildingRect(g);
  const fracs = fracsFor(hazards);
  // numbers match the evidence list, which numbers every tracked hazard
  const layout = layoutMap(hazards, g, fracs);
  const pins = layout.pins.map((p) => ({ ...p, n: all.findIndex((h) => h.id === p.hazardId) + 1 }));
  const clusters = layout.clusters;
  const placed = new Set([...pins.map((p) => p.hazardId), ...clusters.flatMap((c) => c.hazardIds)]);
  const unmapped = hazards.filter((h) => !placed.has(h.id));
  // Crop to the building plus what's drawn around it, so pins are as large as possible on a phone.
  const pad = PIN_R + 22;
  const xs = [b.x, b.x + b.w, ...pins.map((p) => p.x), ...clusters.map((c) => c.x)];
  const ys = [b.y, b.y + b.h, ...pins.map((p) => p.y), ...clusters.map((c) => c.y)];
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
  const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  const half = Math.min(g.size / 2, Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) / 2 + pad);
  const vx = Math.max(0, Math.min(g.size - 2 * half, cx - half));
  const vy = Math.max(0, Math.min(g.size - 2 * half, cy - half));
  const view = `${vx} ${vy} ${2 * half} ${2 * half}`;
  const worst = (ids: string[]) =>
    ids.some((id) => hazardStatus(id, results) === "fail") ? PIN_FILL.fail : PIN_FILL["needs-review"];
  const byId = new Map(all.map((h) => [h.id, h]));

  if (pins.length === 0 && clusters.length === 0) {
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
          <WallProfile hazards={measured} all={all} results={results} />
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
                  {all.indexOf(h) + 1}. {h.label}
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
      <ZoomableMap fullView={`0 0 ${g.size} ${g.size}`} fitView={view}>
        <title id="zonemap-title">{`Zone map for ${buildingLabel}`}</title>
        <desc id="zonemap-desc">
          Top-down sketch of the building with Zone 0, 1 and 2 bands and {pins.length} numbered hazard pins. Each pin links to its
          evidence below.
        </desc>
        {BANDS.map((band) => {
          const r = bandRect(band.ft, g, fracs);
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
        {pins.map((p) => {
          const h = byId.get(p.hazardId)!;
          const status = hazardStatus(h.id, results);
          const fill = status ? PIN_FILL[status] : "var(--muted)";
          return (
            <a key={p.hazardId} href={`#${p.hazardId}`} aria-label={`Pin ${p.n}: ${h.label}. Go to evidence.`}>
              <title>{`${p.n}. ${h.label}`}</title>
              {h.zone_uncertain && (
                <circle cx={p.x} cy={p.y} r={PIN_R + 4} fill="none" stroke={fill} strokeWidth={1.5} strokeDasharray="3 2.5" />
              )}
              <circle cx={p.x} cy={p.y} r={PIN_R} fill={fill} stroke="var(--surface)" strokeWidth={2} />
              <text x={p.x} y={p.y + 4.5} textAnchor="middle" fontSize={12.5} fontWeight={700} fill="var(--surface)">
                {p.n}
              </text>
            </a>
          );
        })}
        {clusters.map((c) => (
          <a
            key={`${c.side}-${c.band}`}
            href={`#wall-${c.side}`}
            aria-label={`${c.hazardIds.length} hazards on the ${sideWords(c.side).toLowerCase()} in Zone ${c.band}. Show the list.`}
          >
            <title>{`${c.hazardIds.length} hazards here: tap for the list`}</title>
            <circle cx={c.x} cy={c.y} r={PIN_R + 9} fill={worst(c.hazardIds)} stroke="var(--surface)" strokeWidth={3} />
            <circle cx={c.x} cy={c.y} r={PIN_R + 13} fill="none" stroke={worst(c.hazardIds)} strokeWidth={1.5} opacity={0.5} />
            <text x={c.x} y={c.y + 5.5} textAnchor="middle" fontSize={16} fontWeight={800} fill="var(--surface)">
              {c.hazardIds.length}
            </text>
          </a>
        ))}
      </ZoomableMap>
      <ul className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs text-muted" aria-label="Legend">
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-fail" aria-hidden /> Fails a rule in force
        </li>
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-review" aria-hidden /> Needs review
        </li>
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full border border-dashed border-muted" aria-hidden /> Near a zone line
        </li>
      </ul>
      <p className="text-center text-xs text-muted">
        Sketch, not to scale: zones are stretched so the closest ones are readable. Use Zoom in for a closer look.
        {clusters.length > 0 && " Big markers group a crowded wall: tap one for its list."} Each wall is listed below.
        {okCount > 0 && ` ${okCount} more seen with no issue (listed under Evidence).`}
      </p>
      {(["N", "E", "S", "W"] as const).map((side) => {
        const onSide = hazards.filter((h) => h.side === side);
        if (!onSide.length) return null;
        const measured = onSide.filter((h) => h.distance_ft);
        return (
          <div key={side} id={`wall-${side}`} className="mt-2 scroll-mt-28 border-t border-line pt-3">
            <h3 className="mb-1 text-sm font-semibold text-ink">
              {sideWords(side)} · {onSide.length} to look at
            </h3>
{measured.length > 0 && <WallProfile hazards={measured} all={all} results={results} />}
            {[
              { title: `On the chart (${measured.length})`, items: measured },
              { title: `Not measured · check on site (${onSide.length - measured.length})`, items: onSide.filter((h) => !h.distance_ft) },
            ]
              .filter((grp) => grp.items.length > 0)
              .map((grp) => (
                <div key={grp.title} className="mt-3">
                  <p className="mb-1 text-xs font-semibold text-muted">{grp.title}</p>
                  <ul className="flex flex-col divide-y divide-line rounded-xl border border-line">
                    {grp.items.map((h) => {
                      const n = all.indexOf(h) + 1;
                      const s = hazardStatus(h.id, results);
                      return (
                        <li key={h.id}>
                          <a href={`#${h.id}`} className="flex min-h-11 items-center gap-3 px-3 py-2 text-sm hover:bg-soft">
                            <span
                              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-surface"
                              style={{ background: s ? PIN_FILL[s] : "var(--muted)" }}
                            >
                              {n}
                            </span>
                            <span className="min-w-0 flex-1 text-ink">{h.label}</span>
                            <span className="shrink-0 text-xs text-muted">
                              {h.distance_ft ? `${h.distance_ft.min}–${h.distance_ft.max} ft` : "no marker in view"}
                            </span>
                          </a>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
          </div>
        );
      })}
      {unmapped.length > 0 && (
        <p className="text-xs text-muted">
          Side not known:{" "}
          {unmapped.map((h, i) => (
            <span key={h.id}>
              {i > 0 && ", "}
              <a className="underline" href={`#${h.id}`}>
                {all.indexOf(h) + 1}. {h.label}
              </a>
            </span>
          ))}{" "}
          ({sideWords("unknown")})
        </p>
      )}
    </div>
  );
}
