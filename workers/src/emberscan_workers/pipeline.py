"""End-to-end scan pipeline: video in, Report out (docs/contracts/README.md).

Stages: upload -> normalize -> frames -> segment (SAM 3.1, one request per concept, run
concurrently) -> measure (scale marker + ground plane) -> rules (deterministic engine) ->
narration (Voice Transcribe, alongside segmentation) -> agent (Muse Spark) -> report.
Every model call goes through the per-run SpendLedger.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import BBox, Evidence, Hazard, Range, Report
from .eave import EaveEstimate, estimate_eave
from .hazards import BY_CLASS, CORE, Concept
from .media import VideoInfo, extract_audio, extract_frames, join_clips, normalize, probe
from .meta import MetaClient
from .meta.agent import ScanTools, run_agent
from .meta.sam import SegmentationResult, Track, segment_video
from .meta.voice import Transcript, transcribe
from .rules import evaluate, load_pack
from .spend import SpendLedger, SpendLimitExceeded
from .spend.pricing import SAM_USD_PER_1K_FRAMES, sam_video_cost

STAGES = [
    "upload",
    "normalize",
    "frames",
    "segment",
    "measure",
    "eaves",
    "rules",
    "narration",
    "agent",
    "report",
]
SAM_FPS = float(os.environ.get("SAM_FPS", "3"))  # most frames per second sent to SAM
MIN_SAM_FPS = float(os.environ.get("MIN_SAM_FPS", "1"))
SAM_BUDGET_SHARE = 0.8  # of the per-run spend limit; the rest covers agent, eaves, narration


def sam_fps_for(duration_s: float, n_concepts: int, run_limit_usd: float) -> float:
    """Frame rate for SAM so every concept fits in the run budget (SAM bills per frame per
    concept): long footage gets fewer frames per second, down to MIN_SAM_FPS."""
    if duration_s <= 0 or n_concepts <= 0:
        return SAM_FPS
    frames = SAM_BUDGET_SHARE * run_limit_usd / (n_concepts * SAM_USD_PER_1K_FRAMES / 1000)
    return round(max(MIN_SAM_FPS, min(SAM_FPS, frames / duration_s)), 2)


SAM_CONCURRENCY = int(os.environ.get("SAM_CONCURRENCY", "6"))
MIN_TRACK_FRAMES = 3
MIN_SAM_CONFIDENCE = 0.3


@dataclass
class ScanJob:
    scan_id: str
    dir: Path
    video_path: Path
    building_label: str
    eave_depth_ft: Range | None = None
    include_proposed: bool = True
    concepts: list[Concept] = field(default_factory=lambda: list(CORE))
    # More walkaround clips after video_path (joined in order) and corner clips for eave depth.
    extra_clips: list[Path] = field(default_factory=list)
    corner_clips: list[Path] = field(default_factory=list)
    status: str = "queued"
    stage: str = "upload"
    progress: float = 0.0
    stages: list[dict[str, Any]] = field(
        default_factory=lambda: [{"name": s, "status": "pending", "detail": ""} for s in STAGES]
    )
    error: str | None = None
    sam_fps: float = SAM_FPS  # chosen per scan from the footage length (sam_fps_for)
    report: Report | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def public(self, with_report: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "scan_id": self.scan_id,
            "status": self.status,
            "stage": self.stage,
            "progress": round(self.progress, 3),
            "stages": self.stages,
            "error": self.error,
            "created_at": self.created_at,
        }
        if with_report and self.report is not None:
            out["report"] = self.report.model_dump(mode="json")
        return out


Notify = Callable[[ScanJob], Awaitable[None] | None]


class Progress:
    def __init__(self, job: ScanJob, notify: Notify | None) -> None:
        self.job, self.notify = job, notify

    async def set(self, stage: str, status: str, detail: str = "") -> None:
        for s in self.job.stages:
            if s["name"] == stage:
                s["status"], s["detail"] = status, detail
        if status == "running":
            self.job.stage = stage
        done = sum(1 for s in self.job.stages if s["status"] in ("done", "skipped"))
        self.job.progress = done / len(self.job.stages)
        if self.notify:
            r = self.notify(self.job)
            if asyncio.iscoroutine(r):
                await r


# ---------------------------------------------------------------- hazards from tracks


def _confidence(sam_conf: float | None, measured: str | None) -> str:
    sam = "high" if (sam_conf or 0) >= 0.7 else "medium" if (sam_conf or 0) >= 0.5 else "low"
    if measured is None:
        return sam
    order = ["low", "medium", "high"]
    return order[min(order.index(sam), order.index(measured))]


def hazards_from_tracks(results: list[SegmentationResult], sam_fps: float) -> list[Hazard]:
    hazards: list[Hazard] = []
    for res in results:
        concept = next((c for c in BY_CLASS.values() if c.prompt == res.concept), None)
        if concept is None or concept.cls in ("wall", "window", "door"):
            continue
        for tid, t in res.tracks.items():
            if len(t.frames) < MIN_TRACK_FRAMES or (t.mean_confidence or 0) < MIN_SAM_CONFIDENCE:
                continue
            best = (
                max(t.boxes, key=lambda i: t.boxes[i].confidence or 0) if t.boxes else t.frames[0]
            )
            b = t.boxes.get(best)
            ev = (
                [
                    Evidence(
                        frame_index=best,
                        timestamp_ms=int(best * 1000 / sam_fps),
                        bbox=BBox(left=b.left, top=b.top, right=b.right, bottom=b.bottom),
                    )
                ]
                if b
                else []
            )
            hazards.append(
                Hazard(
                    id=f"h-{concept.cls}-{tid}",
                    cls=concept.cls,
                    concept=concept.prompt,
                    track_id=tid,
                    label=concept.label,
                    frames=t.frames,
                    confidence=_confidence(t.mean_confidence, None),
                    sam_confidence=round(t.mean_confidence, 3) if t.mean_confidence else None,
                    evidence=ev,
                )
            )
    return hazards


def attach_narration(hazards: list[Hazard], transcript: Transcript | None, sam_fps: float) -> None:
    if not transcript:
        return
    for h in hazards:
        if not h.frames:
            continue
        turns = transcript.near(
            int(min(h.frames) * 1000 / sam_fps), int(max(h.frames) * 1000 / sam_fps)
        )
        if turns:
            h.narration = " ".join(t.text for t in turns)[:300]


# ---------------------------------------------------------------- measurement hook

MeasureFn = Callable[[list[Hazard], dict[str, Track], list[Path], ScanJob], list[Hazard]]


def _default_measure(
    hazards: list[Hazard], tracks: dict[str, Track], frames: list[Path], job: ScanJob
) -> list[Hazard]:
    """Measure distances with the scale marker (geometry package) when available."""
    try:
        from .geometry_bridge import measure_hazards  # wired once geometry lands
    except ImportError:
        return hazards
    return measure_hazards(hazards, tracks, frames, job)


# ---------------------------------------------------------------- run


async def run_scan(
    job: ScanJob,
    client: MetaClient,
    notify: Notify | None = None,
    measure: MeasureFn = _default_measure,
) -> Report:
    p = Progress(job, notify)
    job.status = "processing"
    ledger = SpendLedger.from_env(job.scan_id, log_path=job.dir / "spend.jsonl")
    try:
        await p.set("upload", "done", job.video_path.name)

        await p.set("normalize", "running")
        clips: list[dict[str, Any]] = []
        if job.extra_clips:
            parts = [job.video_path, *job.extra_clips]
            spans = await asyncio.to_thread(
                join_clips, [(p_.name, p_) for p_ in parts], job.dir / "joined.mp4"
            )
            clips = [vars(s) for s in spans]
            job.video_path = job.dir / "joined.mp4"
        src = probe(job.video_path)
        job.sam_fps = fps = sam_fps_for(src.duration_s, len(job.concepts), ledger.limit_usd)
        sam_est = sam_video_cost(round(src.duration_s * fps), requests=len(job.concepts))
        if sam_est > SAM_BUDGET_SHARE * ledger.limit_usd:
            raise SpendLimitExceeded(
                f"{src.duration_s / 60:.1f} min of footage needs about ${sam_est:.2f} of SAM 3.1 "
                f"tracking, over this scan's ${ledger.limit_usd:.2f} limit. Split it into two "
                "scans (for example two sides each)."
            )
        eave_task = asyncio.create_task(_eaves(job, client, ledger, p))
        norm = await asyncio.to_thread(normalize, job.video_path, job.dir / "normalized.mp4")
        sam_video = await asyncio.to_thread(
            normalize, job.video_path, job.dir / "sam.mp4", 720, 300.0, fps
        )
        await p.set(
            "normalize",
            "done",
            (f"{len(clips)} clips joined · " if clips else "")
            + f"{src.duration_s:.0f}s video · {norm.width}x{norm.height} · "
            f"{sam_video.frame_count} frames at {fps:g} fps for SAM 3.1",
        )

        await p.set("frames", "running")
        frames = await asyncio.to_thread(
            extract_frames, job.dir / "sam.mp4", job.dir / "frames", fps
        )
        await p.set("frames", "done", f"{len(frames)} frames extracted")

        narration_task = asyncio.create_task(_narration(job, client, ledger, norm, p))
        results = await _segment(job, client, ledger, sam_video, p)

        await p.set("measure", "running")
        tracks = {
            f"h-{BY_CLASS_BY_PROMPT[r.concept]}-{tid}": t
            for r in results
            for tid, t in r.tracks.items()
            if r.concept in BY_CLASS_BY_PROMPT
        }
        hazards = hazards_from_tracks(results, fps)
        hazards = await asyncio.to_thread(measure, hazards, tracks, [f.path for f in frames], job)
        measured = sum(1 for h in hazards if h.distance_ft is not None)
        await p.set(
            "measure", "done", f"{len(hazards)} hazards · {measured} measured with the marker"
        )

        transcript = await narration_task
        attach_narration(hazards, transcript, fps)

        estimate = await eave_task
        eave, eave_source = job.eave_depth_ft, ("entered" if job.eave_depth_ft else None)
        if eave is None and estimate is not None:
            eave, eave_source = estimate.depth_ft, "corner_video"

        await p.set("rules", "running")
        pack = load_pack("us-ca")
        engine = evaluate(hazards, pack, eave_depth_ft=eave, include_proposed=job.include_proposed)
        n = engine.score
        await p.set(
            "rules",
            "done",
            f"{len(engine.results)} rules · {n.fails} fail · "
            f"{n.reviews} need review · {n.passes} pass",
        )

        await p.set("agent", "running", "Muse Spark is planning fixes")
        agent = await run_agent(client, ledger, ScanTools(hazards, engine.results, transcript, fps))
        await p.set(
            "agent",
            "done",
            f"{len(agent.fixes)} fixes · "
            f"{sum(1 for s in agent.trace if s.kind == 'tool_call')} tool calls",
        )

        await p.set("report", "running")
        report = Report(
            scan_id=job.scan_id,
            building_label=job.building_label,
            created_at=datetime.now(UTC).isoformat(),
            pack_id=pack.pack_id,
            pack_version=pack.version,
            include_proposed=job.include_proposed,
            video={
                "duration_s": src.duration_s,
                "fps": src.fps,
                "width": norm.width,
                "height": norm.height,
                "sam_fps": fps,
                "clips": clips,
                "corner_clips": len(job.corner_clips),
            },
            eave_depth_ft=eave,
            eave_source=eave_source,
            eave_estimate=estimate.model_dump(exclude={"depth_ft"}) if estimate else None,
            hazards=hazards,
            results=engine.results,
            score=engine.score,
            fixes=agent.fixes,
            agent_trace=agent.trace,
            cost=ledger.summary(),
        )
        (job.dir / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
        job.report = report
        job.status = "done"
        await p.set("report", "done", f"Spent ${ledger.spent_usd:.3f}")
        return report
    except SpendLimitExceeded as e:
        job.status, job.error = "failed", f"Stopped to stay within the spend limit: {e}"
        await p.set(job.stage, "failed", job.error)
        raise
    except Exception as e:
        job.status, job.error = "failed", f"{type(e).__name__}: {e}"
        await p.set(job.stage, "failed", job.error)
        raise


BY_CLASS_BY_PROMPT = {c.prompt: c.cls for c in BY_CLASS.values()}


async def _segment(
    job: ScanJob, client: MetaClient, ledger: SpendLedger, sam_video: VideoInfo, p: Progress
) -> list[SegmentationResult]:
    await p.set("segment", "running", f"SAM 3.1: {len(job.concepts)} hazard types in parallel")
    file_id = await client.upload_file(job.dir / "sam.mp4")
    sem = asyncio.Semaphore(SAM_CONCURRENCY)
    done: list[str] = []
    t0 = time.monotonic()

    async def one(c: Concept) -> SegmentationResult | None:
        async with sem:
            try:
                r = await segment_video(
                    client,
                    ledger,
                    job.dir / "sam.mp4",
                    c.prompt,
                    sam_video.frame_count,
                    file_id=file_id,
                )
            except SpendLimitExceeded:
                raise
            except Exception as e:  # one concept failing shouldn't sink the scan
                done.append(f"{c.prompt}: error")
                await p.set("segment", "running", f"'{c.prompt}' failed ({type(e).__name__})")
                return None
            done.append(c.prompt)
            await p.set(
                "segment",
                "running",
                f"SAM 3.1: tracked '{c.prompt}' · {len(r.tracks)} object(s) · "
                f"{len(done)}/{len(job.concepts)} done",
            )
            return r

    try:
        results = [r for r in await asyncio.gather(*(one(c) for c in job.concepts)) if r]
    finally:
        await client.delete_file(file_id)
    objects = sum(len(r.tracks) for r in results)
    await p.set(
        "segment",
        "done",
        f"{len(results)}/{len(job.concepts)} hazard types · "
        f"{objects} objects tracked · {time.monotonic() - t0:.0f}s",
    )
    return results


async def _narration(
    job: ScanJob, client: MetaClient, ledger: SpendLedger, norm: VideoInfo, p: Progress
) -> Transcript | None:
    if not norm.has_audio:
        await p.set("narration", "skipped", "No audio track")
        return None
    await p.set("narration", "running", "Muse Voice Transcribe")
    try:
        wav = await asyncio.to_thread(
            extract_audio, job.dir / "normalized.mp4", job.dir / "audio.wav"
        )
        if wav is None:
            await p.set("narration", "skipped", "No audio track")
            return None
        t = await transcribe(client, ledger, wav)
    except SpendLimitExceeded:
        raise
    except Exception as e:
        await p.set("narration", "skipped", f"Transcription unavailable ({type(e).__name__})")
        return None
    await p.set("narration", "done", f"{len(t.turns)} narration turn(s)")
    return t


async def _eaves(
    job: ScanJob, client: MetaClient, ledger: SpendLedger, p: Progress
) -> EaveEstimate | None:
    """Eave depth from corner clips (runs alongside SAM). An entered depth always wins."""
    if job.eave_depth_ft is not None:
        await p.set("eaves", "skipped", "Eave depth entered by the owner")
        return None
    if not job.corner_clips:
        await p.set("eaves", "skipped", "No corner clips")
        return None
    await p.set("eaves", "running", f"Muse Spark reading {len(job.corner_clips)} corner clip(s)")
    try:
        est = await estimate_eave(client, ledger, job.corner_clips, job.dir)
    except SpendLimitExceeded:
        raise
    except Exception as e:  # an eave estimate is optional; never fail the scan over it
        await p.set("eaves", "skipped", f"Couldn't estimate ({type(e).__name__})")
        return None
    if est is None:
        await p.set("eaves", "done", "Overhang not visible in the corner clips")
        return None
    r = est.depth_ft
    if est.overhang == "none":
        await p.set("eaves", "done", "No eave overhang (flat roof or parapet)")
    else:
        await p.set("eaves", "done", f"About {r.min:g}-{r.max:g} ft ({est.confidence} confidence)")
    return est
