// npm run db:migrate — applies ./drizzle migrations to Neon (DATABASE_URL) or local PGlite (.data/).
// Stop `next dev` first when using PGlite: one process owns the data directory at a time.
import { openForScripts, pgliteDir } from "../src/lib/db";

async function main() {
  const { close } = await openForScripts();
  console.log(`Migrations applied (${process.env.DATABASE_URL ? "Neon via DATABASE_URL" : `PGlite at ${pgliteDir()}`}).`);
  await close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
