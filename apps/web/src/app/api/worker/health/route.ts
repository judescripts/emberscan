import { connection } from "next/server";
import { workerHealth } from "@/lib/worker";

// GET /api/worker/health — lets the New scan screen say up front whether the pipeline is online.
export async function GET() {
  await connection();
  const ok = await workerHealth();
  return Response.json({ ok }, { headers: { "cache-control": "no-store" } });
}
