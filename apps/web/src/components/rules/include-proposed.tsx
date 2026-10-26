"use client";

import { useOptimistic, useTransition } from "react";
import { setIncludeProposed } from "@/app/actions";
import { cx } from "../ui";

/** Per-community switch: show proposed (not yet in force) rules, like California's Zone 0, in reports. */
export function IncludeProposedToggle({ communityId, initial }: { communityId: string; initial: boolean }) {
  const [pending, start] = useTransition();
  const [on, setOn] = useOptimistic(initial);
  return (
    <div className="flex items-start gap-3">
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-labelledby="include-proposed-label"
        aria-describedby="include-proposed-help"
        disabled={pending}
        onClick={() =>
          start(async () => {
            setOn(!on);
            await setIncludeProposed(communityId, !on);
          })
        }
        className={cx("relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition-colors", on ? "bg-brand" : "bg-line")}
      >
        <span className={cx("absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-surface shadow transition-transform", on && "translate-x-5")} />
      </button>
      <div>
        <p id="include-proposed-label" className="text-sm font-semibold text-ink">
          Include proposed rules
        </p>
        <p id="include-proposed-help" className="text-xs text-muted">
          Proposed rules never change the score. They show as “needs review” and feed the Zone 0 readiness meter. Applies to new scans.
        </p>
      </div>
    </div>
  );
}
