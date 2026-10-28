"""EmberScan's measured distance vs a vision model's guess vs a tape measure (docs/distance-check.md).

For every marker-measured hazard in a saved scan, take the clean frame the measurement came
from, draw the hazard's box in orange, and ask Muse Spark how far the boxed object is from the
wall. The model is told the marker's exact size, so it has the same scale EmberScan uses; it
just has to judge the distance by eye instead of with geometry. Writes one CSV row per hazard
with an empty ``tape_ft`` column to fill in on site.

    python scripts/distance_check.py <scan dir> [<scan dir> ...] [--out distance_check.csv]

About a third of a cent per hazard.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import tempfile
import time
from pathlib import Path

from emberscan_workers import service  # noqa: F401  (loads the repo .env)
from emberscan_workers.after_image import CHECK_MODEL, _data_url, _marked, _output_text, clean_frame
from emberscan_workers.contracts import Report
from emberscan_workers.geometry import MARKER_COLS, MARKER_ROWS, SQUARE_IN
from emberscan_workers.meta import MetaClient
from emberscan_workers.spend import SpendLedger, token_cost

TOKENS = (4_000, 6_000)  # medium reasoning can spend thousands of tokens before the reply

PROMPT = (
    "This is a frame from a phone video of a building's exterior. A printed sheet with a "
    f"{MARKER_COLS} x {MARKER_ROWS} checkerboard of exactly {SQUARE_IN:g}-inch squares lies flat "
    "on the ground, its short edge touching the base of the wall. Use it as your scale.\n"
    "Estimate the shortest distance along the ground from the base of the wall to the nearest "
    "part of the object in the orange box (a {label}). 0 means it touches the wall.\n"
    'Reply with JSON only: {{"distance_ft": number, "low_ft": number, "high_ft": number, '
    '"reason": "one short sentence"}}'
)


def _fmt(x: float) -> str:
    return f"{x:.1f}"


async def guess(client: MetaClient, ledger: SpendLedger, image: Path, label: str) -> dict:
    ledger.check("distance_guess", token_cost(CHECK_MODEL, *TOKENS))
    t0 = time.monotonic()
    resp = await client.create_response(
        {
            "model": CHECK_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT.format(label=label.lower())},
                        {"type": "input_image", "image_url": _data_url(image)},
                    ],
                }
            ],
            "reasoning": {"effort": "medium"},
            "max_output_tokens": TOKENS[1],
        }
    )
    usage = resp.get("usage") or {}
    tokens = (int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))
    ledger.record(
        "distance_guess",
        CHECK_MODEL,
        token_cost(CHECK_MODEL, *tokens),
        {"input_tokens": tokens[0], "output_tokens": tokens[1]},
        time.monotonic() - t0,
    )
    text = _output_text(resp)
    try:
        return json.loads(text[text.index("{") : text.rindex("}") + 1])
    except (ValueError, KeyError):
        return {"reason": f"unreadable reply: {text[:80]}"}


async def run(scans: list[Path], out: Path) -> None:
    ledger = SpendLedger(run_id="distance-check", limit_usd=0.50)
    rows = []
    async with MetaClient() as client:
        with tempfile.TemporaryDirectory() as tmp:
            for scan in scans:
                report = Report.model_validate_json((scan / "report.json").read_text("utf-8"))
                for h in report.hazards:
                    if h.method != "marker" or h.distance_ft is None or not h.evidence:
                        continue
                    frame = h.evidence[0].frame_index
                    marked = _marked(clean_frame(scan, frame), Path(tmp) / f"{h.id}.jpg", h)
                    g = await guess(client, ledger, marked, h.label)
                    rows.append(
                        {
                            "scan": scan.name,
                            "building": report.building_label,
                            "hazard": h.id,
                            "label": h.label,
                            "side": h.side,
                            "frame": frame,
                            "emberscan_min_ft": _fmt(h.distance_ft.min),
                            "emberscan_max_ft": _fmt(h.distance_ft.max),
                            "emberscan_confidence": h.confidence,
                            "model_ft": g.get("distance_ft", ""),
                            "model_low_ft": g.get("low_ft", ""),
                            "model_high_ft": g.get("high_ft", ""),
                            "model_reason": g.get("reason", ""),
                            "tape_ft": "",
                        }
                    )
                    print(
                        f"{h.id:18} EmberScan {_fmt(h.distance_ft.min)}-{_fmt(h.distance_ft.max)}"
                        f"  model {g.get('distance_ft', '?')}"
                    )
    if rows:
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"{len(rows)} hazards -> {out}  (${ledger.spent_usd:.3f})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("scans", nargs="+", type=Path)
    p.add_argument("--out", type=Path, default=Path("distance_check.csv"))
    a = p.parse_args()
    asyncio.run(run(a.scans, a.out))


if __name__ == "__main__":
    main()
