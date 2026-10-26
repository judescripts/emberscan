import { connection } from "next/server";
import { passcodeRequired, workerBudget, workerHealth } from "@/lib/worker";

// GET /api/worker/health: lets the New scan screen say up front whether the pipeline is online,
// whether a passcode is needed, and how many scans today's spend cap still allows.
export async function GET() {
  await connection();
  const ok = await workerHealth();
  const budget = ok ? await workerBudget() : null;
  return Response.json(
    { ok, passcodeRequired: passcodeRequired(), scansLeftToday: budget?.scans_left_today ?? null },
    { headers: { "cache-control": "no-store" } },
  );
}
