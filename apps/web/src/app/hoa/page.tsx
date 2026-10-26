import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { TaskList, type TaskRow } from "@/components/hoa/task-list";
import { ButtonLink, Card, PageHeader, SampleBadge, ScoreBadge, SectionTitle, ShortDisclaimer, Skeleton } from "@/components/ui";
import { currentContext } from "@/lib/current";
import { latestDone, listBuildings, listScans, listTasks } from "@/lib/db/queries";

export const metadata: Metadata = { title: "HOA tasks" };

export default function HoaPage() {
  return (
    <main>
      <Suspense fallback={<Skeleton lines={4} />}>
        <Hoa />
      </Suspense>
      <div className="mt-6">
        <ShortDisclaimer />
      </div>
    </main>
  );
}

async function Hoa() {
  const { db, current } = await currentContext();
  if (!current) return <ButtonLink href="/manage/new">+ New community</ButtonLink>;
  const list = await listBuildings(db, current.id);
  const ids = list.map((b) => b.id);
  const all = await listScans(db, ids);
  const tasks = await listTasks(db, ids);

  const rows = list.map((b) => {
    const scan = latestDone(all, b.id);
    const bt = tasks.filter((t) => t.buildingId === b.id && t.status !== "verified" && t.status !== "wontfix");
    return {
      building: b,
      scan,
      hoa: bt.filter((t) => t.responsibility === "HOA").length,
      owner: bt.filter((t) => t.responsibility === "Owner").length,
      unclear: bt.filter((t) => t.responsibility === "Unclear").length,
    };
  });

  const taskRows: TaskRow[] = tasks.map((t) => {
    const scan = latestDone(all, t.buildingId);
    const result = scan?.report?.results.find((r) => r.rule_id === t.ruleId);
    return {
      id: t.id,
      buildingId: t.buildingId,
      buildingLabel: list.find((b) => b.id === t.buildingId)?.label ?? "",
      reportId: scan?.id ?? null,
      title: t.title,
      ruleId: t.ruleId,
      citationLabel: result?.citation_label ?? null,
      citationUrl: result?.citation_url ?? null,
      ruleStatus: result?.status ?? null,
      responsibility: t.responsibility,
      owner: t.owner,
      status: t.status,
      required: t.required,
      lastNote: t.notes.at(-1) ?? null,
    };
  });

  return (
    <>
      <PageHeader
        title="HOA tasks"
        kicker={
          <span className="flex items-center gap-2">
            {current.isSample && <SampleBadge />}
            {current.name}
          </span>
        }
      />
      <Card className="mb-5">
        <SectionTitle kicker="By building">Where things stand</SectionTitle>
        <div className="-mx-4 overflow-x-auto px-4">
          <table className="w-full min-w-[560px] text-left text-sm">
            <caption className="sr-only">Buildings with latest score, rule results and open task counts</caption>
            <thead className="text-xs text-muted">
              <tr className="border-b border-line">
                <th scope="col" className="py-2 pr-3 font-semibold">Building</th>
                <th scope="col" className="py-2 pr-3 font-semibold">Score</th>
                <th scope="col" className="py-2 pr-3 font-semibold">Fails</th>
                <th scope="col" className="py-2 pr-3 font-semibold">Need review</th>
                <th scope="col" className="py-2 pr-3 font-semibold">HOA tasks</th>
                <th scope="col" className="py-2 pr-3 font-semibold">Owner tasks</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ building, scan, hoa, owner, unclear }) => (
                <tr key={building.id} className="border-b border-line last:border-0">
                  <th scope="row" className="py-2 pr-3 font-semibold text-ink">
                    {scan ? (
                      <Link href={`/report/${scan.id}`} className="underline decoration-line underline-offset-2 hover:decoration-brand">
                        {building.label}
                      </Link>
                    ) : (
                      building.label
                    )}
                  </th>
                  <td className="py-2 pr-3">
                    {scan?.report ? (
                      <span className="flex items-center gap-2">
                        <ScoreBadge score={scan.report.score.score} />
                        {scan.isSample && <SampleBadge />}
                      </span>
                    ) : (
                      <Link href={`/scan?building=${building.id}`} className="text-muted underline">
                        Not scanned
                      </Link>
                    )}
                  </td>
                  <td className="py-2 pr-3 font-semibold text-fail tabular-nums">{scan?.report ? scan.report.score.fails : "—"}</td>
                  <td className="py-2 pr-3 font-semibold text-review tabular-nums">{scan?.report ? scan.report.score.reviews : "—"}</td>
                  <td className="py-2 pr-3 tabular-nums">{hoa}</td>
                  <td className="py-2 pr-3 tabular-nums">
                    {owner}
                    {unclear > 0 && <span className="text-muted"> (+{unclear} unclear)</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card>
        <SectionTitle kicker="Fix plan across the community">All tasks</SectionTitle>
        <TaskList tasks={taskRows} />
      </Card>
    </>
  );
}
