import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { BuildingNotePanel } from "@/components/building-note";
import { AddBuilding, CommunityForm, DeleteCommunity, EditableBuilding } from "@/components/manage/forms";
import { Card, PageHeader, SampleBadge, ScoreBadge, SectionTitle, Skeleton } from "@/components/ui";
import { requestDb } from "@/lib/db";
import { getCommunity, latestDone, listBuildings, listScans } from "@/lib/db/queries";
import { isUuid } from "@/lib/ids";
import { PACK_OPTIONS } from "@/lib/rules";
import { pipelineSummary } from "@/lib/summary";

export const metadata: Metadata = { title: "Edit community" };

export default function EditCommunityPage(props: PageProps<"/manage/[communityId]">) {
  return (
    <main>
      <Suspense fallback={<Skeleton lines={3} />}>
        <Edit params={props.params} />
      </Suspense>
    </main>
  );
}

async function Edit({ params }: { params: PageProps<"/manage/[communityId]">["params"] }) {
  const { communityId } = await params;
  if (!isUuid(communityId)) notFound();
  const db = await requestDb();
  const c = await getCommunity(db, communityId);
  if (!c) notFound();
  const buildings = await listBuildings(db, c.id);
  const scans = await listScans(
    db,
    buildings.map((b) => b.id),
  );

  return (
    <>
      <PageHeader
        title={c.name}
        kicker={
          <span className="flex items-center gap-2">
            <Link href="/manage" className="underline underline-offset-2">
              Communities
            </Link>
            {c.isSample && <SampleBadge />}
          </span>
        }
      >
        <DeleteCommunity id={c.id} name={c.name} />
      </PageHeader>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <Card>
          <SectionTitle kicker="Community">Details and rules</SectionTitle>
          <CommunityForm
            packs={PACK_OPTIONS.map((p) => ({ ...p }))}
            values={{ id: c.id, name: c.name, type: c.type, place: c.place, rulePack: c.rulePack, includeProposed: c.includeProposed }}
          />
        </Card>

        <div className="flex flex-col gap-5">
          <Card>
            <SectionTitle kicker={`${buildings.length} building${buildings.length === 1 ? "" : "s"}`}>Buildings</SectionTitle>
            {buildings.length === 0 && <p className="text-sm text-muted">No buildings yet. Add the first one below.</p>}
            <ul className="flex flex-col divide-y divide-line">
              {buildings.map((b) => {
                const scan = latestDone(scans, b.id);
                const summary = scan?.report ? pipelineSummary(scan.report) : null;
                return (
                  <li key={b.id} className="py-3 first:pt-0 last:pb-0">
                    <EditableBuilding
                      values={{ id: b.id, communityId: c.id, label: b.label, units: b.units, eaveMode: b.eaveMode, eaveFt: b.eaveFt, address: b.address }}
                      summary={
                        <div className="flex items-start gap-3">
                          {scan?.report && <ScoreBadge score={scan.report.score.score} />}
                          <div>
                            <p className="font-semibold text-ink">{b.label}</p>
                            {b.address && <p className="text-xs text-muted">{b.address}</p>}
                            <p className="text-xs text-muted">
                              {b.units ? `Units ${b.units} · ` : ""}
                              {b.eaveMode === "none"
                                ? "No eave overhang"
                                : b.eaveMode === "known" && b.eaveFt
                                  ? `Eaves ${b.eaveFt} ft`
                                  : "Eaves measured from video"}
                            </p>
                            {summary ? (
                              <p className="text-xs text-muted">
                                {summary.tracked}
                                {scan?.isSample ? " (sample)" : ""}
                              </p>
                            ) : (
                              <Link href={`/scan?building=${b.id}`} className="text-xs font-semibold text-brand underline">
                                Not scanned yet · Scan now
                              </Link>
                            )}
                          </div>
                        </div>
                      }
                    />
                    {b.address && (
                      <div className="mt-2">
                        <BuildingNotePanel buildingId={b.id} address={b.address} note={b.note ?? null} />
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </Card>
          <Card>
            <SectionTitle kicker="New">Add a building</SectionTitle>
            <AddBuilding communityId={c.id} />
          </Card>
        </div>
      </div>
    </>
  );
}
