import { formatDate } from "@/lib/format";
import type { Report } from "@/lib/report-types";

/** Compare with the building's previous finished scan: score change, cleared and new issues. */
export function SinceLastScan({ report, previous }: { report: Report; previous: { report: Report; createdAt: Date } | null }) {
  if (!previous) {
    return (
      <p className="text-sm text-muted">
        This is the first scan of this building. After fixes, rescan from the same spots: the rescan verifies each fix and updates the
        score.
      </p>
    );
  }
  const prev = previous.report;
  const open = (r: Report) => new Map(r.results.filter((x) => x.status !== "pass").map((x) => [x.rule_id, x]));
  const before = open(prev);
  const now = open(report);
  const cleared = [...before.values()].filter((r) => !now.has(r.rule_id));
  const added = [...now.values()].filter((r) => !before.has(r.rule_id));
  const delta = report.score.score - prev.score.score;
  return (
    <div className="flex flex-col gap-3 text-sm">
      <p className="text-ink">
        Compared with the scan on {formatDate(previous.createdAt)}: score {prev.score.score} → <strong>{report.score.score}</strong>{" "}
        <span className={delta > 0 ? "text-pass" : delta < 0 ? "text-fail" : "text-muted"}>
          ({delta > 0 ? "+" : ""}
          {delta})
        </span>
        . Hazards tracked: {prev.hazards.length} → {report.hazards.length}.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <h3 className="text-xs font-semibold text-muted uppercase">Cleared since then ({cleared.length})</h3>
          <ul className="mt-1 list-disc pl-5">
            {cleared.map((r) => (
              <li key={r.rule_id}>
                {r.title} <span className="text-muted">({r.citation_label})</span>
              </li>
            ))}
            {cleared.length === 0 && <li className="list-none text-muted">None yet.</li>}
          </ul>
        </div>
        <div>
          <h3 className="text-xs font-semibold text-muted uppercase">New since then ({added.length})</h3>
          <ul className="mt-1 list-disc pl-5">
            {added.map((r) => (
              <li key={r.rule_id}>
                {r.title} <span className="text-muted">({r.citation_label})</span>
              </li>
            ))}
            {added.length === 0 && <li className="list-none text-muted">Nothing new.</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}
