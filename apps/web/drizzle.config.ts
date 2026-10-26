import { defineConfig } from "drizzle-kit";

// `npm run db:generate` writes SQL migrations to ./drizzle (committed).
// Apply them with `npm run db:migrate` (PGlite in ./.data locally, Neon when DATABASE_URL is set).
export default defineConfig({
  dialect: "postgresql",
  schema: "./src/lib/db/schema.ts",
  out: "./drizzle",
});
