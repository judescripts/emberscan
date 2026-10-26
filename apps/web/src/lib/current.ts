import { cookies } from "next/headers";
import { cache } from "react";
import { requestDb } from "./db";
import { listCommunities } from "./db/queries";

export const COMMUNITY_COOKIE = "es_community";

/** The signed-in-less hackathon model: the community switcher stores its choice in a cookie. */
export const currentContext = cache(async () => {
  const jar = await cookies();
  const db = await requestDb();
  const all = await listCommunities(db);
  const id = jar.get(COMMUNITY_COOKIE)?.value;
  const current = all.find((c) => c.id === id) ?? all[0] ?? null;
  return { db, communities: all, current };
});
