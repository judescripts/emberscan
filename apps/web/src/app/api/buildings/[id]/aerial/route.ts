import { getDb } from "@/lib/db";
import { getBuilding } from "@/lib/db/queries";
import { fetchAerial, hasAerial } from "@/lib/aerial";
import { isUuid } from "@/lib/ids";

// GET /api/buildings/:id/aerial: the building's aerial cover photo (USGS, public domain), fetched
// from its researched coordinates. Cached here and by the browser/CDN, since it rarely changes.

const cache = new Map<string, ArrayBuffer>(); // "lat,lon" -> jpeg

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  if (!isUuid(id)) return new Response(null, { status: 404 });
  const building = await getBuilding(await getDb(), id);
  if (!building || !hasAerial(building.note)) return new Response(null, { status: 404 });
  const key = `${building.note.lat},${building.note.lon}`;
  let jpeg = cache.get(key) ?? null;
  if (!jpeg) {
    jpeg = await fetchAerial(building.note.lat, building.note.lon);
    if (!jpeg) return new Response(null, { status: 502 });
    cache.set(key, jpeg);
  }
  return new Response(jpeg, {
    headers: { "content-type": "image/jpeg", "cache-control": "public, max-age=86400, s-maxage=604800" },
  });
}
