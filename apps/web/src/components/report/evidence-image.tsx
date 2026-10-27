"use client";

import { useState } from "react";
import { cx } from "../ui";

export type Reason = { ruleId: string; title: string; status: "fail" | "needs-review" | "pass"; reason: string };

const DOT = { fail: "bg-fail", "needs-review": "bg-review", pass: "bg-pass" } as const;
const WORD = { fail: "Fails", "needs-review": "Check on site", pass: "Passes" } as const;

/**
 * Evidence frame with its "why" on demand: hover (desktop) or tap (phone) shows the measurement
 * and the rule reasons over the image; the image itself stays clean the rest of the time.
 */
export function EvidenceImage({
  src,
  alt,
  measurement,
  reasons,
  width,
  height,
}: {
  src: string;
  alt: string;
  measurement: string | null;
  reasons: Reason[];
  width?: number; // frame size, so the page reserves the space before the image loads
  height?: number;
}) {
  const [open, setOpen] = useState(false);
  const shown = reasons.filter((r) => r.status !== "pass");
  const hasWhy = Boolean(measurement) || shown.length > 0;
  return (
    <button
      type="button"
      className="group relative block w-full overflow-hidden rounded-xl bg-soft text-left"
      onClick={() => setOpen((o) => !o)}
      aria-expanded={hasWhy ? open : undefined}
      aria-label={hasWhy ? `${alt}. ${open ? "Hide" : "Show"} why it was flagged` : alt}
      disabled={!hasWhy}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} width={width} height={height} className="block h-auto w-full" loading="lazy" />
      {hasWhy && (
        <>
          <span
            className={cx(
              "absolute top-2 right-2 rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-semibold text-white transition-opacity",
              open ? "opacity-0" : "group-hover:opacity-0",
            )}
            aria-hidden
          >
            <span className="md:hidden">Tap for why</span>
            <span className="hidden md:inline">Hover for why</span>
          </span>
          <div
            className={cx(
              "absolute inset-x-0 bottom-0 max-h-full overflow-y-auto bg-gradient-to-t from-black/90 via-black/80 to-black/0 px-3 pt-8 pb-3 text-white transition-opacity",
              open ? "opacity-100" : "pointer-events-none opacity-0 group-hover:opacity-100",
            )}
          >
            <p className="text-[11px] font-semibold tracking-wide text-white/70 uppercase">Why it was flagged</p>
            {measurement && <p className="mt-1 text-sm font-semibold">{measurement}</p>}
            <ul className="mt-1.5 flex flex-col gap-1.5">
              {shown.map((r) => (
                <li key={r.ruleId} className="flex gap-2 text-xs leading-snug">
                  <span className={cx("mt-1 h-2 w-2 shrink-0 rounded-full", DOT[r.status])} aria-hidden />
                  <span>
                    <span className="font-semibold">
                      {WORD[r.status]} · {r.ruleId}
                    </span>{" "}
                    {r.reason}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </button>
  );
}
