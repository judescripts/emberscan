"""The worker on Modal (ADR 0001): the same FastAPI app as `uvicorn emberscan_workers.service:app`.

    modal deploy modal_app.py      # from workers/, after `modal token new`

Keys come from the Modal secret `emberscan-worker` (META_API_KEY, BASETEN_API_KEY, WORKER_TOKEN,
spend limits; see .env.example). Scans, uploads and the spend ledger live on the Volume
`emberscan-data`. One container only: scans run as in-process background tasks and the
budget is counted from files, so a second container would not see either.

The image mirrors the repo layout under /app, because the code finds the rule packs
(docs/rules) and the SAM parser (workers/sam-parser) relative to its own path.
"""

from __future__ import annotations

from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = "/data"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "curl", "ca-certificates")
    .run_commands(
        "curl -fsSL https://deb.nodesource.com/setup_22.x | bash -",
        "apt-get install -y nodejs",
    )
    .pip_install(
        "pydantic>=2.9,<3",
        "numpy>=2,<3",
        "pillow>=11,<13",
        "httpx>=0.27,<1",
        "opencv-python-headless>=4.10,<5",
        "fastapi>=0.115,<1",
        "python-multipart>=0.0.9",
    )
    .add_local_file(
        HERE / "sam-parser" / "package.json", "/app/workers/sam-parser/package.json", copy=True
    )
    .add_local_file(
        HERE / "sam-parser" / "package-lock.json",
        "/app/workers/sam-parser/package-lock.json",
        copy=True,
    )
    .run_commands("cd /app/workers/sam-parser && npm ci --omit=dev")
    .env({"PYTHONPATH": "/app/workers/src", "WORKER_DATA_DIR": f"{DATA}/scans"})
    .add_local_file(HERE / "sam-parser" / "index.mjs", "/app/workers/sam-parser/index.mjs")
    .add_local_dir(ROOT / "docs" / "rules", "/app/docs/rules")
    .add_local_dir(
        HERE / "src" / "emberscan_workers",
        "/app/workers/src/emberscan_workers",
        ignore=["**/__pycache__/**"],
    )
)

app = modal.App("emberscan-worker")
volume = modal.Volume.from_name("emberscan-data", create_if_missing=True)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("emberscan-worker")],
    volumes={DATA: volume},
    cpu=2.0,
    memory=4096,
    timeout=3600,
    max_containers=1,
    scaledown_window=1200,  # scans keep running after the request that started them returns
)
@modal.concurrent(max_inputs=50)
@modal.asgi_app()
def web():
    from emberscan_workers.service import app as fastapi_app

    return fastapi_app
