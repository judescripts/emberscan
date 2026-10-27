"""End-to-end scan pipeline: video in, Report out (docs/contracts/README.md).

Stages: upload -> normalize -> frames -> segment (SAM 3.1, one request per concept, run
concurrently, plus "person" and "license plate") -> privacy (blur them in every frame before
anything is kept) -> measure (scale marker + ground plane) -> rules (deterministic engine) ->
narration (Voice Transcribe, alongside segmentation) -> agent (Muse Spark) -> report.
Every model call goes through the per-run SpendLedger.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import shutil
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .after_image import illustrate_fixes
from .contracts import AgentStep, BBox, Evidence, Hazard, Range, Report
from .hazards import BY_CLASS, CORE, Concept
from .media import VideoInfo, extract_audio, extract_frames, join_clips, normalize, probe
from .meta import MetaClient
from .meta.agent import ScanTools, run_agent
from .meta.openweight import OpenWeightClient, open_weight_enabled
from .meta.sam import SegmentationResult, Track, segment_video
from .meta.voice import Transcript, transcribe
from .privacy import (
    PRIVACY_CONCEPTS,
    PRIVACY_PROMPTS,
    PrivacyReport,
    delete_raw,
    guard_frames,
    split_privacy,
)
from .rules import covered_distance, evaluate, load_pack
from .spend import SpendLedger, SpendLimitExceeded
from .spend.pricing import SAM_USD_PER_1K_FRAMES, sam_video_cost

STAGES = [
    "upload",
    "normalize",
    "frames",
    "narration",  # runs alongside segment
    "segment",
    "privacy",
    "measure",
    "rules",
    "agent",
    "report",
]
SAM_FPS = float(os.environ.get("SAM_FPS", "3"))  # most frames per second sent to SAM
MIN_SAM_FPS = float(os.environ.get("MIN_SAM_FPS", "1"))
MARKER_SHORT_SIDE = 1080  # resolution for marker detection
SAM_BUDGET_SHARE = 0.8  # of the per-run spend limit; the rest covers agent, narration, pictures


def sam_fps_for(duration_s: float, n_concepts: int, run_limit_usd: float) -> float:
    """Frame rate for SAM so every concept fits in the run budget (SAM bills per frame per
    concept): long footage gets fewer frames per second, down to MIN_SAM_FPS."""
    if duration_s <= 0 or n_concepts <= 0:
        return SAM_FPS
    frames = SAM_BUDGET_SHARE * run_limit_usd / (n_concepts * SAM_USD_PER_1K_FRAMES / 1000)
    # One frame of headroom, rounded down: the frame count is rounded later, and an estimate a
    # hair over the budget would refuse the scan.
    fps = math.floor((frames - 1) / duration_s * 100) / 100
    return max(MIN_SAM_FPS, min(SAM_FPS, fps))


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
    # More walkaround clips after video_path, joined in order.
    extra_clips: list[Path] = field(default_factory=list)
    site_type: str = "HOA"  # community type: HOA | Condo | Home | Commercial (agent wording)
    clip_sides: list[str] = field(
        default_factory=list
    )  # N/E/S/W per walkaround clip, "" if unknown
    status: str = "queued"
    stage: str = "upload"
    progress: float = 0.0
    stages: list[dict[str, Any]] = field(
        default_factory=lambda: [{"name": s, "status": "pending", "detail": ""} for s in STAGES]
    )
    error: str | None = None
    sam_fps: float = SAM_FPS  # chosen per scan from the footage length (sam_fps_for)
    marker_frames: list[Path] = field(default_factory=list)  # full-res twins of the SAM frames
    report: Report | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def sam_concepts(self) -> list[Concept]:
        """Hazard concepts plus the privacy ones (always on: the guard is not optional)."""
        return [*self.concepts, *PRIVACY_CONCEPTS]

    def stages_detail(self, name: str) -> str:
        return next((s["detail"] for s in self.stages if s["name"] == name), "")

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


SIDE_WORDS = {"north": "N", "east": "E", "south": "S", "west": "W"}
_SIDE_RE = re.compile(r"\b(north|east|south|west)(?:ern)?\s+(?:side|wall|face)\b", re.I)


def narration_sides(transcript: Transcript | None) -> list[tuple[int, str]]:
    """(time_ms, side) wherever the person filming names a side ("north side", "east wall")."""
    if not transcript:
        return []
    marks = []
    for t in transcript.turns:
        for m in _SIDE_RE.finditer(t.text):
            marks.append((t.start_ms, SIDE_WORDS[m.group(1).lower()]))
    return sorted(marks)


def assign_sides(
    hazards: list[Hazard],
    sam_fps: float,
    clips: list[dict[str, Any]],
    clip_sides: list[str],
    spoken: list[tuple[int, str]],
) -> int:
    """Give each hazard the side of the clip it was mostly seen in (when the uploader tagged
    clips), else the side last named in the narration before it appeared. Returns how many
    hazards got a side."""
    spans = clips or [{"start_s": 0.0, "duration_s": float("inf")}]
    n = 0
    for h in hazards:
        if not h.frames:
            continue
        votes: dict[str, int] = {}
        for f in h.frames:
            t = f / sam_fps
            for i, s in enumerate(spans):
                if s["start_s"] <= t < s["start_s"] + s["duration_s"]:
                    side = clip_sides[i] if i < len(clip_sides) else ""
                    if side in ("N", "E", "S", "W"):
                        votes[side] = votes.get(side, 0) + 1
                    break
        side = max(votes, key=lambda k: votes[k]) if votes else None
        if side is None and spoken:
            first_ms = min(h.frames) * 1000 / sam_fps
            said = [s for ms, s in spoken if ms <= first_ms + 1500]
            side = said[-1] if said else None
        if side:
            h.side = side
            n += 1
    return n


def split_at_clips(
    results: list[SegmentationResult], clips: list[dict[str, Any]], sam_fps: float
) -> None:
    """SAM tracks across the cut between joined clips can merge two different plants into one
    object. Split every track at clip boundaries (in place): object "3" seen in clips 1 and 3
    becomes "3" and "3c2"."""
    if len(clips) < 2:
        return
    edges = [round(c["start_s"] * sam_fps) for c in clips[1:]]

    def clip_of(frame: int) -> int:
        return sum(1 for e in edges if frame >= e)

    for res in results:
        out: dict[str, Track] = {}
        for tid, t in res.tracks.items():
            parts: dict[int, Track] = {}
            for f in t.frames:
                c = clip_of(f)
                part = parts.setdefault(c, Track(object_id=t.object_id, concept=t.concept))
                if f in t.boxes:
                    part.boxes[f] = t.boxes[f]
                if f in t.masks:
                    part.masks[f] = t.masks[f]
            first = min(parts) if parts else 0
            for c, part in parts.items():
                out[tid if c == first else f"{tid}c{c}"] = part
        res.tracks = out


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
    uploads = [job.video_path, *job.extra_clips]  # deleted when the scan ends
    guarded = False  # frames on disk are blurred
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
        n_sam = len(job.sam_concepts)
        job.sam_fps = fps = sam_fps_for(src.duration_s, n_sam, ledger.limit_usd)
        sam_est = sam_video_cost(round(src.duration_s * fps), requests=n_sam)
        if sam_est > SAM_BUDGET_SHARE * ledger.limit_usd:
            raise SpendLimitExceeded(
                f"{src.duration_s / 60:.1f} min of footage needs about ${sam_est:.2f} of SAM 3.1 "
                f"tracking, over this scan's ${ledger.limit_usd:.2f} limit. Split it into two "
                "scans (for example two sides each)."
            )
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
        if (
            min(src.width, src.height) > MARKER_SHORT_SIDE * 0.9
            and min(src.width, src.height) > 720
        ):
            # Same timestamps at higher resolution, for finding a small, slanted marker.
            await asyncio.to_thread(
                normalize, job.video_path, job.dir / "marker.mp4", MARKER_SHORT_SIDE, 300.0, fps
            )
            hi = await asyncio.to_thread(
                extract_frames, job.dir / "marker.mp4", job.dir / "frames_hi", fps
            )
            job.marker_frames = [f.path for f in hi]
        await p.set("frames", "done", f"{len(frames)} frames extracted")

        narration_task = asyncio.create_task(_narration(job, client, ledger, norm, p))
        results, private = split_privacy(await _segment(job, client, ledger, sam_video, p))
        split_at_clips(results, clips, fps)

        await p.set("privacy", "running", "Blurring people and license plates in every frame")
        privacy = await asyncio.to_thread(
            guard_frames, private, [f.path for f in frames], job.marker_frames or None
        )
        if not privacy.checked:  # fail closed: never keep frames nobody checked
            raise RuntimeError(
                "The privacy check for people and license plates couldn't run, so nothing "
                "was kept. Please try the scan again."
            )
        guarded = True
        await p.set("privacy", "done", privacy.summary())

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
        sided = assign_sides(hazards, fps, clips, job.clip_sides, narration_sides(transcript))
        if sided:
            await p.set(
                "narration",
                "done",
                f"{job.stages_detail('narration')} · {sided} hazards placed on a side",
            )

        # Eave depth comes from the owner (a depth, or 0 for no overhang); None = not sure.
        eave = job.eave_depth_ft
        eave_source = "entered" if eave is not None else None

        await p.set("rules", "running")
        pack = load_pack("us-ca")
        engine = evaluate(
            hazards,
            pack,
            eave_depth_ft=eave,
            include_proposed=job.include_proposed,
            covered_ft=covered_distance(hazards),
        )
        n = engine.score
        await p.set(
            "rules",
            "done",
            f"{len(engine.results)} rules · {n.fails} fail · "
            f"{n.reviews} need review · {n.passes} pass",
        )

        scan_tools = ScanTools(hazards, engine.results, transcript, fps)
        if open_weight_enabled():
            await p.set("agent", "running", "Muse Spark Open is planning fixes")
            async with OpenWeightClient() as open_client:
                agent = await run_agent(
                    client, ledger, scan_tools, site_type=job.site_type, open_client=open_client
                )
        else:
            await p.set("agent", "running", "Muse Spark is planning fixes")
            agent = await run_agent(client, ledger, scan_tools, site_type=job.site_type)
        await p.set("agent", "running", "Muse Image is drawing after pictures of the top fixes")
        pictures = await illustrate_fixes(client, ledger, agent.fixes, hazards, job.dir)
        # The loop as the report shows it: guard first, then plan / tools / verify, then picture.
        raw_deleted = await asyncio.to_thread(delete_raw, job.dir, uploads)
        privacy.raw_deleted = raw_deleted
        agent.trace.insert(0, privacy_step(privacy))
        if pictures:
            agent.trace.append(
                AgentStep(
                    kind="illustrate",
                    summary=f"Muse Image drew {pictures} after picture(s) from blurred frames; "
                    "Muse Spark checked each shows the fix and dropped any that didn't. "
                    "Labelled as AI illustrations, not evidence.",
                    detail={
                        "fixes": [f.id for f in agent.fixes if f.illustration],
                        "model": "muse-image-1.0",
                    },
                )
            )
        await p.set(
            "agent",
            "done",
            f"{len(agent.fixes)} fixes · "
            f"{sum(1 for s in agent.trace if s.kind == 'tool_call')} tool calls"
            + (f" · {agent.model['label']}" if agent.model else " · rule-based plan")
            + (f" · {pictures} after pictures (Muse Image)" if pictures else ""),
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
            },
            eave_depth_ft=eave,
            eave_source=eave_source,
            hazards=hazards,
            results=engine.results,
            score=engine.score,
            fixes=agent.fixes,
            agent_trace=agent.trace,
            agent_model=agent.model,
            privacy=privacy.as_dict(),
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
    finally:
        if job.status != "done":
            # A failed scan keeps nothing unblurred: raw video always, frames if not yet guarded.
            await asyncio.to_thread(delete_raw, job.dir, uploads)
            if not guarded:
                for d in ("frames", "frames_hi", "evidence", "after"):
                    shutil.rmtree(job.dir / d, ignore_errors=True)


def privacy_step(privacy: PrivacyReport) -> AgentStep:
    return AgentStep(
        kind="privacy",
        summary=f"Privacy guard (runs before anything is kept): {privacy.summary()} "
        + (
            "Raw video deleted after processing."
            if privacy.raw_deleted
            else "Raw video kept for local debugging."
        ),
        detail={
            "people": privacy.people,
            "plates": privacy.plates,
            "frames_blurred": privacy.frames_blurred,
            "found_by": "SAM 3.1",
        },
    )


BY_CLASS_BY_PROMPT = {c.prompt: c.cls for c in BY_CLASS.values()}


async def _segment(
    job: ScanJob, client: MetaClient, ledger: SpendLedger, sam_video: VideoInfo, p: Progress
) -> list[SegmentationResult]:
    concepts = job.sam_concepts
    await p.set(
        "segment",
        "running",
        f"SAM 3.1: {len(job.concepts)} hazard types + people and plates, in parallel",
    )
    file_id = await client.upload_file(job.dir / "sam.mp4")
    sem = asyncio.Semaphore(SAM_CONCURRENCY)
    done: list[str] = []
    t0 = time.monotonic()

    async def one(c: Concept) -> SegmentationResult | None:
        # The privacy concepts get a second try: without them the scan can't keep any frames.
        tries = 2 if c.prompt in PRIVACY_PROMPTS else 1
        async with sem:
            for attempt in range(tries):
                try:
                    r = await segment_video(
                        client,
                        ledger,
                        job.dir / "sam.mp4",
                        c.prompt,
                        sam_video.frame_count,
                        file_id=file_id,
                    )
                    break
                except SpendLimitExceeded:
                    raise
                except Exception as e:  # one concept failing shouldn't sink the scan
                    if attempt + 1 < tries:
                        continue
                    done.append(f"{c.prompt}: error")
                    await p.set("segment", "running", f"'{c.prompt}' failed ({type(e).__name__})")
                    return None
            done.append(c.prompt)
            await p.set(
                "segment",
                "running",
                f"SAM 3.1: tracked '{c.prompt}' · {len(r.tracks)} object(s) · "
                f"{len(done)}/{len(concepts)} done",
            )
            return r

    try:
        results = [r for r in await asyncio.gather(*(one(c) for c in concepts)) if r]
    finally:
        await client.delete_file(file_id)
    hazard_results = [r for r in results if r.concept not in PRIVACY_PROMPTS]
    objects = sum(len(r.tracks) for r in hazard_results)
    await p.set(
        "segment",
        "done",
        f"{len(hazard_results)}/{len(job.concepts)} hazard types · "
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
