import Link from "next/link";
import { Suspense } from "react";
import { BuildingNotePanel, ZoneChip } from "@/components/building-note";
import { ButtonLink, Card, PageHeader, Pill, SampleBadge, ScoreBadge, ShortDisclaimer, Skeleton } from "@/components/ui";
import { currentContext } from "@/lib/current";
import { latestDone, listBuildings, listScans } from "@/lib/db/queries";
import { scoreLabel } from "@/lib/score";
import { firstCitation, pipelineSummary } from "@/lib/summary";

export default function BuildingsPage() {
  return (
    <main>
      <Suspense fallback={<Skeleton lines={3} />}>
        <Buildings />
      </Suspense>
    </main>
  );
}

async function Buildings() {
  const { db, current } = await currentContext();
  if (!current) {
    return (
      <Card>
        <h1 className="text-xl font-bold">Start with a community</h1>
        <p className="mt-1 text-muted">Add your HOA, condo, home or commercial site, then its buildings. Each building gets its own scan.</p>
        <ButtonLink href="/manage/new" className="mt-4">
          + New community
        </ButtonLink>
      </Card>
    );
  }
  const list = await listBuildings(db, current.id);
  const allScans = await listScans(
    db,
    list.map((b) => b.id),
  );

  return (
    <>
      <PageHeader
        title={current.name}
        kicker={
          <span className="flex flex-wrap items-center gap-2">
            {current.isSample && <SampleBadge />}
            <span>
              {current.type} · {current.place || "No place set"} · {list.length} building{list.length === 1 ? "" : "s"}
            </span>
          </span>
        }
      >
        <ButtonLink href={`/manage/${current.id}`} variant="secondary">
          Add or edit buildings
        </ButtonLink>
      </PageHeader>

      {list.length === 0 && (
        <Card>
          <p className="text-muted">No buildings yet.</p>
          <ButtonLink href={`/manage/${current.id}`} className="mt-3">
            Add a building
          </ButtonLink>
        </Card>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {list.map((b) => {
          const scan = latestDone(allScans, b.id);
          const running = allScans.find((s) => s.buildingId === b.id && (s.status === "queued" || s.status === "processing"));
          const report = scan?.report;
          const summary = report ? pipelineSummary(report) : null;
          const cite = report ? firstCitation(report) : null;
          return (
            <li key={b.id}>
              <Card className="flex h-full flex-col gap-3">
                <div className="flex items-start gap-3">
                  {report ? (
                    <ScoreBadge score={report.score.score} />
                  ) : (
                    <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-soft text-xs font-semibold text-muted">
                      —
                    </span>
                  )}
                  <div className="min-w-0 flex-1">
                    <h2 className="font-bold text-ink">{b.label}</h2>
                    {b.units && <p className="text-sm text-muted">Units {b.units}</p>}
                    {b.address && <p className="text-sm text-muted">{b.address}</p>}
                    {b.note?.hazard_class && (
                      <p className="mt-1">
                        <ZoneChip note={b.note} />
                      </p>
                    )}
                    {report ? (
                      <p className="mt-1 flex flex-wrap items-center gap-1.5 text-sm font-semibold">
                        {scoreLabel(report.score.score)}
                        {scan?.isSample && <SampleBadge />}
                      </p>
                    ) : (
                      <p className="mt-1 text-sm text-muted">
                        Not scanned yet ·{" "}
                        <Link href={`/scan?building=${b.id}`} className="font-semibold text-brand underline underline-offset-2">
                          Scan now
                        </Link>
                      </p>
                    )}
                  </div>
                </div>
                {report && summary && (
                  <div className="flex flex-col gap-1.5 text-sm">
                    <div className="flex flex-wrap gap-1.5">
                      {report.score.fails > 0 && <Pill tone="fail">{report.score.fails} {report.score.fails === 1 ? "fail" : "fails"}</Pill>}
                      {report.score.reviews > 0 && <Pill tone="review">{report.score.reviews} need review</Pill>}
                      {report.score.passes > 0 && <Pill tone="pass">{report.score.passes} pass</Pill>}
                    </div>
                    <p className="text-muted">{summary.tracked}</p>
                    {summary.closest && <p className="text-muted">Closest: {summary.closest}</p>}
                    {cite && <p className="text-xs text-muted">Top issue: {cite}</p>}
                  </div>
                )}
                {b.address && (
                  <BuildingNotePanel buildingId={b.id} address={b.address} note={b.note ?? null} compact />
                )}
                {running && (
                  <Link href={`/scan/${running.id}`} className="text-sm font-semibold text-brand underline underline-offset-2">
                    Scan in progress · {Math.round((running.progress ?? 0) * 100)}% ({running.stage ?? "queued"})
                  </Link>
                )}
                <div className="mt-auto flex flex-wrap gap-2">
                  {scan && (
                    <ButtonLink href={`/report/${scan.id}`} variant="primary">
                      Open report
                    </ButtonLink>
                  )}
                  <ButtonLink href={`/scan?building=${b.id}`} variant="secondary">
                    {scan ? "Rescan" : "Scan now"}
                  </ButtonLink>
                </div>
              </Card>
            </li>
          );
        })}
      </ul>
      <div className="mt-6">
        <ShortDisclaimer />
      </div>
    </>
  );
}
