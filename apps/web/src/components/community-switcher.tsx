"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { selectCommunity } from "@/app/actions";

const NEW = "__new";
const MANAGE = "__manage";

export function CommunitySwitcher({
  communities,
  currentId,
}: {
  communities: { id: string; name: string; isSample: boolean }[];
  currentId: string | null;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <div className="min-w-0 flex-1 md:flex-none">
      <label htmlFor="community-switcher" className="sr-only">
        Community
      </label>
      <select
        id="community-switcher"
        // Chrome on iOS tags form fields with __gcruniqueid before React hydrates; harmless.
        suppressHydrationWarning
        value={currentId ?? NEW}
        disabled={pending}
        onChange={(e) => {
          const v = e.target.value;
          if (v === NEW) {
            router.push("/manage/new");
            return;
          }
          if (v === MANAGE) {
            router.push("/manage");
            return;
          }
          start(() => selectCommunity(v));
        }}
        className="w-full truncate rounded-lg md:w-auto md:max-w-xs border border-white/15 bg-white/10 py-1.5 pr-7 pl-2 text-sm font-semibold text-white [&>option]:text-black"
      >
        {communities.length === 0 && <option value={NEW}>No community yet</option>}
        {communities.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
            {c.isSample ? " (Sample)" : ""}
          </option>
        ))}
        <option value={NEW}>+ New community</option>
        <option value={MANAGE}>Manage communities…</option>
      </select>
    </div>
  );
}
