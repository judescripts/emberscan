import { createReadStream } from "node:fs";
import { mkdir, readdir, rm, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { Readable } from "node:stream";
import { isUuid } from "./ids";

// Big walkarounds arrive in pieces: Cloudflare (in front of the preview tunnel) refuses any
// request over 100 MB. The browser sends each clip in CHUNK_BYTES slices to /api/uploads,
// appended to a file per clip here, then POST /api/scans?upload=<id> streams the clips on to
// the worker and deletes them. Local disk only: fine for the dev server and a single host.

export const CHUNK_BYTES = 50 * 1024 * 1024;
export const MAX_CLIPS = 20;

const ROOT = path.join(os.tmpdir(), "emberscan-uploads");

export function uploadDir(uploadId: string): string | null {
  return isUuid(uploadId) ? path.join(ROOT, uploadId) : null;
}

export function clipPath(uploadId: string, clip: number): string | null {
  const dir = uploadDir(uploadId);
  if (!dir || !Number.isInteger(clip) || clip < 0 || clip >= MAX_CLIPS) return null;
  return path.join(dir, String(clip));
}

export async function ensureDir(uploadId: string): Promise<void> {
  const dir = uploadDir(uploadId);
  if (dir) await mkdir(dir, { recursive: true });
}

export async function sizeOf(file: string): Promise<number> {
  try {
    return (await stat(file)).size;
  } catch {
    return 0;
  }
}

/** The uploaded clip files in order, or null if the upload doesn't exist or has gaps. */
export async function clipFiles(uploadId: string): Promise<string[] | null> {
  const dir = uploadDir(uploadId);
  if (!dir) return null;
  let names: string[];
  try {
    names = await readdir(dir);
  } catch {
    return null;
  }
  const n = names.length;
  if (n === 0 || n > MAX_CLIPS) return null;
  const files = Array.from({ length: n }, (_, i) => path.join(dir, String(i)));
  return names.every((x) => Number(x) < n) ? files : null;
}

export async function removeUpload(uploadId: string): Promise<void> {
  const dir = uploadDir(uploadId);
  if (dir) await rm(dir, { recursive: true, force: true });
}

function safeName(name: string): string {
  return name.replace(/["\r\n\\]/g, "_").slice(0, 120) || "walkaround.mp4";
}

/** A multipart body (fields, then one `video` part per clip, read from disk as it goes). */
export function multipartFromClips(
  boundary: string,
  fields: [string, string][],
  clips: { file: string; name: string }[],
): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  async function* parts(): AsyncGenerator<Uint8Array> {
    for (const [k, v] of fields) {
      yield enc.encode(`--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`);
    }
    for (const c of clips) {
      yield enc.encode(
        `--${boundary}\r\nContent-Disposition: form-data; name="video"; filename="${safeName(c.name)}"\r\n` +
          "Content-Type: application/octet-stream\r\n\r\n",
      );
      for await (const chunk of createReadStream(c.file)) yield chunk as Uint8Array;
      yield enc.encode("\r\n");
    }
    yield enc.encode(`--${boundary}--\r\n`);
  }
  return Readable.toWeb(Readable.from(parts())) as ReadableStream<Uint8Array>;
}
