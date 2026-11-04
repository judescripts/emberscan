import { createHash, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

// Locked communities (LOCKED_COMMUNITY_IDS, comma-separated) are read-only on a public deployment,
// so visitors can't rename, edit or delete the example report. An admin who signs in at /admin
// with ADMIN_TOKEN can still change them. Visitors can make their own community to try a scan.

export const ADMIN_COOKIE = "es_admin";
export const LOCKED_MESSAGE = "This example is locked. Create your own community to try EmberScan.";

function lockedIds(): string[] {
  return (process.env.LOCKED_COMMUNITY_IDS ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function isLockedCommunity(id: string): boolean {
  return lockedIds().includes(id);
}

const digest = (s: string) => createHash("sha256").update(s).digest();

export function adminTokenOk(given: string | undefined | null): boolean {
  const token = process.env.ADMIN_TOKEN;
  if (!token || !given) return false;
  return timingSafeEqual(digest(given), digest(token));
}

export async function isAdmin(): Promise<boolean> {
  return adminTokenOk((await cookies()).get(ADMIN_COOKIE)?.value);
}

/** True when this visitor may change the community: it isn't locked, or they're the admin. */
export async function canEdit(communityId: string): Promise<boolean> {
  return !isLockedCommunity(communityId) || (await isAdmin());
}
