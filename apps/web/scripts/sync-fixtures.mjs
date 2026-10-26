// Copies shared fixtures from the repo's docs/ into the web app so the app builds on its own.
// Runs before `next build` (see package.json "prebuild"). Missing sources are skipped.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const repo = join(web, "..", "..");

const copies = [
  ["docs/contracts/report.sample.json", "src/lib/sample-report.json"],
  ["docs/rules/us-ca.json", "src/lib/rules/us-ca.json"],
  ["docs/filming/emberscan-scale-marker.pdf", "public/emberscan-scale-marker.pdf"],
];

for (const [from, to] of copies) {
  const src = join(repo, from);
  const dest = join(web, to);
  if (!existsSync(src)) {
    console.log(`sync-fixtures: skip ${from} (not found)`);
    continue;
  }
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(src, dest);
  console.log(`sync-fixtures: ${from} -> ${to}`);
}
