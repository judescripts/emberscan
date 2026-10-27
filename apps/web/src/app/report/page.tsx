import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { DeleteFailedScan } from "@/components/report/delete-failed-scan";
import { ButtonLink, Card, cx, PageHeader, Pill, SampleBadge, ScoreBadge, ShortDisclaimer, Skeleton } from "@/components/ui";
import { currentContext } from "@/lib/current";
import { listBuildings, listScans } from "@/lib/db/queries";
import type { Scan } from "@/lib/db/schema";
import { formatDate } from "@/lib/format";
import { scoreLabel } from "@/lib/score";
import { firstCitation, pipelineSummary } from "@/lib/summary";
import { BuildingCover } from "@/components/building-cover";

export const metadata: Metadata = { title: "Reports" };

export default function ReportsPage() {
  return (
    <main>
      <Suspense fallback={<Skeleton lines={3} />}>
        <Reports />
      </Suspense>
      <div className="mt-6">
        <ShortDisclaimer />
      </div>
    </main>
  );
}

/** Tiny score-over-time line for a building's finished scans (oldest to newest). */
function Trend({ scores }: { scores: number[] }) {
  if (scores.length < 2) return null;
  const w = 64;
  const h = 20;
  const pts = scores.map((s, i) => `${(i / (scores.length - 1)) * w},${h - (s / 100) * h}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-5 w-16" aria-label={`Score trend: ${scores.join(", ")}`} role="img">
      <polyline points={pts} fill="none" stroke="var(--brand)" strokeWidth={1.8} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

async function Reports() {
  const { db, current } = await currentContext();
  if (!current) return <ButtonLink href="/manage/new">+ New community</ButtonLink>;
  const list = await listBuildings(db, current.id);
  const all = await listScans(
    db,
    list.map((b) => b.id),
  ); // newest first

  const rows = list.map((b) => {
    const scans = all.filter((s) => s.buildingId === b.id);
    const done = scans.filter((s) => s.status === "done" && s.report);
    const latest = done[0] ?? null;
    const running = scans.find((s) => s.status === "queued" || s.status === "processing") ?? null;
    const earlier = scans.filter((s) => s !== latest && s !== running);
    return { b, latest, running, earlier, done };
  });
  // Buildings needing the most attention first; unscanned ones last.
  rows.sort((x, y) => (x.latest?.report?.score.score ?? 101) - (y.latest?.report?.score.score ?? 101));

  return (
    <>
      <PageHeader title="Reports" kicker={`${current.name} · ${list.length} building${list.length === 1 ? "" : "s"}`} />
      {list.length === 0 ? (
        <Card>
          <p className="text-muted">No buildings yet in {current.name}.</p>
          <ButtonLink href={`/manage/${current.id}`} className="mt-3">
            Add a building
          </ButtonLink>
        </Card>
      ) : (
        <ul className="flex flex-col gap-3">
          {rows.map(({ b, latest, running, earlier, done }) => {
            const r = latest?.report ?? null;
            const summary = r ? pipelineSummary(r) : null;
            const cite = r ? firstCitation(r) : null;
            return (
              <li key={b.id}>
                <Card className="flex flex-col gap-3">
                  <BuildingCover building={b} bleed className="[&_img]:max-h-40" />
                  <div className="flex items-start gap-3">
                    {r ? (
                      <ScoreBadge score={r.score.score} />
                    ) : (
                      <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-soft text-xs text-muted">—</span>
                    )}
                    <div className="min-w-0 flex-1">
                      <h2 className="flex flex-wrap items-center gap-2 font-bold text-ink">
                        {b.label}
                        {latest?.isSample && <SampleBadge />}
                      </h2>
                      {r && latest ? (
                        <>
                          <p className="flex flex-wrap items-center gap-2 text-sm text-muted">
                            <span>
                              {scoreLabel(r.score.score)} · scanned {formatDate(latest.createdAt)}
                            </span>
                            <Trend scores={[...done].reverse().map((s) => s.report!.score.score)} />
                          </p>
                          <div className="mt-1 flex flex-wrap gap-1.5">
                            {r.score.fails > 0 && <Pill tone="fail">{r.score.fails} {r.score.fails === 1 ? "fail" : "fails"}</Pill>}
                            {r.score.reviews > 0 && <Pill tone="review">{r.score.reviews} need review</Pill>}
                          </div>
                          {summary && <p className="mt-1 text-sm text-muted">{summary.tracked}</p>}
                          {cite && <p className="text-xs text-muted">Top issue: {cite}</p>}
                        </>
                      ) : (
                        <p className="text-sm text-muted">No finished scan yet.</p>
                      )}
                    </div>
                  </div>

                  {running && (
                    <Link href={`/scan/${running.id}`} className="text-sm font-semibold text-brand underline underline-offset-2">
                      Scan in progress · {Math.round((running.progress ?? 0) * 100)}% ({running.stage ?? "queued"})
                    </Link>
                  )}

                  <div className="flex flex-wrap gap-2">
                    {latest && <ButtonLink href={`/report/${latest.id}`}>Open report</ButtonLink>}
                    <ButtonLink href={`/scan?building=${b.id}`} variant="secondary">
                      {latest ? "Rescan" : "Scan now"}
                    </ButtonLink>
                  </div>

                  {earlier.length > 0 && <History scans={earlier} newest={latest} />}
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}

/** Date and time, so several scans on one day stay distinguishable (California rule packs: Pacific time). */
function when(d: Date | string) {
  return new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/Los_Angeles" });
}

function History({ scans, newest }: { scans: Scan[]; newest: Scan | null }) {
  // each finished scan compared with the one before it (scans are newest first)
  const finished = scans.filter((s) => s.report);
  const failed = scans.filter((s) => s.status === "failed").length;
  return (
    <details className="group rounded-xl border border-line">
      <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 text-sm font-semibold text-ink [&::-webkit-details-marker]:hidden">
        <span>
          Earlier scans ({finished.length})
          {failed > 0 && <span className="font-normal text-muted"> · {failed} failed attempt{failed === 1 ? "" : "s"}</span>}
        </span>
        <span aria-hidden className="text-muted transition-transform group-open:rotate-180">
          ▾
        </span>
      </summary>
      <ol className="divide-y divide-line border-t border-line">
        {scans.map((s, i) => {
          const r = s.report;
          const next = i === 0 ? newest : scans.slice(0, i).reverse().find((x) => x.report) ?? newest;
          const delta = r && next?.report ? next.report.score.score - r.score.score : null;
          return (
            <li key={s.id} className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm">
              {r ? (
                <Link href={`/report/${s.id}`} className="flex min-w-0 flex-1 items-center gap-2 hover:underline">
                  <span className="w-32 shrink-0 text-muted tabular-nums">{when(s.createdAt)}</span>
                  <span className="font-semibold text-ink tabular-nums">{r.score.score}</span>
                  <span className="truncate text-muted">{scoreLabel(r.score.score)}</span>
                </Link>
              ) : (
                <span className="flex min-w-0 flex-1 items-center gap-2">
                  <span className="w-32 shrink-0 text-muted tabular-nums">{when(s.createdAt)}</span>
                  <span className={cx("font-semibold", s.status === "failed" ? "text-fail" : "text-muted")}>
                    {s.status === "failed" ? "Failed" : "Didn't finish"}
                  </span>
                </span>
              )}
              {delta !== null && delta !== 0 && (
                <span className={cx("text-xs font-semibold", delta > 0 ? "text-pass" : "text-fail")}>
                  {delta > 0 ? `then +${delta}` : `then ${delta}`}
                </span>
              )}
              {s.status === "failed" && <DeleteFailedScan scanId={s.id} />}
            </li>
          );
        })}
      </ol>
    </details>
  );
}
