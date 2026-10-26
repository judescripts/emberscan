import Link from "next/link";
import type { ReactNode } from "react";
import type { RuleStatus } from "@/lib/report-types";
import { scoreLabel, scoreTone } from "@/lib/score";
import { statusWords } from "@/lib/format";
import { IconExternal } from "./icons";

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

const TONE: Record<"fail" | "review" | "pass" | "neutral", string> = {
  fail: "bg-fail-soft text-fail",
  review: "bg-review-soft text-review",
  pass: "bg-pass-soft text-pass",
  neutral: "bg-soft text-muted",
};

export function toneFor(status: RuleStatus | null | undefined): keyof typeof TONE {
  return status === "fail" ? "fail" : status === "needs-review" ? "review" : status === "pass" ? "pass" : "neutral";
}

export function Pill({ tone = "neutral", children, className }: { tone?: keyof typeof TONE; children: ReactNode; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold whitespace-nowrap", TONE[tone], className)}>
      {children}
    </span>
  );
}

export function StatusPill({ status }: { status: RuleStatus }) {
  return <Pill tone={toneFor(status)}>{statusWords(status)}</Pill>;
}

export function SampleBadge() {
  return (
    <span className="inline-flex items-center rounded-full border border-dashed border-muted px-2 py-0.5 text-[11px] font-semibold tracking-wide text-muted uppercase">
      Sample
    </span>
  );
}

export function ScoreBadge({ score, size = "md" }: { score: number; size?: "md" | "lg" }) {
  const tone = scoreTone(score);
  return (
    <span
      className={cx(
        "inline-flex flex-col items-center justify-center rounded-2xl font-bold tabular-nums",
        TONE[tone],
        size === "lg" ? "h-24 w-24 text-4xl" : "h-14 w-14 text-xl",
      )}
      aria-label={`Score ${score} of 100: ${scoreLabel(score)}`}
    >
      {score}
      <span className={cx("font-medium opacity-80", size === "lg" ? "text-xs" : "text-[10px]")}>/100</span>
    </span>
  );
}

export function Card({ children, className, ...rest }: { children: ReactNode; className?: string } & React.HTMLAttributes<HTMLElement>) {
  return (
    <section className={cx("rounded-2xl border border-line bg-surface p-4 sm:p-5", className)} {...rest}>
      {children}
    </section>
  );
}

export function SectionTitle({ children, kicker, id }: { children: ReactNode; kicker?: string; id?: string }) {
  return (
    <div className="mb-3">
      {kicker && <p className="text-xs font-semibold tracking-wider text-muted uppercase">{kicker}</p>}
      <h2 id={id} className="text-lg font-bold text-ink">
        {children}
      </h2>
    </div>
  );
}

export function Citation({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-xs font-medium text-brand underline decoration-line underline-offset-2 hover:decoration-brand"
    >
      {label}
      <IconExternal />
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

export function ButtonLink({ href, children, variant = "primary", className }: { href: string; children: ReactNode; variant?: "primary" | "secondary"; className?: string }) {
  return (
    <Link href={href} className={cx(buttonClass(variant), className)}>
      {children}
    </Link>
  );
}

export function buttonClass(variant: "primary" | "secondary" | "danger" | "ghost" = "primary") {
  const common =
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  switch (variant) {
    case "primary":
      return `${common} bg-brand text-brand-fg hover:opacity-90`;
    case "secondary":
      return `${common} border border-line bg-surface text-ink hover:bg-soft`;
    case "danger":
      return `${common} border border-fail text-fail hover:bg-fail-soft`;
    default:
      return `${common} text-ink hover:bg-soft`;
  }
}

export const inputClass =
  "w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink placeholder:text-muted focus-visible:border-brand";

export function PageHeader({ title, kicker, children }: { title: string; kicker?: ReactNode; children?: ReactNode }) {
  return (
    <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        {kicker && <div className="mb-1 text-sm text-muted">{kicker}</div>}
        <h1 className="text-2xl font-bold text-ink">{title}</h1>
      </div>
      {children}
    </header>
  );
}

export function ShortDisclaimer() {
  return (
    <p className="text-xs text-muted">
      EmberScan flags likely hazards from video. It is not an inspection and does not certify safety or compliance.
    </p>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading…</span>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="es-pulse h-20 rounded-2xl bg-soft" />
      ))}
    </div>
  );
}
