"use client";

import { useEffect } from "react";
import { buttonClass, cx } from "../ui";

export type NavItem = { id: string; label: string };

function openFor(hash: string) {
  const id = decodeURIComponent(hash.replace(/^#/, ""));
  if (!id) return;
  const el = document.getElementById(id);
  if (!el) return;
  // open every folded section on the way to the target, then scroll to it
  let p: HTMLElement | null = el;
  while (p) {
    if (p instanceof HTMLDetailsElement) p.open = true;
    p = p.parentElement;
  }
  // after the sections open; again once lazy images above have had a moment to load and shift things
  for (const ms of [0, 350, 900]) setTimeout(() => el.scrollIntoView({ block: "start" }), ms);
}

/** Sticky jump bar for the report, plus collapse/expand all for its folding sections. */
export function ReportNav({ items }: { items: NavItem[] }) {
  useEffect(() => {
    const onHash = () => openFor(window.location.hash);
    const onClick = (e: MouseEvent) => {
      const a = (e.target as HTMLElement).closest?.("a[href^='#']") as HTMLAnchorElement | null;
      if (a && a.hash) setTimeout(() => openFor(a.hash), 0);
    };
    onHash();
    window.addEventListener("hashchange", onHash);
    document.addEventListener("click", onClick);
    return () => {
      window.removeEventListener("hashchange", onHash);
      document.removeEventListener("click", onClick);
    };
  }, []);

  const setAll = (open: boolean) =>
    document.querySelectorAll<HTMLDetailsElement>("details[data-report-section]").forEach((d) => (d.open = open));

  return (
    <nav
      aria-label="Report sections"
      className="sticky top-14 z-20 -mx-4 border-b border-line bg-bg/95 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-bg/80"
    >
      <div className="flex items-center gap-2">
        <ul className="flex min-w-0 flex-1 gap-1.5 overflow-x-auto [scrollbar-width:none]">
          {items.map((it) => (
            <li key={it.id} className="shrink-0">
              <a
                href={`#${it.id}`}
                className="block rounded-full border border-line bg-surface px-3 py-1 text-xs font-semibold text-ink hover:bg-soft"
              >
                {it.label}
              </a>
            </li>
          ))}
        </ul>
        <div className="hidden shrink-0 gap-1 sm:flex">
          <button type="button" className={cx(buttonClass("ghost"), "px-2 py-1 text-xs")} onClick={() => setAll(false)}>
            Collapse all
          </button>
          <button type="button" className={cx(buttonClass("ghost"), "px-2 py-1 text-xs")} onClick={() => setAll(true)}>
            Expand all
          </button>
        </div>
      </div>
    </nav>
  );
}
