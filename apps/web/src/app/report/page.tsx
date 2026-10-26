import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { ButtonLink, Card, PageHeader, Pill, SampleBadge, ScoreBadge, ShortDisclaimer, Skeleton } from "@/components/ui";
import { currentContext } from "@/lib/current";
import { listBuildings, listScans } from "@/lib/db/queries";
import { formatDate } from "@/lib/format";
import { scoreLabel } from "@/lib/score";
import { firstCitation, pipelineSummary } from "@/lib/summary";

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

async function Reports() {
  const { db, current } = await currentContext();
  if (!current) return <ButtonLink href="/manage/new">+ New community</ButtonLink>;
  const list = await listBuildings(db, current.id);
  const label = new Map(list.map((b) => [b.id, b.label]));
  const all = await listScans(
    db,
    list.map((b) => b.id),
  );
  const latestIds = new Set(list.map((b) => all.find((s) => s.buildingId === b.id && s.report)?.id).filter(Boolean));

  return (
    <>
      <PageHeader title="Reports" kicker={current.name} />
      {all.length === 0 ? (
        <Card>
          <p className="text-muted">No scans yet in {current.name}.</p>
          <ButtonLink href="/scan" className="mt-3">
            Start a scan
          </ButtonLink>
        </Card>
      ) : (
        <ul className="flex flex-col gap-3">
          {all.map((s) => {
            const r = s.report;
            const summary = r ? pipelineSummary(r) : null;
            const cite = r ? firstCitation(r) : null;
            const href = r ? `/report/${s.id}` : `/scan/${s.id}`;
            return (
              <li key={s.id}>
                <Link href={href} className="block rounded-2xl border border-line bg-surface p-4 hover:border-brand">
                  <div className="flex items-start gap-3">
                    {r ? <ScoreBadge score={r.score.score} /> : <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-soft text-xs text-muted">{Math.round(s.progress * 100)}%</span>}
                    <div className="min-w-0 flex-1">
                      <p className="flex flex-wrap items-center gap-2 font-bold text-ink">
                        {label.get(s.buildingId)}
                        {s.isSample && <SampleBadge />}
                        {latestIds.has(s.id) && <Pill>Latest</Pill>}
                      </p>
                      <p className="text-sm text-muted">
                        {formatDate(s.createdAt)} · {r ? scoreLabel(r.score.score) : s.status === "failed" ? "Failed" : `In progress: ${s.stage ?? "queued"}`}
                      </p>
                      {summary && <p className="mt-1 text-sm text-muted">{summary.tracked}</p>}
                      {cite && <p className="text-xs text-muted">Top issue: {cite}</p>}
                    </div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
