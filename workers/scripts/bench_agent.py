"""Hosted Muse Spark vs Muse Spark Open on Baseten, same scan, same tools and verifier (story D4).

Replays the fix-plan agent on a saved report's hazards and rule results (no video, no SAM) and
prints latency, tokens, cost, and what the verifier accepted. Each run calls both models for
real, so it costs money: about a cent per run per model.

    python scripts/bench_agent.py <scan dir or report.json> [--runs 3] [--site Commercial]
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from pathlib import Path

from emberscan_workers import service  # noqa: F401  (loads the repo .env)
from emberscan_workers.contracts import Report
from emberscan_workers.meta import MetaClient
from emberscan_workers.meta.agent import (
    AUDIENCE,
    DEFAULT_MODEL,
    SYSTEM,
    ScanTools,
    _HostedChat,
    _OpenChat,
    _run_agent_once,
)
from emberscan_workers.meta.openweight import OpenWeightClient
from emberscan_workers.spend import SpendLedger


async def bench(report: Report, runs: int, site: str) -> list[dict]:
    instructions = SYSTEM + ("\n" + AUDIENCE[site] if site in AUDIENCE else "")
    rows = []
    async with MetaClient() as meta, OpenWeightClient() as open_client:
        for name, make in (
            ("hosted", lambda: _HostedChat(meta, DEFAULT_MODEL, instructions)),
            ("open", lambda: _OpenChat(open_client, instructions)),
        ):
            for i in range(runs):
                tools = ScanTools(report.hazards, report.results, None, report.video["sam_fps"])
                ledger = SpendLedger(run_id=f"bench-{name}-{i}", limit_usd=0.50)
                chat = make()
                t0 = time.monotonic()
                try:
                    res = await _run_agent_once(chat, ledger, tools)
                    err = None
                except Exception as e:  # report it, keep benchmarking
                    res, err = None, f"{type(e).__name__}: {str(e)[:120]}"
                verify = next((s for s in (res.trace if res else []) if s.kind == "verify"), None)
                rows.append(
                    {
                        "provider": name,
                        "label": chat.label,
                        "seconds": round(time.monotonic() - t0, 1),
                        "turns": len(ledger.records),
                        "tokens_in": sum(r.units["input_tokens"] for r in ledger.records),
                        "tokens_out": sum(r.units["output_tokens"] for r in ledger.records),
                        "usd": round(ledger.spent_usd + ledger.partner_usd, 4),
                        "fixes": len(res.fixes) if res else 0,
                        "valid": bool(res and not res.fell_back),
                        "dropped": len(res.dropped) if res else 0,
                        "verify": verify.summary if verify else "-",
                        "error": err,
                    }
                )
                print(rows[-1], flush=True)
    return rows


def summarize(rows: list[dict]) -> None:
    print("\nprovider  runs  valid  p50 s  max s  mean $   fixes")
    for name in ("hosted", "open"):
        rs = [r for r in rows if r["provider"] == name]
        secs = [r["seconds"] for r in rs]
        print(
            f"{name:8}  {len(rs):4}  {sum(r['valid'] for r in rs):5}  "
            f"{statistics.median(secs):5.1f}  {max(secs):5.1f}  "
            f"{statistics.mean(r['usd'] for r in rs):.4f}  "
            f"{[r['fixes'] for r in rs]}"
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--site", default="Commercial")
    a = ap.parse_args()
    path = Path(a.report)
    path = path / "report.json" if path.is_dir() else path
    report = Report.model_validate_json(path.read_text(encoding="utf-8"))
    summarize(asyncio.run(bench(report, a.runs, a.site)))


if __name__ == "__main__":
    main()
