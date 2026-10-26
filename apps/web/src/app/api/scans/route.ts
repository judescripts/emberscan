import { getDb } from "@/lib/db";
import { getBuilding, getCommunity } from "@/lib/db/queries";
import { scans } from "@/lib/db/schema";
import { isUuid } from "@/lib/ids";
import { WorkerUnreachable, workerFetch, workerUrl } from "@/lib/worker";

// POST /api/scans?building=<id>  body: multipart/form-data with a single `video` file part.
// Streams the upload straight through to the worker's POST /scans (no buffering in memory),
// prepending the building fields the worker needs. Returns { scanId } for the progress view.

export const maxDuration = 300;

function boundaryOf(contentType: string | null): string | null {
  const m = /boundary=(?:"([^"]+)"|([^;]+))/i.exec(contentType ?? "");
  return m ? (m[1] ?? m[2]).trim() : null;
}

function fieldPart(boundary: string, name: string, value: string): string {
  return `--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`;
}

export async function POST(request: Request) {
  const buildingId = new URL(request.url).searchParams.get("building");
  if (!isUuid(buildingId)) return Response.json({ error: "bad_request", message: "Pick a building first." }, { status: 400 });
  const ct = request.headers.get("content-type");
  const boundary = boundaryOf(ct);
  if (!boundary || !ct?.toLowerCase().startsWith("multipart/form-data") || !request.body) {
    return Response.json({ error: "bad_request", message: "Send the video as multipart/form-data." }, { status: 400 });
  }

  const db = await getDb();
  const building = await getBuilding(db, buildingId);
  if (!building) return Response.json({ error: "not_found", message: "Building not found." }, { status: 404 });
  const community = await getCommunity(db, building.communityId);

  const fields: [string, string][] = [
    ["building_label", building.label],
    ["include_proposed", String(community?.includeProposed ?? true)],
  ];
  if (building.eaveMode === "known" && building.eaveFt) fields.push(["eave_depth_ft", String(building.eaveFt)]);
  const prefix = new TextEncoder().encode(fields.map(([k, v]) => fieldPart(boundary, k, v)).join(""));

  const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>();
  const pump = (async () => {
    const writer = writable.getWriter();
    await writer.write(prefix);
    writer.releaseLock();
    await request.body!.pipeTo(writable);
  })();
  pump.catch(() => {
    /* client aborted; the worker fetch below fails and reports it */
  });

  let res: Response;
  try {
    res = await workerFetch(
      "/scans",
      { method: "POST", body: readable, duplex: "half", headers: { "content-type": ct } },
      5 * 60 * 1000,
    );
  } catch (err) {
    if (err instanceof WorkerUnreachable) {
      return Response.json(
        { error: "worker_unreachable", message: `The scan pipeline isn't reachable right now (${workerUrl()}).` },
        { status: 503 },
      );
    }
    throw err;
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    return Response.json({ error: "worker_error", message: `The pipeline rejected the upload (${res.status}). ${text.slice(0, 300)}` }, { status: 502 });
  }
  const { scan_id } = (await res.json()) as { scan_id: string };
  const [row] = await db
    .insert(scans)
    .values({
      buildingId,
      workerScanId: scan_id,
      status: "queued",
      stage: "upload",
      progress: 0,
      stages: [{ name: "upload", status: "done", detail: "Video received by the pipeline" }],
    })
    .returning();
  return Response.json({ scanId: row.id }, { status: 201 });
}
