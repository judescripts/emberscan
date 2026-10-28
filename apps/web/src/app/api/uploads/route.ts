import { createWriteStream } from "node:fs";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import type { ReadableStream as NodeWebStream } from "node:stream/web";
import { CHUNK_BYTES, clipPath, ensureDir, sizeOf } from "@/lib/uploads";
import { passcodeOk } from "@/lib/worker";

// PUT /api/uploads?upload=<uuid>&clip=<n>&offset=<bytes>  body: raw bytes of one slice.
// Appends the slice to clip n of that upload. The offset must equal what's already stored,
// so a retried slice can't be written twice. See lib/uploads.ts.

export const maxDuration = 300;

export async function PUT(request: Request) {
  const q = new URL(request.url).searchParams;
  if (!passcodeOk(request.headers.get("x-scan-passcode"))) {
    return Response.json({ error: "passcode", message: "That scan passcode isn't right." }, { status: 401 });
  }
  const uploadId = q.get("upload") ?? "";
  const file = clipPath(uploadId, Number(q.get("clip")));
  const offset = Number(q.get("offset"));
  const length = Number(request.headers.get("content-length"));
  if (!file || !Number.isInteger(offset) || offset < 0 || !request.body) {
    return Response.json({ error: "bad_request", message: "Bad upload slice." }, { status: 400 });
  }
  if (!(length > 0 && length <= CHUNK_BYTES)) {
    return Response.json({ error: "bad_request", message: "Upload slices must be 50 MB or less." }, { status: 413 });
  }
  await ensureDir(uploadId);
  const have = await sizeOf(file);
  if (have !== offset) return Response.json({ error: "offset", have }, { status: 409 });
  await pipeline(Readable.fromWeb(request.body as NodeWebStream), createWriteStream(file, { flags: "a" }));
  return Response.json({ size: await sizeOf(file) });
}
