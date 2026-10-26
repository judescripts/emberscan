import { costWords, effortWords, ownerWords } from "@/lib/format";
import type { Fix } from "@/lib/report-types";

/** Required/Recommended, effort, cost band and who's responsible. Neutral chips: these aren't statuses. */
export function FixTags({ fix }: { fix: Fix }) {
  const chip = "rounded-full bg-soft px-2 py-0.5 text-xs font-semibold text-ink";
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Fix details">
      <li className={fix.required ? "rounded-full bg-brand px-2 py-0.5 text-xs font-semibold text-brand-fg" : chip}>
        {fix.required ? "Required" : "Recommended"}
      </li>
      <li className={chip}>{effortWords(fix.effort)}</li>
      <li className={chip}>{costWords(fix.cost_band)}</li>
      <li className={chip}>{ownerWords(fix.owner)}</li>
    </ul>
  );
}
