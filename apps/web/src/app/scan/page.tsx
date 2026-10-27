import type { Metadata } from "next";
import { Suspense } from "react";
import { MarkerExample } from "@/components/scan/marker-example";
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
      <PageHeader title="New scan" kicker="One building, a few short clips" />
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
            <div className="mt-4 rounded-xl border border-line bg-soft p-3 text-sm">
              <p className="font-semibold text-ink">Your privacy, built into the pipeline</p>
              <ul className="mt-1 flex list-disc flex-col gap-0.5 pl-5 text-muted">
                <li>People and license plates are found by SAM 3.1 and blurred in every kept frame.</li>
                <li>No blur check, no scan: it fails closed instead of keeping unblurred frames.</li>
                <li>The raw video and audio are deleted when the scan ends, even if it fails.</li>
                <li>After pictures are drawn from blurred frames and never add people.</li>
                <li>The report says what was blurred, under How it was made.</li>
              </ul>
            </div>
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
          b.eaveMode === "none"
            ? "No eave overhang (entered): no corner clips needed"
            : b.eaveMode === "known" && b.eaveFt
              ? `Eave depth: ${b.eaveFt} ft (entered)`
              : "Eave depth: estimated from corner clips (3–5 s each, filmed along the wall)",
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
          <strong>Print the scale marker</strong> at 100% and lay it <strong>flat on the ground</strong> with the orange{" "}
          <strong>WALL EDGE</strong> strip touching the base of the wall. It turns pixels into feet.{" "}
          <a href="/emberscan-scale-marker.pdf" className="font-semibold text-brand underline underline-offset-2" target="_blank" rel="noopener">
            Scale marker (PDF)
          </a>
        </li>
        <li>
          <strong>One short take per planting bed</strong> (8–10 s): put the marker in the middle of the bed, stand 6–10 ft back
          and film the bed with the sheet <strong>in view the whole time</strong>. Then move the marker to the next bed.
        </li>
        <li>
          Aim at the <strong>base of the wall</strong>. Plants, mulch, firewood and fences within about 8 ft of the sheet get
          measured. Portrait or landscape both work.
        </li>
        <li>
          <strong>Tag each clip&apos;s side</strong> (N/E/S/W) when you upload, or just say “north side…” while filming, so hazards
          land on the zone map.
        </li>
        <li>
          <strong>Eaves:</strong> if the roof overhangs, add 3–5 s corner clips filmed along the wall so the overhang shows. Flat
          roof or parapet? Set the building to “No overhang” and skip them.
        </li>
        <li>
          Keep people, licence plates and views inside out of frame. <strong>Talk as you go</strong> if it helps: “this woodpile
          is unit 6&apos;s”.
        </li>
      </ol>
      <MarkerExample />
    </Card>
  );
}