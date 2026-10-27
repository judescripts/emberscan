import { cx } from "../ui";

/**
 * A report section that folds. Native <details>, so it works without JavaScript; the report nav
 * opens it when a link points inside, and offers collapse/expand all.
 */
export function ReportSection({
  id,
  kicker,
  title,
  card = true,
  defaultOpen = true,
  children,
}: {
  id: string;
  kicker: string;
  title: React.ReactNode;
  card?: boolean;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  return (
    <details
      id={id}
      open={defaultOpen}
      data-report-section
      className={cx("group scroll-mt-28", card && "rounded-2xl border border-line bg-surface p-4 sm:p-5")}
    >
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 [&::-webkit-details-marker]:hidden">
        <span>
          <span className="block text-[11px] font-semibold tracking-wide text-muted uppercase">{kicker}</span>
          <span className="block text-lg font-bold text-ink">{title}</span>
        </span>
        <span
          aria-hidden
          className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-soft text-ink transition-transform group-open:rotate-180"
        >
          <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M4 6l4 4 4-4" />
          </svg>
        </span>
      </summary>
      <div className="mt-3">{children}</div>
    </details>
  );
}
