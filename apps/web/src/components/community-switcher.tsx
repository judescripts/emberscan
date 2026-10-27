"use client";

import { useRouter } from "next/navigation";
import { useSyncExternalStore, useTransition } from "react";
import { selectCommunity } from "@/app/actions";

const NEW = "__new";
const MANAGE = "__manage";

const SELECT_CLASS =
  "w-full truncate rounded-lg md:w-auto md:max-w-xs border border-white/15 bg-white/10 py-1.5 pr-7 pl-2 text-sm font-semibold text-white [&>option]:text-black";

const noop = () => () => {};

export function CommunitySwitcher({
  communities,
  currentId,
}: {
  communities: { id: string; name: string; isSample: boolean }[];
  currentId: string | null;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  // The <select> is rendered only after hydration: Chrome on iOS tags form fields with
  // __gcruniqueid before React hydrates, which React reports as a mismatch. Until then a
  // look-alike placeholder shows the current community.
  const hydrated = useSyncExternalStore(noop, () => true, () => false);
  const current = communities.find((c) => c.id === currentId);
  return (
    <div className="min-w-0 flex-1 md:flex-none">
      <label htmlFor="community-switcher" className="sr-only">
        Community
      </label>
      {!hydrated ? (
        <span className={`block ${SELECT_CLASS}`}>{current ? current.name : "No community yet"}</span>
      ) : (
        <select
          id="community-switcher"
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
          className={SELECT_CLASS}
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
      )}
    </div>
  );
}
