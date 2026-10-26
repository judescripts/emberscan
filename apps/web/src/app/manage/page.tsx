import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { ButtonLink, PageHeader, Pill, SampleBadge, ShortDisclaimer, Skeleton } from "@/components/ui";
import { currentContext } from "@/lib/current";
import { latestDone, listBuildings, listScans } from "@/lib/db/queries";
import { packLabel } from "@/lib/rules";
import { pipelineSummary } from "@/lib/summary";

export const metadata: Metadata = { title: "Manage" };

export default function ManagePage() {
  return (
    <main>
      <PageHeader title="Manage communities">
        <div className="flex gap-2">
          <ButtonLink href="/rules" variant="secondary">
            Rules
          </ButtonLink>
          <ButtonLink href="/manage/new">+ New community</ButtonLink>
        </div>
      </PageHeader>
      <Suspense fallback={<Skeleton lines={2} />}>
        <Communities />
      </Suspense>
      <div className="mt-6">
        <ShortDisclaimer />
      </div>
    </main>
  );
}

async function Communities() {
  const { db, communities, current } = await currentContext();
  if (communities.length === 0) return <p className="text-muted">No communities yet.</p>;
  const cards = await Promise.all(
    communities.map(async (c) => {
      const bs = await listBuildings(db, c.id);
      const scans = await listScans(
        db,
        bs.map((b) => b.id),
      );
      const done = bs.map((b) => latestDone(scans, b.id)).filter((s) => s?.report);
      const hazards = done.reduce((n, s) => n + (s!.report!.hazards.length ?? 0), 0);
      const fails = done.reduce((n, s) => n + (s!.report!.score.fails ?? 0), 0);
      const sample = done[0]?.report ? pipelineSummary(done[0].report) : null;
      return { c, buildings: bs.length, scanned: done.length, hazards, fails, sample };
    }),
  );
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {cards.map(({ c, buildings, scanned, hazards, fails, sample }) => (
        <li key={c.id}>
          <Link href={`/manage/${c.id}`} className="block h-full rounded-2xl border border-line bg-surface p-4 hover:border-brand">
            <p className="flex flex-wrap items-center gap-2 font-bold text-ink">
              {c.name}
              {c.isSample && <SampleBadge />}
              {current?.id === c.id && <Pill>Current</Pill>}
            </p>
            <p className="text-sm text-muted">
              {c.type} · {c.place || "No place set"} · {packLabel(c.rulePack)}
              {c.includeProposed ? " · proposed rules on" : ""}
            </p>
            <p className="mt-2 text-sm text-ink">
              {buildings} building{buildings === 1 ? "" : "s"}, {scanned} scanned
              {scanned > 0 && ` · ${hazards} hazards tracked, ${fails} rule fail${fails === 1 ? "" : "s"}`}
            </p>
            {sample?.closest && <p className="text-xs text-muted">Closest: {sample.closest}</p>}
          </Link>
        </li>
      ))}
    </ul>
  );
}
