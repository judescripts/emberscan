import json
import time
from pathlib import Path

import pytest

from emberscan_workers.spend import Budget, BudgetExhausted


def _log(data: Path, scan_id: str, cost: float, at: float | None = None) -> None:
    d = data / scan_id
    d.mkdir(parents=True, exist_ok=True)
    rec = {
        "run_id": scan_id,
        "stage": "segment",
        "model": "sam-3.1",
        "cost_usd": cost,
        "units": {},
        "at": at if at is not None else time.time(),
    }
    with (d / "spend.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _budget(tmp_path: Path, **kw) -> Budget:
    return Budget(data_dir=tmp_path, per_run_usd=0.5, **kw)


def test_reserves_until_daily_cap(tmp_path: Path) -> None:
    b = _budget(tmp_path, daily_usd=1.0, max_concurrent=5)
    b.reserve("a")
    b.reserve("b")  # 2 x $0.50 held = $1.00, exactly the cap
    with pytest.raises(BudgetExhausted, match="Daily"):
        b.reserve("c")
    assert b.status()["scans_left_today"] == 0


def test_actual_spend_replaces_reservation_after_release(tmp_path: Path) -> None:
    b = _budget(tmp_path, daily_usd=1.0, max_concurrent=5)
    b.reserve("a")
    _log(tmp_path, "a", 0.12)
    b.release("a")
    s = b.status()
    assert s["spent_24h_usd"] == pytest.approx(0.12) and s["reserved_usd"] == 0
    assert s["scans_left_today"] == 1  # (1.00 - 0.12) // 0.50


def test_old_spend_counts_toward_total_not_daily(tmp_path: Path) -> None:
    _log(tmp_path, "old", 9.8, at=time.time() - 2 * 24 * 3600)
    b = _budget(tmp_path, daily_usd=5.0, total_usd=10.0)
    s = b.status()
    assert s["spent_24h_usd"] == 0 and s["spent_total_usd"] == pytest.approx(9.8)
    with pytest.raises(BudgetExhausted, match="Total"):
        b.reserve("a")


def test_concurrency_limit(tmp_path: Path) -> None:
    b = _budget(tmp_path, daily_usd=100, max_concurrent=1)
    b.reserve("a")
    with pytest.raises(BudgetExhausted, match="running"):
        b.reserve("b")
    b.release("a")
    b.reserve("b")


def test_ignores_bad_lines(tmp_path: Path) -> None:
    _log(tmp_path, "a", 0.2)
    with (tmp_path / "a" / "spend.jsonl").open("a", encoding="utf-8") as f:
        f.write("not json\n{}\n")
    assert _budget(tmp_path).status()["spent_total_usd"] == pytest.approx(0.2)
