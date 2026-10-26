import type { BuildingNote, WorkerScan } from "./report-types";

// Worker HTTP API (docs/contracts/README.md). Server-side only: the token never reaches the browser.

export function workerUrl(): string {
  return (process.env.WORKER_URL ?? "http://localhost:8000").replace(/\/+$/, "");
}

export function workerHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = process.env.WORKER_TOKEN;
  return token ? { Authorization: `Bearer ${token}`, ...extra } : extra;
}

export class WorkerUnreachable extends Error {
  constructor(cause: unknown) {
    super(`EmberScan worker not reachable at ${workerUrl()}`);
    this.cause = cause;
  }
}

export async function workerFetch(path: string, init: RequestInit & { duplex?: "half" } = {}, timeoutMs = 10000) {
  try {
    return await fetch(`${workerUrl()}${path}`, {
      ...init,
      headers: { ...workerHeaders(), ...(init.headers as Record<string, string> | undefined) },
      signal: init.signal ?? AbortSignal.timeout(timeoutMs),
      cache: "no-store",
    });
  } catch (err) {
    throw new WorkerUnreachable(err);
  }
}

export async function workerHealth(): Promise<boolean> {
  try {
    const res = await workerFetch("/health", {}, 2500);
    return res.ok;
  } catch {
    return false;
  }
}

export type WorkerBudget = { scans_left_today: number; spent_24h_usd: number; daily_limit_usd: number };

export async function workerBudget(): Promise<WorkerBudget | null> {
  try {
    const res = await workerFetch("/budget", {}, 2500);
    return res.ok ? ((await res.json()) as WorkerBudget) : null;
  } catch {
    return null;
  }
}

// Optional shared passcode for starting scans (SCAN_PASSCODE). Browsing stays open; only the
// paid step is gated, so a public demo link can't be used to drain the Meta account.
export function passcodeRequired(): boolean {
  return Boolean(process.env.SCAN_PASSCODE);
}

export function passcodeOk(given: string | null): boolean {
  const want = process.env.SCAN_PASSCODE;
  if (!want) return true;
  if (!given || given.length !== want.length) return false;
  let diff = 0;
  for (let i = 0; i < want.length; i++) diff |= want.charCodeAt(i) ^ given.charCodeAt(i);
  return diff === 0;
}

/** Address research (Muse Spark + public map data). Throws with a user-facing message. */
export async function workerResearch(address: string): Promise<BuildingNote> {
  let res: Response;
  try {
    res = await workerFetch(
      "/research",
      { method: "POST", body: JSON.stringify({ address }), headers: { "content-type": "application/json" } },
      90_000,
    );
  } catch {
    throw new Error("The research service isn't reachable right now.");
  }
  if (res.status === 429) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? "The AI budget is used up for today.");
  }
  if (!res.ok) throw new Error(`Research failed (${res.status}).`);
  return (await res.json()) as BuildingNote;
}

export async function getWorkerScan(workerScanId: string): Promise<WorkerScan> {
  const res = await workerFetch(`/scans/${encodeURIComponent(workerScanId)}`);
  if (!res.ok) throw new Error(`Worker returned ${res.status} for scan ${workerScanId}`);
  return (await res.json()) as WorkerScan;
}
