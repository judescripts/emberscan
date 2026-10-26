"use server";

import { eq } from "drizzle-orm";
import { refresh } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { COMMUNITY_COOKIE } from "@/lib/current";
import { getDb } from "@/lib/db";
import { getBuilding, getCommunity, syncTasks } from "@/lib/db/queries";
import { buildings, communities, fixTasks, scans, type CommunityType, type FixNote, type FixStatus } from "@/lib/db/schema";
import { SAMPLE_REPORT, SAMPLE_STAGES } from "@/lib/db/seed";
import { PACK_OPTIONS } from "@/lib/rules";
import { isUserSettable } from "@/lib/tasks";
import { workerResearch } from "@/lib/worker";

// Hackathon scope: no accounts yet, so actions validate input but not identity.

export type FormState = { ok: boolean; error?: string; message?: string };

function text(fd: FormData, key: string, max = 120): string {
  return String(fd.get(key) ?? "").trim().slice(0, max);
}

async function setCommunityCookie(id: string) {
  (await cookies()).set(COMMUNITY_COOKIE, id, { path: "/", sameSite: "lax", maxAge: 60 * 60 * 24 * 365 });
}

export async function selectCommunity(id: string) {
  const db = await getDb();
  if (!(await getCommunity(db, id))) return;
  await setCommunityCookie(id);
  refresh();
}

const TYPES: CommunityType[] = ["HOA", "Condo", "Home", "Commercial"];

export async function saveCommunity(_prev: FormState, fd: FormData): Promise<FormState> {
  const id = text(fd, "id", 64);
  const name = text(fd, "name");
  const type = text(fd, "type", 10) as CommunityType;
  const place = text(fd, "place");
  const rulePack = text(fd, "rule_pack", 32) || "us-ca";
  const includeProposed = fd.get("include_proposed") === "on";
  if (!name) return { ok: false, error: "Give the community a name." };
  if (!TYPES.includes(type)) return { ok: false, error: "Pick a community type." };
  if (!PACK_OPTIONS.some((p) => p.id === rulePack && p.available)) {
    return { ok: false, error: "That rule pack is coming soon. California is available now." };
  }
  const db = await getDb();
  if (id) {
    await db.update(communities).set({ name, type, place, rulePack, includeProposed }).where(eq(communities.id, id));
    refresh();
    return { ok: true, message: "Saved." };
  }
  const [row] = await db.insert(communities).values({ name, type, place, rulePack, includeProposed }).returning();
  await setCommunityCookie(row.id);
  redirect(`/manage/${row.id}`);
}

export async function deleteCommunity(id: string) {
  const db = await getDb();
  await db.delete(communities).where(eq(communities.id, id));
  (await cookies()).delete(COMMUNITY_COOKIE);
  redirect("/manage");
}

export async function setIncludeProposed(communityId: string, include: boolean) {
  const db = await getDb();
  await db.update(communities).set({ includeProposed: include }).where(eq(communities.id, communityId));
  refresh();
}

export async function saveBuilding(_prev: FormState, fd: FormData): Promise<FormState> {
  const id = text(fd, "id", 64);
  const communityId = text(fd, "community_id", 64);
  const label = text(fd, "label");
  const units = text(fd, "units");
  const eaveMode = text(fd, "eave_mode", 10) === "known" ? "known" : "video";
  const eaveRaw = text(fd, "eave_ft", 10);
  const eaveFt = eaveMode === "known" ? Number(eaveRaw) : null;
  if (!label) return { ok: false, error: "Give the building a label, like “Building C · Units 9–12”." };
  if (eaveMode === "known" && (!Number.isFinite(eaveFt) || (eaveFt as number) <= 0 || (eaveFt as number) > 10)) {
    return { ok: false, error: "Enter the eave depth in feet (for example 1.5), or choose “Measure from video”." };
  }
  const address = text(fd, "address", 200);
  const db = await getDb();
  if (id) {
    const before = await getBuilding(db, id);
    // A new address makes the old research note wrong; clear it so the card researches again.
    const note = before && before.address === address ? before.note : null;
    await db.update(buildings).set({ label, units, address, note, eaveMode, eaveFt }).where(eq(buildings.id, id));
  } else {
    if (!(await getCommunity(db, communityId))) return { ok: false, error: "Community not found." };
    await db.insert(buildings).values({ communityId, label, units, address, eaveMode, eaveFt });
  }
  refresh();
  return { ok: true, message: id ? "Building saved." : "Building added." };
}

/** Run the address research agent for a building and store its note. */
export async function researchBuilding(id: string): Promise<FormState> {
  const db = await getDb();
  const b = await getBuilding(db, id);
  if (!b) return { ok: false, error: "Building not found." };
  if (b.address.length < 5) return { ok: false, error: "Add the building's street address first." };
  try {
    const note = await workerResearch(b.address);
    await db.update(buildings).set({ note }).where(eq(buildings.id, id));
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Research failed." };
  }
  refresh();
  return { ok: true, message: "Research note updated." };
}

export async function deleteBuilding(id: string) {
  const db = await getDb();
  await db.delete(buildings).where(eq(buildings.id, id));
  refresh();
}

/** Worker offline: attach the sample report to this building as a scan clearly marked Sample. */
export async function loadSampleReport(buildingId: string) {
  const db = await getDb();
  const building = await getBuilding(db, buildingId);
  if (!building) throw new Error("Building not found");
  const [scan] = await db
    .insert(scans)
    .values({
      buildingId,
      status: "done",
      stage: "report",
      progress: 1,
      stages: SAMPLE_STAGES,
      report: { ...SAMPLE_REPORT, created_at: new Date().toISOString() },
      isSample: true,
    })
    .returning();
  await syncTasks(db, buildingId, scan.id, SAMPLE_REPORT);
  redirect(`/report/${scan.id}`);
}

export type TaskUpdate = { status?: string; owner?: string; note?: string };

export async function updateTask(taskId: string, update: TaskUpdate): Promise<FormState> {
  const db = await getDb();
  const [task] = await db.select().from(fixTasks).where(eq(fixTasks.id, taskId));
  if (!task) return { ok: false, error: "Task not found." };
  const note = (update.note ?? "").trim().slice(0, 500);
  const patch: Partial<typeof fixTasks.$inferInsert> = { updatedAt: new Date() };
  const notes: FixNote[] = [...task.notes];
  const when = new Date().toISOString();
  const by = (update.owner ?? task.owner).trim() || "Resident";

  if (update.status !== undefined && update.status !== task.status) {
    if (!isUserSettable(update.status)) {
      return { ok: false, error: "Only a rescan can mark a fix as verified." };
    }
    if (update.status === "wontfix" && !note) {
      return { ok: false, error: "Say why this won't be fixed. The reason stays with the report." };
    }
    if (task.status === "verified" && update.status !== "open") {
      return { ok: false, error: "This was verified by a rescan. Reopen it first if something changed." };
    }
    patch.status = update.status as FixStatus;
    const label = { open: "Reopened", progress: "Started", fixed: "Marked fixed (needs rescan)", wontfix: "Won't fix" }[
      update.status as "open" | "progress" | "fixed" | "wontfix"
    ];
    notes.push({ text: note ? `${label}: ${note}` : label, at: when, by });
  } else if (note) {
    notes.push({ text: note, at: when, by });
  }
  if (update.owner !== undefined) patch.owner = update.owner.trim().slice(0, 80);
  patch.notes = notes;
  await db.update(fixTasks).set(patch).where(eq(fixTasks.id, taskId));
  refresh();
  return { ok: true };
}

/** Remove a scan that failed or was a test; tasks from other scans are untouched. */
export async function deleteScan(scanId: string) {
  const db = await getDb();
  const [row] = await db.select().from(scans).where(eq(scans.id, scanId));
  if (!row) return;
  if (row.status !== "failed") throw new Error("Only failed scans can be removed.");
  await db.delete(scans).where(eq(scans.id, scanId));
  redirect("/");
}
