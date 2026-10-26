import { and, asc, desc, eq, inArray } from "drizzle-orm";
import type { Report } from "../report-types";
import { rescanTransition, ruleStatusMap, taskRuleId } from "../tasks";
import type { DB } from "./index";
import { buildings, communities, fixTasks, scans, type Building, type FixNote, type Scan } from "./schema";

export async function listCommunities(db: DB) {
  return db.select().from(communities).orderBy(asc(communities.createdAt));
}

export async function getCommunity(db: DB, id: string) {
  const [row] = await db.select().from(communities).where(eq(communities.id, id));
  return row ?? null;
}

export async function listBuildings(db: DB, communityId: string) {
  return db.select().from(buildings).where(eq(buildings.communityId, communityId)).orderBy(asc(buildings.label));
}

export async function getBuilding(db: DB, id: string) {
  const [row] = await db.select().from(buildings).where(eq(buildings.id, id));
  return row ?? null;
}

export async function getScan(db: DB, id: string) {
  const [row] = await db.select().from(scans).where(eq(scans.id, id));
  return row ?? null;
}

/** Scans for these buildings, newest first. */
export async function listScans(db: DB, buildingIds: string[]) {
  if (buildingIds.length === 0) return [] as Scan[];
  return db.select().from(scans).where(inArray(scans.buildingId, buildingIds)).orderBy(desc(scans.createdAt));
}

export function latestDone(scansNewestFirst: Scan[], buildingId: string): Scan | undefined {
  return scansNewestFirst.find((s) => s.buildingId === buildingId && s.status === "done" && s.report);
}

export async function listTasks(db: DB, buildingIds: string[]) {
  if (buildingIds.length === 0) return [];
  return db.select().from(fixTasks).where(inArray(fixTasks.buildingId, buildingIds)).orderBy(asc(fixTasks.priority));
}

/** Insert a finished scan's report and update the building's fix tasks (rescan verification). */
export async function attachReport(db: DB, scanId: string, building: Building, report: Report) {
  await db
    .update(scans)
    .set({ report, status: "done", progress: 1, stage: "report" })
    .where(eq(scans.id, scanId));
  await syncTasks(db, building.id, scanId, report);
}

export async function syncTasks(db: DB, buildingId: string, scanId: string, report: Report) {
  const existing = await db.select().from(fixTasks).where(eq(fixTasks.buildingId, buildingId));
  const byRule = new Map(existing.map((t) => [t.ruleId, t]));
  const statuses = ruleStatusMap(report);
  const fixRuleIds = new Set(report.fixes.map(taskRuleId));
  const when = new Date().toISOString();

  for (const fix of report.fixes) {
    const ruleId = taskRuleId(fix);
    const task = byRule.get(ruleId);
    if (!task) {
      await db.insert(fixTasks).values({
        buildingId,
        ruleId,
        title: fix.title,
        responsibility: fix.owner,
        required: fix.required,
        owner: "", // a name is optional; who's responsible lives in `responsibility`
        priority: fix.priority,
        sourceScanId: scanId,
        notes: [],
      });
      continue;
    }
    const outcome = rescanTransition(task.status, statuses.get(ruleId), true);
    const notes: FixNote[] = outcome.note ? [...task.notes, { text: outcome.note, at: when, by: "Rescan" }] : task.notes;
    await db
      .update(fixTasks)
      .set({
        title: fix.title,
        required: fix.required,
        priority: fix.priority,
        sourceScanId: scanId,
        status: outcome.status,
        notes,
        updatedAt: new Date(),
      })
      .where(eq(fixTasks.id, task.id));
  }

  // Tasks from earlier scans that this scan no longer flags.
  for (const task of existing) {
    if (fixRuleIds.has(task.ruleId)) continue;
    const outcome = rescanTransition(task.status, statuses.get(task.ruleId), false);
    if (outcome.status === task.status && !outcome.note) continue;
    await db
      .update(fixTasks)
      .set({
        status: outcome.status,
        notes: outcome.note ? [...task.notes, { text: outcome.note, at: when, by: "Rescan" }] : task.notes,
        updatedAt: new Date(),
      })
      .where(and(eq(fixTasks.id, task.id), eq(fixTasks.buildingId, buildingId)));
  }
}
