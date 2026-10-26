import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { Suspense } from "react";
import { AgentTrace } from "@/components/report/agent-trace";
import { EvidenceList } from "@/components/report/evidence";
import { Findings } from "@/components/report/findings";
import { FixTags } from "@/components/report/fix-tags";
import { FixTracker } from "@/components/report/fix-tracker";
import { SinceLastScan } from "@/components/report/since-last";
import { ZoneMap } from "@/components/report/zone-map";
import { Card, cx, Pill, SampleBadge, ScoreBadge, SectionTitle, Skeleton } from "@/components/ui";
import { requestDb } from "@/lib/db";
import { getBuilding, getCommunity, getScan, listScans, listTasks } from "@/lib/db/queries";
import { formatDate, formatRange, sideWords } from "@/lib/format";
import { DEFAULT_DISCLAIMER } from "@/lib/report-types";
import { getPack, packLabel } from "@/lib/rules";
import { projectedScore, scoreLabel, topFixes } from "@/lib/score";
import { taskRuleId } from "@/lib/tasks";
import { isUuid } from "@/lib/ids";

export const metadata: Metadata = { title: "Report" };

export default function ReportPage(props: PageProps<"/report/[scanId]">) {
  return (
    <main>
      <Suspense fallback={<Skeleton lines={5} />}>
        <ReportView params={props.params} />
      </Suspense>
    </main>
  );
}

async function ReportView({ params }: { params: PageProps<"/report/[scanId]">["params"] }) {
  const { scanId } = await params;
  if (!isUuid(scanId)) notFound();
  const db = await requestDb();
  const scan = await getScan(db, scanId);
  if (!scan) notFound();
  if (!scan.report) redirect(`/scan/${scan.id}`);
  const report = scan.report;
  const building = await getBuilding(db, scan.buildingId);
  if (!building) notFound();
  const community = await getCommunity(db, building.communityId);
  const history = await listScans(db, [building.id]);
  const prevScan = history.find((s) => s.id !== scan.id && s.status === "done" && s.report && s.createdAt < scan.createdAt);
  const tasks = await listTasks(db, [building.id]);
  const taskByRule = new Map(tasks.map((t) => [t.ruleId, t]));
  const pack = getPack(report.pack_id);
  const plain = Object.fromEntries(pack.rules.map((r) => [r.id, r.plain_language]));
  const start = topFixes(report.fixes, 3);
  const projected = projectedScore(report, start);
  const allFixes = topFixes(report.fixes, report.fixes.length);
  const imageBase = scan.workerScanId ? `/api/scans/${scan.id}/files` : null;
  const isLatest = history.find((s) => s.status === "done" && s.report)?.id === scan.id;
  const z0 = report.score;
  const eave = report.eave_depth_ft
    ? report.eave_depth_ft.max === 0
      ? `No eave overhang (${report.eave_source === "corner_video" ? "seen in corner clips" : "entered"})`
      : report.eave_source === "corner_video"
      ? `Eaves about ${formatRange(report.eave_depth_ft)} deep (estimated from corner clips, ${report.eave_estimate?.confidence ?? "low"} confidence)`
      : report.eave_source === "entered"
        ? `Eaves ${formatRange(report.eave_depth_ft)} deep (entered)`
        : `Eaves about ${formatRange(report.eave_depth_ft)} deep (measured)`
    : building.eaveMode === "known" && building.eaveFt
      ? `Eaves ${building.eaveFt} ft deep (entered)`
      : "Eave depth not measured";

  return (
    <article className="flex flex-col gap-5">
      {/* 1. Header */}
      <header>
        <div className="mb-1 flex flex-wrap items-center gap-2 text-sm text-muted">
          {scan.isSample && <SampleBadge />}
          <span>{community?.name}</span>
        </div>
        <h1 className="text-2xl font-bold text-ink">{building.label}</h1>
        <p className="mt-1 text-sm text-muted">
          Scanned {formatDate(report.created_at)} · {packLabel(report.pack_id)} rules, version {report.pack_version}
          {report.include_proposed ? " · proposed Zone 0 rules shown" : ""} · {eave}
          {report.video?.duration_s ? ` · ${Math.round(Number(report.video.duration_s))} s walkaround` : ""}
        </p>
        <p className="mt-2 rounded-lg bg-soft px-3 py-2 text-xs text-ink">
          Flags likely hazards from video. Not an inspection, and it does not certify that this property is safe or compliant.
        </p>
        {!isLatest && (
          <p className="mt-2 text-sm font-semibold text-review">This is an older scan of this building. Fix status shows today&apos;s state.</p>
        )}
      </header>

      {/* 2. Score */}
      <Card aria-labelledby="score-title">
        <div className="flex flex-wrap items-center gap-4">
          <ScoreBadge score={report.score.score} size="lg" />
          <div className="min-w-0 flex-1">
            <h2 id="score-title" className="text-xl font-bold text-ink">
              {scoreLabel(report.score.score)}
            </h2>
            <p className="text-sm text-muted">Score counts rules in force today. Proposed Zone 0 rules are tracked separately below.</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Pill tone="fail">{report.score.fails} fail</Pill>
              <Pill tone="review">{report.score.reviews} need review</Pill>
              <Pill tone="pass">{report.score.passes} pass</Pill>
              <Pill>{report.hazards.length} hazards tracked</Pill>
            </div>
          </div>
        </div>
        <div className="mt-4">
          <div className="flex items-baseline justify-between text-sm">
            <span className="font-semibold text-ink">Zone 0 readiness (proposed rules)</span>
            <span className="text-muted tabular-nums">
              {z0.zone0_met} of {z0.zone0_total} met
            </span>
          </div>
          <div
            className="mt-1 h-2.5 overflow-hidden rounded-full bg-soft"
            role="meter"
            aria-label="Zone 0 readiness"
            aria-valuemin={0}
            aria-valuemax={z0.zone0_total || 1}
            aria-valuenow={z0.zone0_met}
          >
            <div className="h-full rounded-full bg-brand" style={{ width: `${z0.zone0_total ? (z0.zone0_met / z0.zone0_total) * 100 : 0}%` }} />
          </div>
          <p className="mt-1 text-xs text-muted">Zone 0 (the first 5 ft) isn&apos;t law yet in California. This shows how ready the building is if it passes.</p>
        </div>
        {report.score.unfilmed_sides.length > 0 && (
          <p className="mt-3 text-sm text-review">
            Not filmed: {report.score.unfilmed_sides.map(sideWords).join(", ")}. The score is capped at 80 until every side is filmed.
          </p>
        )}
      </Card>

      {/* 3. Start here */}
      <Card aria-labelledby="start-here">
        <SectionTitle id="start-here" kicker="Start here">
          {start.length ? `Top ${start.length} fixes` : "No fixes suggested"}
        </SectionTitle>
        {start.length > 0 && (
          <>
            <p className="mb-3 text-sm text-ink">
              Do these and rescan: score <strong>{report.score.score}</strong> → <strong>{projected}</strong>{" "}
              <span className="text-muted">({scoreLabel(projected)})</span>
            </p>
            <ol className="flex flex-col gap-3">
              {start.map((f, i) => (
                <li key={f.id} className="flex gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-soft text-sm font-bold text-ink">{i + 1}</span>
                  <div className="min-w-0">
                    <a href={`#fix-${f.id}`} className="font-semibold text-ink underline decoration-line underline-offset-2 hover:decoration-brand">
                      {f.title}
                    </a>
                    <p className="text-sm text-muted">{f.why}</p>
                    <div className="mt-1.5">
                      <FixTags fix={f} owner={taskByRule.get(taskRuleId(f))?.responsibility} />
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </>
        )}
      </Card>

      {/* 4. Zone map */}
      <Card aria-labelledby="zone-map">
        <SectionTitle id="zone-map" kicker="Where things are">
          Zone map
        </SectionTitle>
        <ZoneMap hazards={report.hazards} results={report.results} buildingLabel={building.label} />
      </Card>

      {/* 5. Evidence */}
      <section aria-labelledby="evidence">
        <SectionTitle id="evidence" kicker="Tracked across the video">
          Evidence
        </SectionTitle>
        <EvidenceList report={report} imageBase={imageBase} />
      </section>

      {/* 6. Agent trace */}
      <section aria-labelledby="agent-trace">
        <AgentTrace report={report} />
      </section>

      {/* 7. Since last scan */}
      <Card aria-labelledby="since-last">
        <SectionTitle id="since-last" kicker="Progress">
          Since last scan
        </SectionTitle>
        <SinceLastScan report={report} previous={prevScan?.report ? { report: prevScan.report, createdAt: prevScan.createdAt } : null} />
      </Card>

      {/* 8. All fixes, with tracking */}
      <section aria-labelledby="all-fixes">
        <SectionTitle id="all-fixes" kicker="Fix plan">
          All fixes ({allFixes.length})
        </SectionTitle>
        <ol className="flex flex-col gap-3">
          {allFixes.map((f) => {
            const t = taskByRule.get(taskRuleId(f));
            return (
              <li key={f.id} id={`fix-${f.id}`} className="target-ring scroll-mt-20 rounded-2xl border border-line bg-surface p-4">
                <h3 className="font-bold text-ink">{f.title}</h3>
                <p className="mt-0.5 text-sm text-muted">{f.why}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <FixTags fix={f} owner={t?.responsibility} />
                  {f.rule_ids.map((id) => (
                    <a key={id} href={`#rule-${id}`} className="font-mono text-xs text-brand underline underline-offset-2">
                      {id}
                    </a>
                  ))}
                </div>
                <div className="mt-3">
                  <FixTracker
                    task={t ? { id: t.id, status: t.status, responsibility: t.responsibility, owner: t.owner, notes: t.notes } : null}
                  />
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      {/* 9. Findings by rule */}
      <Card aria-labelledby="findings">
        <SectionTitle id="findings" kicker="Every rule checked">
          Findings by rule
        </SectionTitle>
        <Findings results={report.results} hazards={report.hazards} plain={plain} />
      </Card>

      {/* 10. Full disclaimer */}
      <footer className={cx("rounded-2xl border border-line bg-soft p-4 text-sm text-ink")}>
        <h2 className="mb-1 font-bold">About this report</h2>
        <p>{report.disclaimer || DEFAULT_DISCLAIMER}</p>
        <p className="mt-2 text-xs text-muted">{pack.disclaimer}</p>
        <p className="mt-2 text-xs text-muted">
          Distances come from the video and are shown as ranges. Rules are checked by a fixed, tested rules engine; the AI agent explains and prioritizes but cannot change a result.
        </p>
      </footer>
    </article>
  );
}
