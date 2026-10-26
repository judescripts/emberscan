#!/usr/bin/env node
// Reads SAM 3.1 Responses events (a JSON array) on stdin and writes tracks JSON to stdout:
// { complete, usage, tracks: { [objectId]: { boxes: { [frame]: [l, t, r, b, conf] },
//                                            masks: { [frame]: { rle: {size, counts}, bounds: [l, t, r, b] } } } } }
// Uses Meta's official parser; the Node build is ~70x faster than the pure-Python one for
// the arithmetic-coded masks, which matters for full walkarounds.
import { parseVideoStream, decodeMaskToRLE } from '@meta-sam/parser';

export async function parseEvents(events) {
  const usage = events.find((e) => e.type === 'response.completed')?.response?.usage ?? null;
  async function* source() {
    for (const e of events) yield e;
  }
  const parsed = parseVideoStream(source());
  const result = await parsed.finalResult;
  const tracks = {};
  for (const rec of result.records) {
    const frame = rec.frame?.frameIndex;
    if (frame === undefined || (rec.kind !== 'box' && rec.kind !== 'mask')) continue;
    const t = (tracks[rec.objectId] ??= { boxes: {}, masks: {} });
    if (rec.kind === 'box') {
      t.boxes[frame] = [rec.left, rec.top, rec.right, rec.bottom, rec.confidence ?? null];
    } else {
      const rle = decodeMaskToRLE(rec.mask);
      const b = rec.bounds;
      t.masks[frame] = { rle: { size: rle.size, counts: rle.counts }, bounds: [b.left, b.top, b.right, b.bottom] };
    }
  }
  return { complete: result.outcome?.status === 'completed', usage, tracks };
}

async function readStdin() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks).toString('utf8').replace(/^﻿/, '');
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith('index.mjs')) {
  const events = JSON.parse(await readStdin());
  process.stdout.write(JSON.stringify(await parseEvents(events)));
}
