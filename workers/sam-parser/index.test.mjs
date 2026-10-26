import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseEvents } from './index.mjs';

const events = JSON.parse(
  readFileSync(new URL('../tests/fixtures/sam_bark_mulch_events.json', import.meta.url), 'utf8'),
);

test('recorded bark-mulch response parses into one tracked object', async () => {
  const t0 = performance.now();
  const out = await parseEvents(events);
  assert.ok(performance.now() - t0 < 10_000, 'parsing should take seconds, not minutes');
  assert.equal(out.complete, true);
  assert.equal(out.usage.video_frames_processed, 50);
  assert.deepEqual(Object.keys(out.tracks), ['0']);
  const t = out.tracks['0'];
  assert.equal(Object.keys(t.boxes).length, 24);
  assert.equal(Object.keys(t.masks).length, 24);
  assert.deepEqual(t.masks['0'].bounds, [0, 272, 1280, 720]);
  assert.equal(t.masks['0'].rle.size.length, 2);
  assert.ok(t.boxes['0'][4] > 0.5);
});
