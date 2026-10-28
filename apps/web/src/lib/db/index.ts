import path from "node:path";
import type { PgliteDatabase } from "drizzle-orm/pglite";
import * as schema from "./schema";

// One Drizzle API, two drivers, picked by env:
// - DATABASE_URL set  -> Neon serverless (HTTP) for production. Run `npm run db:migrate` on deploy.
// - otherwise         -> PGlite (embedded Postgres) in apps/web/.data for local dev; migrated and
//                        seeded with the sample community on first use.
export type DB = PgliteDatabase<typeof schema>;

const MIGRATIONS = path.join(process.cwd(), "drizzle");

export function pgliteDir(): string {
  return process.env.PGLITE_DIR ?? path.join(process.cwd(), ".data", "pglite");
}

async function openNeon(url: string): Promise<DB> {
  const { neon } = await import("@neondatabase/serverless");
  const { drizzle } = await import("drizzle-orm/neon-http");
  // neon-http shares the pg-core query builder; we never use transactions, so the cast is safe.
  return drizzle({ client: neon(url), schema }) as unknown as DB;
}

async function openPglite(opts: { migrate: boolean; seed: boolean }): Promise<DB> {
  const { mkdirSync } = await import("node:fs");
  const { PGlite } = await import("@electric-sql/pglite");
  const { drizzle } = await import("drizzle-orm/pglite");
  const dir = pgliteDir();
  mkdirSync(dir, { recursive: true });
  const client = new PGlite(dir);
  const db = drizzle({ client, schema });
  if (opts.migrate) {
    const { migrate } = await import("drizzle-orm/pglite/migrator");
    await migrate(db, { migrationsFolder: MIGRATIONS });
  }
  if (opts.seed) {
    const { seedSampleIfEmpty } = await import("./seed");
    await seedSampleIfEmpty(db);
  }
  return db;
}

const g = globalThis as unknown as { __emberscanDb?: Promise<DB> };

/** Shared connection for the app (one PGlite instance per process: it owns its data dir). */
export function getDb(): Promise<DB> {
  if (!g.__emberscanDb) {
    const url = process.env.DATABASE_URL;
    // SEED_SAMPLE=0 starts empty (no sample community), e.g. to record onboarding from scratch.
    g.__emberscanDb = url
      ? openNeon(url)
      : openPglite({ migrate: true, seed: process.env.SEED_SAMPLE !== "0" });
    g.__emberscanDb.catch(() => {
      g.__emberscanDb = undefined;
    });
  }
  return g.__emberscanDb;
}

/** For scripts: open without auto-seeding, and apply migrations for whichever driver is active. */
export async function openForScripts(): Promise<{ db: DB; close: () => Promise<void> }> {
  const url = process.env.DATABASE_URL;
  if (url) {
    const db = await openNeon(url);
    const { migrate } = await import("drizzle-orm/neon-http/migrator");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await migrate(db as any, { migrationsFolder: MIGRATIONS });
    return { db, close: async () => {} };
  }
  const db = await openPglite({ migrate: true, seed: false });
  return {
    db,
    close: async () => {
      await (db as unknown as { $client: { close: () => Promise<void> } }).$client.close();
    },
  };
}

export { schema };

/** For server components: marks the render as request-time (fresh data) before touching the DB. */
export async function requestDb(): Promise<DB> {
  const { connection } = await import("next/server");
  await connection();
  return getDb();
}
