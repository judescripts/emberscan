import type { WorkerScan } from "./report-types";

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

export async function getWorkerScan(workerScanId: string): Promise<WorkerScan> {
  const res = await workerFetch(`/scans/${encodeURIComponent(workerScanId)}`);
  if (!res.ok) throw new Error(`Worker returned ${res.status} for scan ${workerScanId}`);
  return (await res.json()) as WorkerScan;
}
