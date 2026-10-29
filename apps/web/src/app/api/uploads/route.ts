import { isUuid } from "@/lib/ids";
import { WorkerUnreachable, passcodeOk, workerFetch } from "@/lib/worker";

// PUT /api/uploads?upload=<uuid>&clip=<n>&offset=<bytes>  body: raw bytes of one slice.
// Big walkarounds go up in small slices (Vercel functions take 4.5 MB bodies; Cloudflare 100 MB),
// passed straight on to the worker's PUT /uploads/{id}/{clip}, which appends them. The offset
// must equal what the worker already has, so a retried slice is never written twice (409 says
// what it has). POST /api/scans?upload=<uuid> then starts the scan.

export const maxDuration = 60;
const MAX_SLICE_BYTES = 4 * 1024 * 1024;

export async function PUT(request: Request) {
  const q = new URL(request.url).searchParams;
  if (!passcodeOk(request.headers.get("x-scan-passcode"))) {
    return Response.json({ error: "passcode", message: "That scan passcode isn't right." }, { status: 401 });
  }
  const uploadId = q.get("upload");
  const clip = Number(q.get("clip"));
  const offset = Number(q.get("offset"));
  if (!isUuid(uploadId) || !Number.isInteger(clip) || clip < 0 || !Number.isInteger(offset) || offset < 0) {
    return Response.json({ error: "bad_request", message: "Bad upload slice." }, { status: 400 });
  }
  const body = await request.arrayBuffer();
  if (body.byteLength === 0 || body.byteLength > MAX_SLICE_BYTES) {
    return Response.json({ error: "bad_request", message: "Upload slices must be 4 MB or less." }, { status: 413 });
  }
  let res: Response;
  try {
    res = await workerFetch(
      `/uploads/${uploadId}/${clip}?offset=${offset}`,
      { method: "PUT", body, headers: { "content-type": "application/octet-stream" } },
      45_000,
    );
  } catch (err) {
    if (err instanceof WorkerUnreachable) {
      return Response.json({ error: "worker_unreachable", message: "The scan pipeline isn't reachable right now." }, { status: 503 });
    }
    throw err;
  }
  return new Response(await res.text(), { status: res.status, headers: { "content-type": "application/json" } });
}
