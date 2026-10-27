"use client";

import { useState } from "react";
import { cx } from "../ui";

export type Thumb = { id: string; n: number; label: string; tone: "fail" | "review" | "pass" | "neutral"; src: string | null };

const BG = { fail: "bg-fail", review: "bg-review", pass: "bg-pass", neutral: "bg-muted" } as const;

/** Thumbnail strip; "+N more" opens the rest in place instead of jumping away. */
export function ThumbStrip({ thumbs, max }: { thumbs: Thumb[]; max: number }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? thumbs : thumbs.slice(0, max);
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2" aria-label="Evidence for this fix">
      {shown.map((t) => (
        <a
          key={t.id}
          href={`#${t.id}`}
          className="group/thumb relative block h-16 w-16 shrink-0 overflow-hidden rounded-lg border border-line bg-soft"
          title={`${t.n}. ${t.label}: see evidence`}
        >
          {t.src ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={t.src} alt="" loading="lazy" className="h-full w-full object-cover transition-transform group-hover/thumb:scale-105" />
          ) : (
            <span className="flex h-full w-full items-center justify-center px-1 text-center text-[10px] text-muted">{t.label}</span>
          )}
          <span className={cx("absolute top-1 left-1 rounded px-1 text-[10px] font-bold text-surface", BG[t.tone])}>{t.n}</span>
          <span className="sr-only">
            {t.n}. {t.label}: see evidence
          </span>
        </a>
      ))}
      {thumbs.length > max && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          aria-expanded={expanded}
          className="flex h-16 min-w-16 items-center justify-center rounded-lg border border-dashed border-line px-2 text-xs font-semibold text-brand hover:bg-soft"
        >
          {expanded ? "Show fewer" : `+${thumbs.length - max} more`}
        </button>
      )}
    </div>
  );
}
