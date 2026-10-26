import { eq } from "drizzle-orm";
import sampleReport from "../sample-report.json";
import type { Report, WorkerStage } from "../report-types";
import { PIPELINE_STAGES } from "../report-types";
import type { DB } from "./index";
import { syncTasks } from "./queries";
import { buildings, communities, scans } from "./schema";

export const SAMPLE_REPORT = sampleReport as unknown as Report;

export const SAMPLE_STAGES: WorkerStage[] = PIPELINE_STAGES.map((name) => ({
  name,
  status: "done",
  detail: "Sample data",
}));

/** Creates the sample community (clearly marked "Sample") unless any community exists. */
export async function seedSampleIfEmpty(db: DB): Promise<boolean> {
  const any = await db.select({ id: communities.id }).from(communities).limit(1);
  if (any.length > 0) return false;
  await seedSample(db);
  return true;
}

export async function seedSample(db: DB) {
  const existing = await db.select().from(communities).where(eq(communities.isSample, true));
  if (existing.length > 0) return existing[0];

  const [community] = await db
    .insert(communities)
    .values({
      name: "Willow Creek Townhomes",
      type: "HOA",
      place: "Sample community · Southern California",
      rulePack: "us-ca",
      includeProposed: true,
      isSample: true,
    })
    .returning();

  await db.insert(buildings).values({
    communityId: community.id,
    label: "Building A · Units 1–4",
    units: "1, 2, 3, 4",
    eaveMode: "video",
  });
  const [b] = await db
    .insert(buildings)
    .values({
      communityId: community.id,
      label: SAMPLE_REPORT.building_label,
      units: "5, 6, 7, 8",
      eaveMode: "known",
      eaveFt: 1.75,
    })
    .returning();

  const [scan] = await db
    .insert(scans)
    .values({
      buildingId: b.id,
      workerScanId: null,
      status: "done",
      stage: "report",
      progress: 1,
      stages: SAMPLE_STAGES,
      report: SAMPLE_REPORT,
      isSample: true,
      createdAt: new Date(SAMPLE_REPORT.created_at),
    })
    .returning();
  await syncTasks(db, b.id, scan.id, SAMPLE_REPORT);
  return community;
}
