"""Worker HTTP API (docs/contracts/README.md). Run locally:

    .venv/bin/uvicorn emberscan_workers.service:app --port 8000

Scans run in-process as background tasks; state is persisted under WORKER_DATA_DIR so
finished reports survive restarts.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .contracts import Range, Report
from .hazards import BY_CLASS, CORE
from .meta import MetaClient
from .pipeline import ScanJob, run_scan
from .research import research_address_safe
from .spend import Budget, BudgetExhausted, SpendLedger

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_env_file() -> None:
    """Minimal .env loader (repo root .env), without overriding real env vars."""
    path = Path(os.environ.get("WORKER_ENV_FILE", REPO_ROOT / ".env"))
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if v.strip() and k.strip() not in os.environ:
            os.environ[k.strip()] = v.strip()


_load_env_file()
DATA_DIR = Path(os.environ.get("WORKER_DATA_DIR", REPO_ROOT / "workers" / ".data" / "scans"))
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
MAX_CLIPS = 40
ALLOWED_EXT = {".mp4", ".mov", ".m4v"}
SCAN_ID = re.compile(r"^[a-z0-9-]{8,64}$")
# Sliced uploads (PUT /uploads/...): clips arrive in pieces small enough for any proxy in
# front of the worker (Vercel functions accept 4.5 MB bodies), then POST /uploads/{id}/scan.
UPLOADS_DIR = DATA_DIR / "_uploads"
UPLOAD_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MAX_SLICE_BYTES = 50 * 1024 * 1024

app = FastAPI(title="EmberScan worker", version="0.1.0")
JOBS: dict[str, ScanJob] = {}
BUDGET = Budget.from_env(DATA_DIR)
RESEARCH_LIMIT_USD = float(os.environ.get("SPEND_LIMIT_USD_PER_RESEARCH", "0.05"))


def require_token(authorization: str | None = Header(default=None)) -> None:
    token = os.environ.get("WORKER_TOKEN")
    if token and authorization != f"Bearer {token}":
        raise HTTPException(401, "missing or wrong token")


def _save_state(job: ScanJob) -> None:
    (job.dir / "job.json").write_text(json.dumps(job.public(with_report=False)), encoding="utf-8")


def _load_job(scan_id: str) -> ScanJob | None:
    d = DATA_DIR / scan_id
    state = d / "job.json"
    if not state.exists():
        return None
    s = json.loads(state.read_text(encoding="utf-8"))
    job = ScanJob(scan_id=scan_id, dir=d, video_path=d, building_label="")
    job.status, job.stage, job.progress = s["status"], s["stage"], s["progress"]
    job.stages, job.error, job.created_at = s["stages"], s.get("error"), s.get("created_at", "")
    if job.status == "processing":  # the worker restarted mid-run
        job.status, job.error = "failed", "Worker restarted during processing; please rescan."
    rep = d / "report.json"
    if rep.exists():
        job.report = Report.model_validate_json(rep.read_text(encoding="utf-8"))
    return job


async def _run(job: ScanJob) -> None:
    try:
        async with MetaClient() as client:
            await run_scan(job, client, notify=_save_state)
    except Exception:
        pass  # error is recorded on the job
    finally:
        BUDGET.release(job.scan_id)
        _save_state(job)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "jobs": len(JOBS)}


@app.get("/budget", dependencies=[Depends(require_token)])
async def budget() -> dict:
    return BUDGET.status()


class ResearchRequest(BaseModel):
    address: str = Field(min_length=5, max_length=200)


@app.post("/research", dependencies=[Depends(require_token)])
async def research(req: ResearchRequest) -> dict:
    """Address research note (Muse Spark + public map data). Synchronous, ~10-30 s."""
    run_id = f"research-{uuid.uuid4().hex[:12]}"
    try:
        BUDGET.reserve(run_id, RESEARCH_LIMIT_USD, is_scan=False)
    except BudgetExhausted as e:
        raise HTTPException(429, str(e)) from e
    try:
        ledger = SpendLedger(run_id, RESEARCH_LIMIT_USD, DATA_DIR / run_id / "spend.jsonl")
        note = await research_address_safe(req.address.strip(), ledger)
        return note.model_dump(mode="json")
    finally:
        BUDGET.release(run_id)


@app.post("/scans", status_code=202, dependencies=[Depends(require_token)])
async def create_scan(
    video: list[UploadFile] = File(...),
    building_label: str = Form(...),
    eave_depth_ft: float | None = Form(default=None),
    include_proposed: bool = Form(default=True),
    concepts: str | None = Form(default=None),
    clip_sides: str | None = Form(default=None),
    community_type: str | None = Form(default=None),
) -> dict:
    """One or more walkaround clips (`video`, joined in order). Eave depth is entered, if known."""
    if len(video) > MAX_CLIPS:
        raise HTTPException(413, f"at most {MAX_CLIPS} clips per scan")
    for up in video:
        ext = Path(up.filename or "").suffix.lower() or ".mp4"
        if ext not in ALLOWED_EXT:
            raise HTTPException(415, f"unsupported video type {ext}; use MP4 or MOV")
    scan_id = uuid.uuid4().hex[:16]
    try:
        BUDGET.reserve(scan_id)  # before any upload work: refuse fast when over budget
    except BudgetExhausted as e:
        raise HTTPException(429, str(e)) from e
    d = DATA_DIR / scan_id
    d.mkdir(parents=True, exist_ok=True)
    total = 0

    async def save(up: UploadFile, name: str) -> Path:
        nonlocal total
        path = d / f"{name}{Path(up.filename or '').suffix.lower() or '.mp4'}"
        with path.open("wb") as f:
            while chunk := await up.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "videos are larger than 500 MB in total")
                f.write(chunk)
        return path

    try:
        walks = [await save(up, f"upload{i:02d}" if i else "upload") for i, up in enumerate(video)]
    except BaseException:
        BUDGET.release(scan_id)
        raise
    return _start(
        scan_id,
        d,
        walks,
        building_label,
        eave_depth_ft,
        include_proposed,
        concepts,
        clip_sides,
        community_type,
    )


def _start(
    scan_id: str,
    d: Path,
    walks: list[Path],
    building_label: str,
    eave_depth_ft: float | None,
    include_proposed: bool,
    concepts: str | None,
    clip_sides: str | None,
    community_type: str | None,
) -> dict:
    chosen = list(CORE)
    if concepts:
        names = [c.strip() for c in concepts.split(",") if c.strip()]
        chosen = [BY_CLASS[n] for n in names if n in BY_CLASS] or chosen
    eave = (  # 0 is a real answer: no overhang (flat roof, parapet)
        Range(min=eave_depth_ft, max=eave_depth_ft)
        if eave_depth_ft is not None and 0 <= eave_depth_ft <= 10
        else None
    )
    job = ScanJob(
        scan_id=scan_id,
        dir=d,
        video_path=walks[0],
        building_label=building_label[:120],
        eave_depth_ft=eave,
        include_proposed=include_proposed,
        concepts=chosen,
        extra_clips=walks[1:],
        site_type=community_type
        if community_type in ("HOA", "Condo", "Home", "Commercial")
        else "HOA",
        clip_sides=[
            s.strip().upper() if s.strip().upper() in ("N", "E", "S", "W") else ""
            for s in (clip_sides or "").split(",")
        ][: len(walks)],
    )
    JOBS[scan_id] = job
    _save_state(job)
    asyncio.create_task(_run(job))
    return {"scan_id": scan_id}


def _upload_dir(upload_id: str) -> Path:
    if not UPLOAD_ID.match(upload_id):
        raise HTTPException(404, "no such upload")
    return UPLOADS_DIR / upload_id


@app.put("/uploads/{upload_id}/{clip}", dependencies=[Depends(require_token)])
async def put_slice(upload_id: str, clip: int, offset: int, request: Request):
    """Append one slice to clip `clip`. `offset` must equal the bytes already stored, so a
    retried slice is never written twice; on a mismatch the reply says what is stored."""
    if not 0 <= clip < MAX_CLIPS or offset < 0:
        raise HTTPException(400, "bad slice")
    d = _upload_dir(upload_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / str(clip)
    have = path.stat().st_size if path.exists() else 0
    if have != offset:
        return JSONResponse({"error": "offset", "have": have}, status_code=409)
    n = 0
    with path.open("ab") as f:
        async for chunk in request.stream():
            n += len(chunk)
            if n > MAX_SLICE_BYTES or have + n > MAX_UPLOAD_BYTES:
                f.truncate(have)
                raise HTTPException(413, "slice or video too large")
            f.write(chunk)
    return {"size": have + n}


class UploadScan(BaseModel):
    names: list[str] = Field(min_length=1, max_length=MAX_CLIPS)
    building_label: str = Field(max_length=200)
    eave_depth_ft: float | None = None
    include_proposed: bool = True
    concepts: str | None = None
    clip_sides: str | None = None
    community_type: str | None = None


@app.post("/uploads/{upload_id}/scan", status_code=202, dependencies=[Depends(require_token)])
async def scan_from_upload(upload_id: str, req: UploadScan) -> dict:
    """Start a scan from the clips sent with PUT /uploads (one per name, in order)."""
    up = _upload_dir(upload_id)
    files = [up / str(i) for i in range(len(req.names))]
    stored = {p.name for p in up.iterdir()} if up.is_dir() else set()
    if stored != {f.name for f in files}:
        raise HTTPException(400, "the upload is incomplete")
    exts = [Path(n).suffix.lower() or ".mp4" for n in req.names]
    if any(e not in ALLOWED_EXT for e in exts):
        raise HTTPException(415, "unsupported video type; use MP4 or MOV")
    scan_id = uuid.uuid4().hex[:16]
    try:
        BUDGET.reserve(scan_id)
    except BudgetExhausted as e:
        shutil.rmtree(up, ignore_errors=True)
        raise HTTPException(429, str(e)) from e
    d = DATA_DIR / scan_id
    d.mkdir(parents=True, exist_ok=True)
    walks = [
        f.replace(d / f"{f'upload{i:02d}' if i else 'upload'}{ext}")
        for i, (f, ext) in enumerate(zip(files, exts, strict=True))
    ]
    shutil.rmtree(up, ignore_errors=True)
    return _start(
        scan_id,
        d,
        walks,
        req.building_label,
        req.eave_depth_ft,
        req.include_proposed,
        req.concepts,
        req.clip_sides,
        req.community_type,
    )


def _job(scan_id: str) -> ScanJob:
    if not SCAN_ID.match(scan_id):
        raise HTTPException(404, "no such scan")
    job = JOBS.get(scan_id)
    if job is None or job.status in ("done", "failed"):
        # A finished scan's report.json can be rewritten (e.g. its after pictures redrawn), so
        # it is read from disk rather than served from memory.
        job = _load_job(scan_id) or job
    if job is None:
        raise HTTPException(404, "no such scan")
    JOBS[scan_id] = job
    return job


@app.get("/scans/{scan_id}", dependencies=[Depends(require_token)])
async def get_scan(scan_id: str) -> dict:
    return _job(scan_id).public()


@app.get("/scans/{scan_id}/files/{path:path}", dependencies=[Depends(require_token)])
async def get_file(scan_id: str, path: str) -> FileResponse:
    job = _job(scan_id)
    target = (job.dir / path).resolve()
    if job.dir.resolve() not in target.parents or not target.is_file():
        raise HTTPException(404, "no such file")
    if target.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(404, "no such file")
    return FileResponse(target)
