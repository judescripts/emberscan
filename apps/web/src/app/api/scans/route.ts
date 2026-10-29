import { getDb } from "@/lib/db";
import { getBuilding, getCommunity } from "@/lib/db/queries";
import { scans } from "@/lib/db/schema";
import { isUuid } from "@/lib/ids";
import { WorkerUnreachable, passcodeOk, workerFetch, workerUrl } from "@/lib/worker";

// POST /api/scans?building=<id>&upload=<uuid>  body: JSON { names: string[], sides?: string }.
// The clips were already sent in slices to /api/uploads, which the worker kept; this asks the
// worker to start the scan from them, with the building fields it needs. Returns { scanId }.
//
// POST /api/scans?building=<id>  body: multipart/form-data with one `video` part per clip.
// Streams the upload straight through to the worker's POST /scans (no buffering in memory).
// Only for small uploads where nothing sits in front of the app with a body limit.

export const maxDuration = 300;

function boundaryOf(contentType: string | null): string | null {
  const m = /boundary=(?:"([^"]+)"|([^;]+))/i.exec(contentType ?? "");
  return m ? (m[1] ?? m[2]).trim() : null;
}

function fieldPart(boundary: string, name: string, value: string): string {
  return `--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`;
}

export async function POST(request: Request) {
  const q = new URL(request.url).searchParams;
  const buildingId = q.get("building");
  if (!isUuid(buildingId)) return Response.json({ error: "bad_request", message: "Pick a building first." }, { status: 400 });
  if (!passcodeOk(request.headers.get("x-scan-passcode"))) {
    return Response.json({ error: "passcode", message: "That scan passcode isn't right." }, { status: 401 });
  }
  const uploadId = q.get("upload");
  if (uploadId !== null && !isUuid(uploadId)) {
    return Response.json({ error: "bad_request", message: "Bad upload." }, { status: 400 });
  }
  const ct = request.headers.get("content-type");
  const boundary = boundaryOf(ct);
  if (!uploadId && (!boundary || !ct?.toLowerCase().startsWith("multipart/form-data") || !request.body)) {
    return Response.json({ error: "bad_request", message: "Send the video as multipart/form-data." }, { status: 400 });
  }

  const db = await getDb();
  const building = await getBuilding(db, buildingId);
  if (!building) return Response.json({ error: "not_found", message: "Building not found." }, { status: 404 });
  const community = await getCommunity(db, building.communityId);

  const fields: Record<string, string> = {
    building_label: building.label,
    include_proposed: String(community?.includeProposed ?? true),
    community_type: community?.type ?? "HOA",
  };
  if (building.eaveMode === "known" && building.eaveFt) fields.eave_depth_ft = String(building.eaveFt);
  if (building.eaveMode === "none") fields.eave_depth_ft = "0";

  let res: Response;
  try {
    if (uploadId) {
      const body = (await request.json().catch(() => ({}))) as { names?: unknown; sides?: unknown };
      const names = Array.isArray(body.names) ? body.names.map(String) : [];
      if (names.length === 0) {
        return Response.json({ error: "bad_request", message: "The upload is incomplete. Try again." }, { status: 400 });
      }
      res = await workerFetch(
        `/uploads/${uploadId}/scan`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            ...fields,
            include_proposed: fields.include_proposed === "true",
            eave_depth_ft: fields.eave_depth_ft === undefined ? null : Number(fields.eave_depth_ft),
            names,
            clip_sides: typeof body.sides === "string" && body.sides ? body.sides : null,
          }),
        },
        60_000,
      );
    } else {
      const b = boundary!;
      const prefix = new TextEncoder().encode(
        Object.entries(fields)
          .map(([k, v]) => fieldPart(b, k, v))
          .join(""),
      );
      const t = new TransformStream<Uint8Array, Uint8Array>();
      const pump = (async () => {
        const writer = t.writable.getWriter();
        await writer.write(prefix);
        writer.releaseLock();
        await request.body!.pipeTo(t.writable);
      })();
      pump.catch(() => {
        /* client aborted; the worker fetch below fails and reports it */
      });
      res = await workerFetch(
        "/scans",
        { method: "POST", body: t.readable, duplex: "half", headers: { "content-type": ct! } },
        5 * 60 * 1000,
      );
    }
  } catch (err) {
    if (err instanceof WorkerUnreachable) {
      return Response.json(
        { error: "worker_unreachable", message: `The scan pipeline isn't reachable right now (${workerUrl()}).` },
        { status: 503 },
      );
    }
    throw err;
  }
  if (res.status === 429) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    return Response.json(
      { error: "budget", message: `${body.detail ?? "The scan budget is used up."} The sample report is still available.` },
      { status: 429 },
    );
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
