// npm run db:seed — migrates, then creates the "Willow Creek Townhomes" sample community
// (marked Sample) with two buildings and one sample scan. Safe to run twice.
// Stop `next dev` first when using PGlite: one process owns the data directory at a time.
import { openForScripts } from "../src/lib/db";
import { seedSample } from "../src/lib/db/seed";

async function main() {
  const { db, close } = await openForScripts();
  const community = await seedSample(db);
  console.log(`Sample community ready: ${community.name} (${community.id})`);
  await close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
