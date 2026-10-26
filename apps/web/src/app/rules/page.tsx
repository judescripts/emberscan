import type { Metadata } from "next";
import { Suspense } from "react";
import { IncludeProposedToggle } from "@/components/rules/include-proposed";
import { ButtonLink, Card, Citation, cx, PageHeader, ShortDisclaimer, Skeleton } from "@/components/ui";
import { currentContext } from "@/lib/current";
import { formatDate, rulePackStatusWords } from "@/lib/format";
import { getPack, packLabel, thresholdWords, ZONE_ORDER, type PackRule } from "@/lib/rules";

export const metadata: Metadata = { title: "Rules" };

export default function RulesPage() {
  return (
    <main>
      <Suspense fallback={<Skeleton lines={4} />}>
        <Rules />
      </Suspense>
      <div className="mt-6">
        <ShortDisclaimer />
      </div>
    </main>
  );
}

const STATUS_CHIP: Record<PackRule["status"], string> = {
  adopted: "bg-brand text-brand-fg",
  proposed: "border border-dashed border-ink text-ink",
  guidance: "bg-soft text-muted",
};

async function Rules() {
  const { current } = await currentContext();
  if (!current) return <ButtonLink href="/manage/new">+ New community</ButtonLink>;
  const pack = getPack(current.rulePack);
  const zones = [...pack.zones].sort((a, b) => ZONE_ORDER.indexOf(a.id) - ZONE_ORDER.indexOf(b.id));
  const zoneNote = typeof pack.status_notes.zone0 === "string" ? pack.status_notes.zone0 : null;
  const counts = {
    adopted: pack.rules.filter((r) => r.status === "adopted").length,
    proposed: pack.rules.filter((r) => r.status === "proposed").length,
    guidance: pack.rules.filter((r) => r.status === "guidance").length,
  };

  return (
    <>
      <PageHeader title="Rules" kicker={`${current.name} · ${packLabel(pack.pack_id)}`} />
      <Card className="mb-5">
        <p className="text-sm text-ink">
          Rule pack <span className="font-mono">{pack.pack_id}</span>, version {pack.version} (checked {formatDate(pack.checked_on)}):{" "}
          {counts.adopted} in force, {counts.proposed} proposed, {counts.guidance} guidance. Rules are data, checked by a fixed rules
          engine; every result links to its source.
        </p>
        <div className="mt-3">
          <IncludeProposedToggle communityId={current.id} initial={current.includeProposed} />
        </div>
        {zoneNote && (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer font-semibold text-ink">Where Zone 0 stands</summary>
            <p className="mt-1 text-muted">{zoneNote}</p>
          </details>
        )}
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer font-semibold text-ink">Where these rules apply</summary>
          <p className="mt-1 text-muted">{pack.applies_where}</p>
        </details>
      </Card>

      <div className="flex flex-col gap-5">
        {zones.map((z) => {
          const rules = pack.rules.filter((r) => r.zone === z.id);
          if (rules.length === 0) return null;
          return (
            <section key={z.id} aria-labelledby={`zone-${z.id}`}>
              <h2 id={`zone-${z.id}`} className="text-lg font-bold text-ink">
                {z.name}
              </h2>
              <p className="mb-2 text-sm text-muted">
                {z.min_ft}–{z.max_ft} ft · {z.note}
              </p>
              <ul className="flex flex-col gap-2">
                {rules.map((r) => {
                  const hidden = r.status === "proposed" && !current.includeProposed;
                  return (
                    <li key={r.id} id={r.id} className={cx("rounded-xl border border-line bg-surface p-3", hidden && "opacity-60")}>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={cx("rounded-full px-2 py-0.5 text-xs font-semibold", STATUS_CHIP[r.status])}>
                          {rulePackStatusWords(r.status)}
                        </span>
                        <span className="font-mono text-xs text-muted">{r.id}</span>
                        {r.effective_date && <span className="text-xs text-muted">Effective {formatDate(r.effective_date)}</span>}
                        {hidden && <span className="text-xs text-muted">Not shown in this community&apos;s reports</span>}
                      </div>
                      <h3 className="mt-1 font-semibold text-ink">{r.title}</h3>
                      <p className="text-sm text-ink">{r.plain_language}</p>
                      <p className="mt-1 text-xs text-muted">Threshold: {thresholdWords(r)}</p>
                      <div className="mt-1.5">
                        <Citation href={r.citation_url} label={r.citation_label} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}
      </div>
      <p className="mt-5 text-xs text-muted">{pack.disclaimer}</p>
    </>
  );
}
