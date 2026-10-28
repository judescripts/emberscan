import { getDb } from "@/lib/db";
import { getBuilding, getCommunity } from "@/lib/db/queries";
import { scans } from "@/lib/db/schema";
import { isUuid } from "@/lib/ids";
import { clipFiles, multipartFromClips, removeUpload } from "@/lib/uploads";
import { WorkerUnreachable, passcodeOk, workerFetch, workerUrl } from "@/lib/worker";

// POST /api/scans?building=<id>  body: multipart/form-data with one `video` part per clip.
// Streams the upload straight through to the worker's POST /scans (no buffering in memory),
// prepending the building fields the worker needs. Returns { scanId } for the progress view.
//
// POST /api/scans?building=<id>&upload=<uuid>  body: JSON { names: string[], sides?: string }.
// The clips were already sent in slices to /api/uploads (big videos); they're streamed from
// disk to the worker the same way, then deleted.

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
  if (!passcodeOk(request.headers.get("x-scan-passcode"))) {
    return Response.json({ error: "passcode", message: "That scan passcode isn't right." }, { status: 401 });
  }
  const uploadId = new URL(request.url).searchParams.get("upload");
  let ct = request.headers.get("content-type");
  let boundary = boundaryOf(ct);
  let clips: { file: string; name: string }[] | null = null;
  let sides = "";
  if (uploadId) {
    const files = await clipFiles(uploadId);
    const body = (await request.json().catch(() => ({}))) as { names?: unknown; sides?: unknown };
    const names = Array.isArray(body.names) ? body.names.map(String) : [];
    if (!files || names.length !== files.length) {
      return Response.json({ error: "bad_request", message: "The upload is incomplete. Try again." }, { status: 400 });
    }
    clips = files.map((file, i) => ({ file, name: names[i] }));
    sides = typeof body.sides === "string" ? body.sides : "";
    boundary = `----emberscan${crypto.randomUUID().replaceAll("-", "")}`;
    ct = `multipart/form-data; boundary=${boundary}`;
  } else if (!boundary || !ct?.toLowerCase().startsWith("multipart/form-data") || !request.body) {
    return Response.json({ error: "bad_request", message: "Send the video as multipart/form-data." }, { status: 400 });
  }

  const db = await getDb();
  const building = await getBuilding(db, buildingId);
  if (!building) return Response.json({ error: "not_found", message: "Building not found." }, { status: 404 });
  const community = await getCommunity(db, building.communityId);

  const fields: [string, string][] = [
    ["building_label", building.label],
    ["include_proposed", String(community?.includeProposed ?? true)],
    ["community_type", community?.type ?? "HOA"],
  ];
  if (building.eaveMode === "known" && building.eaveFt) fields.push(["eave_depth_ft", String(building.eaveFt)]);
  if (building.eaveMode === "none") fields.push(["eave_depth_ft", "0"]);
  const b = boundary;
  if (!b || !ct) return Response.json({ error: "bad_request" }, { status: 400 });

  let readable: ReadableStream<Uint8Array>;
  if (clips) {
    if (sides) fields.push(["clip_sides", sides]);
    readable = multipartFromClips(b, fields, clips);
  } else {
    const prefix = new TextEncoder().encode(fields.map(([k, v]) => fieldPart(b, k, v)).join(""));
    const t = new TransformStream<Uint8Array, Uint8Array>();
    readable = t.readable;
    const pump = (async () => {
      const writer = t.writable.getWriter();
      await writer.write(prefix);
      writer.releaseLock();
      await request.body!.pipeTo(t.writable);
    })();
    pump.catch(() => {
      /* client aborted; the worker fetch below fails and reports it */
    });
  }

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
  } finally {
    // The worker has its own copy once it answers (or the upload is useless if it failed).
    if (uploadId) await removeUpload(uploadId);
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
