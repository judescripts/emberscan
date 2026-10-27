"""Account-wide spend caps across all scans.

The Meta account has no hard spending cap (the $150 setting is an email alert), so the worker
enforces one. Every scan already logs each paid call to ``<data_dir>/<scan_id>/spend.jsonl``;
the budget totals those logs and, before a scan starts, reserves that scan's worst case (its
per-run limit). A scan is refused when the reservation would break the rolling 24-hour cap,
the all-time cap, or the concurrency limit. Running scans count at their full reservation,
so the caps hold even if every in-flight scan spends its whole allowance.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DAILY_USD = 5.0
DEFAULT_TOTAL_USD = 50.0
DEFAULT_MAX_CONCURRENT = 2
DAY_S = 24 * 3600


class BudgetExhausted(RuntimeError):
    """Raised when a new scan would break an account-wide cap."""


@dataclass
class Budget:
    data_dir: Path
    per_run_usd: float
    daily_usd: float = DEFAULT_DAILY_USD
    total_usd: float = DEFAULT_TOTAL_USD
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    _running: dict[str, float] = field(default_factory=dict)  # id -> reserved USD
    _scans: set[str] = field(default_factory=set)  # the ids that count toward concurrency
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def from_env(cls, data_dir: Path) -> Budget:
        env = os.environ.get
        return cls(
            data_dir=data_dir,
            per_run_usd=float(env("SPEND_LIMIT_USD_PER_RUN", "0.50")),
            daily_usd=float(env("SPEND_LIMIT_USD_PER_DAY", DEFAULT_DAILY_USD)),
            total_usd=float(env("SPEND_LIMIT_USD_TOTAL", DEFAULT_TOTAL_USD)),
            max_concurrent=int(env("MAX_CONCURRENT_SCANS", DEFAULT_MAX_CONCURRENT)),
        )

    def _spent(self, now: float) -> tuple[float, float]:
        """(last 24 h, all time) actual spend of scans that are not running."""
        day = total = 0.0
        for log in self.data_dir.glob("*/spend.jsonl"):
            if log.parent.name in self._running:
                continue
            for line in log.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                    cost, at = float(rec["cost_usd"]), float(rec["at"])
                except (ValueError, KeyError, TypeError):
                    continue
                if rec.get("partner") or str(rec.get("model", "")).startswith("meta-models/"):
                    continue  # billed to partner credits (Baseten), not the Meta account
                total += cost
                if now - at < DAY_S:
                    day += cost
        return day, total

    def status(self) -> dict[str, float | int]:
        with self._lock:
            day, total = self._spent(time.time())
            held = sum(self._running.values())
        return {
            "spent_24h_usd": round(day, 4),
            "spent_total_usd": round(total, 4),
            "reserved_usd": round(held, 4),
            "daily_limit_usd": self.daily_usd,
            "total_limit_usd": self.total_usd,
            "per_run_limit_usd": self.per_run_usd,
            "running": len(self._scans),
            "max_concurrent": self.max_concurrent,
            "scans_left_today": max(0, int((self.daily_usd - day - held) // self.per_run_usd)),
        }

    def reserve(self, scan_id: str, amount_usd: float | None = None, is_scan: bool = True) -> None:
        """Hold a run's worst-case cost (default: one scan), or raise BudgetExhausted."""
        amount = self.per_run_usd if amount_usd is None else amount_usd
        with self._lock:
            if is_scan and len(self._scans) >= self.max_concurrent:
                raise BudgetExhausted("Too many scans running right now; try again in a minute.")
            day, total = self._spent(time.time())
            held = sum(self._running.values()) + amount
            if day + held > self.daily_usd:
                raise BudgetExhausted(
                    f"Daily scan budget reached (${day:.2f} of ${self.daily_usd:.2f} in 24 h)."
                )
            if total + held > self.total_usd:
                raise BudgetExhausted(
                    f"Total scan budget reached (${total:.2f} of ${self.total_usd:.2f})."
                )
            self._running[scan_id] = amount
            if is_scan:
                self._scans.add(scan_id)

    def release(self, scan_id: str) -> None:
        with self._lock:
            self._running.pop(scan_id, None)
            self._scans.discard(scan_id)
