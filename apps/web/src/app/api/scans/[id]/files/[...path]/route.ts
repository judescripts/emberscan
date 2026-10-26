import { getDb } from "@/lib/db";
import { getScan } from "@/lib/db/queries";
import { isUuid } from "@/lib/ids";
import { workerFetch } from "@/lib/worker";

// GET /api/scans/:id/files/<image_path> — proxies evidence images from the worker
// (GET {WORKER_URL}/scans/{worker_scan_id}/files/{path}) so the browser never needs the worker URL or token.

export async function GET(_req: Request, ctx: RouteContext<"/api/scans/[id]/files/[...path]">) {
  const { id, path } = await ctx.params;
  if (!isUuid(id) || path.some((p) => p === ".." || p === "." || p.includes("\\"))) {
    return new Response("Not found", { status: 404 });
  }
  const db = await getDb();
  const scan = await getScan(db, id);
  if (!scan?.workerScanId) return new Response("Not found", { status: 404 });
  try {
    const res = await workerFetch(`/scans/${encodeURIComponent(scan.workerScanId)}/files/${path.map(encodeURIComponent).join("/")}`);
    if (!res.ok || !res.body) return new Response("Not found", { status: res.status === 404 ? 404 : 502 });
    const type = res.headers.get("content-type") ?? "application/octet-stream";
    if (!/^image\//.test(type)) return new Response("Unsupported file type", { status: 415 });
    return new Response(res.body, {
      headers: { "content-type": type, "cache-control": "private, max-age=3600", "x-content-type-options": "nosniff" },
    });
  } catch {
    return new Response("Worker unreachable", { status: 502 });
  }
}
