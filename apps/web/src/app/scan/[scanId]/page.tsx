import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ScanProgress } from "@/components/scan/scan-progress";
import { PageHeader, SampleBadge, ShortDisclaimer, Skeleton } from "@/components/ui";
import { requestDb } from "@/lib/db";
import { getBuilding, getScan } from "@/lib/db/queries";
import { isUuid } from "@/lib/ids";

export const metadata: Metadata = { title: "Scanning" };

export default function ScanProgressPage(props: PageProps<"/scan/[scanId]">) {
  return (
    <main>
      <Suspense fallback={<Skeleton lines={4} />}>
        <Progress params={props.params} />
      </Suspense>
      <div className="mt-6">
        <ShortDisclaimer />
      </div>
    </main>
  );
}

async function Progress({ params }: { params: PageProps<"/scan/[scanId]">["params"] }) {
  const { scanId } = await params;
  if (!isUuid(scanId)) notFound();
  const db = await requestDb();
  const scan = await getScan(db, scanId);
  if (!scan) notFound();
  const building = await getBuilding(db, scan.buildingId);
  return (
    <>
      <PageHeader
        title={building?.label ?? "Scan"}
        kicker={
          <span className="flex items-center gap-2">
            {scan.isSample && <SampleBadge />}
            Walkaround video → measured, cited fix plan
          </span>
        }
      />
      <ScanProgress
        buildingId={scan.buildingId}
        initial={{
          id: scan.id,
          status: scan.status,
          stage: scan.stage,
          progress: scan.progress,
          stages: scan.stages ?? [],
          error: scan.error,
          hasReport: Boolean(scan.report),
          isSample: scan.isSample,
        }}
      />
    </>
  );
}
