import { eq } from "drizzle-orm";
import { getDb } from "@/lib/db";
import { attachReport, getBuilding, getScan } from "@/lib/db/queries";
import { scans } from "@/lib/db/schema";
import { isUuid } from "@/lib/ids";
import { getWorkerScan, WorkerUnreachable } from "@/lib/worker";

// GET /api/scans/:id — polled by the progress view. Asks the worker for fresh status, stores it,
// and attaches the report (plus rescan verification of fix tasks) once the worker is done.

export async function GET(_req: Request, ctx: RouteContext<"/api/scans/[id]">) {
  const { id } = await ctx.params;
  if (!isUuid(id)) return Response.json({ error: "not_found" }, { status: 404 });
  const db = await getDb();
  let scan = await getScan(db, id);
  if (!scan) return Response.json({ error: "not_found" }, { status: 404 });

  let workerReachable = true;
  let workerError: string | null = null;
  if (scan.workerScanId && scan.status !== "done" && scan.status !== "failed") {
    try {
      const w = await getWorkerScan(scan.workerScanId);
      const stages = w.stages && w.stages.length ? w.stages : scan.stages;
      await db
        .update(scans)
        .set({
          status: w.status === "done" && !w.report ? "processing" : w.status,
          stage: w.stage ?? scan.stage,
          progress: typeof w.progress === "number" ? w.progress : scan.progress,
          stages,
          error: w.error ?? null,
        })
        .where(eq(scans.id, id));
      if (w.status === "done" && w.report) {
        const building = await getBuilding(db, scan.buildingId);
        if (building) await attachReport(db, id, building, w.report);
      }
      scan = (await getScan(db, id))!;
    } catch (err) {
      workerReachable = false;
      workerError = err instanceof WorkerUnreachable ? err.message : String((err as Error).message ?? err);
    }
  }

  return Response.json(
    {
      id: scan.id,
      status: scan.status,
      stage: scan.stage,
      progress: scan.progress,
      stages: scan.stages ?? [],
      error: scan.error,
      hasReport: Boolean(scan.report),
      isSample: scan.isSample,
      workerReachable,
      workerError,
    },
    { headers: { "cache-control": "no-store" } },
  );
}
