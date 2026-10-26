import type { Metadata } from "next";
import { Suspense } from "react";
import { ScanForm } from "@/components/scan/scan-form";
import { ButtonLink, Card, PageHeader, SectionTitle, ShortDisclaimer, Skeleton } from "@/components/ui";
import { currentContext } from "@/lib/current";
import { listBuildings } from "@/lib/db/queries";
import { STAGE_INFO } from "@/lib/pipeline";
import { PIPELINE_STAGES } from "@/lib/report-types";

export const metadata: Metadata = { title: "New scan" };

export default function NewScanPage(props: PageProps<"/scan">) {
  return (
    <main>
      <PageHeader title="New scan" kicker="One building, one walkaround video" />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <FilmingGuide />
        <div className="flex flex-col gap-5">
          <Card>
            <SectionTitle kicker="Step 2">Upload the video</SectionTitle>
            <Suspense fallback={<Skeleton lines={2} />}>
              <FormSection searchParams={props.searchParams} />
            </Suspense>
          </Card>
          <Card>
            <SectionTitle kicker="What happens next">The pipeline</SectionTitle>
            <ol className="flex flex-col gap-2 text-sm">
              {PIPELINE_STAGES.map((s, i) => (
                <li key={s} className="flex gap-3">
                  <span className="w-5 shrink-0 text-right font-mono text-xs text-muted">{i + 1}</span>
                  <span>
                    <span className="font-semibold text-ink">{STAGE_INFO[s].title}</span>{" "}
                    <span className="font-mono text-xs text-muted">· {STAGE_INFO[s].tool}</span>
                    <span className="block text-muted">{STAGE_INFO[s].what}</span>
                  </span>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>
      <div className="mt-6">
        <ShortDisclaimer />
      </div>
    </main>
  );
}

async function FormSection({ searchParams }: { searchParams: PageProps<"/scan">["searchParams"] }) {
  const { building } = await searchParams;
  const { db, current } = await currentContext();
  if (!current) {
    return <ButtonLink href="/manage/new">+ New community</ButtonLink>;
  }
  const list = await listBuildings(db, current.id);
  if (list.length === 0) {
    return (
      <div>
        <p className="text-sm text-muted">Add a building to {current.name} first.</p>
        <ButtonLink href={`/manage/${current.id}`} className="mt-3">
          Add a building
        </ButtonLink>
      </div>
    );
  }
  const pre = typeof building === "string" && list.some((b) => b.id === building) ? building : null;
  return (
    <ScanForm
      initialBuilding={pre}
      buildings={list.map((b) => ({
        id: b.id,
        label: b.label,
        eave:
          b.eaveMode === "known" && b.eaveFt
            ? `Eave depth: ${b.eaveFt} ft (entered)`
            : "Eave depth: measured from the video (film one corner from below for 3 s)",
      }))}
    />
  );
}

function FilmingGuide() {
  return (
    <Card>
      <SectionTitle kicker="Step 1">How to film</SectionTitle>
      <ol className="flex flex-col gap-3 text-sm text-ink">
        <li>
          <strong>Print the scale marker</strong> and lay it <strong>flat on the ground</strong> with one edge touching the wall. It turns
          pixels into feet.{" "}
          <a href="/emberscan-scale-marker.pdf" className="font-semibold text-brand underline underline-offset-2" target="_blank" rel="noopener">
            Scale marker (PDF)
          </a>
        </li>
        <li>
          <strong>Step about 10 ft out</strong> from the wall and walk all the way around the building, holding the phone at chest
          height, landscape, slow and steady.
        </li>
        <li>
          Keep the <strong>ground line and the wall</strong> in view. Pause on anything close to the house: mulch, shrubs, firewood,
          fences, under decks.
        </li>
        <li>
          At one corner, hold a <strong>3-second shot</strong> looking up at the eaves so EmberScan can measure how deep they are.
        </li>
        <li>
          <strong>Talk as you go</strong> if it helps: “this woodpile is unit 6&apos;s”. Narration is matched to what&apos;s on screen.
        </li>
      </ol>
      <div
        aria-hidden
        className="mt-4 grid grid-cols-[1fr_auto] items-end gap-2 rounded-xl bg-soft p-3 text-[11px] text-muted"
      >
        <div className="relative h-16">
          <div className="absolute inset-x-0 top-0 h-10 rounded-t border border-b-0 border-muted bg-surface text-center leading-10">wall</div>
          <div className="absolute bottom-0 left-4 h-4 w-10 border border-ink bg-[repeating-linear-gradient(90deg,var(--text)_0_4px,transparent_4px_8px)] opacity-70" />
          <div className="absolute right-0 bottom-0 left-0 border-t border-dashed border-muted" />
        </div>
        <div className="text-right">
          marker flat,
          <br />
          edge on the wall
        </div>
      </div>
    </Card>
  );
}
