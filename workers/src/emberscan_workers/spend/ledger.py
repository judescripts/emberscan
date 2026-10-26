"""Per-run spend ledger: check an estimate before each model call, record actual usage after.

Spend is on a personal card once hackathon credits run out, and the account's $150
setting is an email alert, not a hard cap. So the hard cap lives here.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_LIMIT_USD = 0.50


class SpendLimitExceeded(RuntimeError):
    """Raised before a call that would push the run over its limit."""


@dataclass(frozen=True)
class UsageRecord:
    run_id: str
    stage: str
    model: str
    cost_usd: float
    units: dict[str, float]
    latency_s: float | None = None
    at: float = field(default_factory=time.time)


@dataclass
class SpendLedger:
    run_id: str
    limit_usd: float = DEFAULT_LIMIT_USD
    log_path: Path | None = None
    records: list[UsageRecord] = field(default_factory=list)

    @classmethod
    def from_env(cls, run_id: str, log_path: Path | None = None) -> SpendLedger:
        limit = float(os.environ.get("SPEND_LIMIT_USD_PER_RUN", DEFAULT_LIMIT_USD))
        return cls(run_id=run_id, limit_usd=limit, log_path=log_path)

    @property
    def spent_usd(self) -> float:
        return sum(r.cost_usd for r in self.records)

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.limit_usd - self.spent_usd)

    def check(self, stage: str, estimated_usd: float) -> None:
        """Call before a model request with a worst-case estimate."""
        if estimated_usd < 0:
            raise ValueError("estimate must be >= 0")
        if self.spent_usd + estimated_usd > self.limit_usd:
            raise SpendLimitExceeded(
                f"run {self.run_id}: {stage} would cost up to ${estimated_usd:.4f}; "
                f"spent ${self.spent_usd:.4f} of ${self.limit_usd:.2f} limit"
            )

    def record(
        self,
        stage: str,
        model: str,
        cost_usd: float,
        units: dict[str, float],
        latency_s: float | None = None,
    ) -> UsageRecord:
        """Call after a model request with the actual billed usage."""
        rec = UsageRecord(self.run_id, stage, model, cost_usd, units, latency_s)
        self.records.append(rec)
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(rec)) + "\n")
        return rec

    def summary(self) -> dict[str, object]:
        by_stage: dict[str, float] = {}
        by_model: dict[str, float] = {}
        for r in self.records:
            by_stage[r.stage] = by_stage.get(r.stage, 0.0) + r.cost_usd
            by_model[r.model] = by_model.get(r.model, 0.0) + r.cost_usd
        return {
            "run_id": self.run_id,
            "calls": len(self.records),
            "spent_usd": round(self.spent_usd, 6),
            "limit_usd": self.limit_usd,
            "by_stage": {k: round(v, 6) for k, v in by_stage.items()},
            "by_model": {k: round(v, 6) for k, v in by_model.items()},
        }
