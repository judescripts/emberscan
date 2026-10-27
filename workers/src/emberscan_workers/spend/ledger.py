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
DEFAULT_PARTNER_LIMIT_USD = 0.30


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
    partner: bool = False  # billed to partner credits (Baseten), not the Meta account


@dataclass
class SpendLedger:
    """Meta account spend counts toward `limit_usd`; partner-credit spend (Muse Spark Open on
    Baseten) has its own `partner_limit_usd`, so one never crowds out the other."""

    run_id: str
    limit_usd: float = DEFAULT_LIMIT_USD
    log_path: Path | None = None
    records: list[UsageRecord] = field(default_factory=list)
    partner_limit_usd: float = DEFAULT_PARTNER_LIMIT_USD

    @classmethod
    def from_env(cls, run_id: str, log_path: Path | None = None) -> SpendLedger:
        limit = float(os.environ.get("SPEND_LIMIT_USD_PER_RUN", DEFAULT_LIMIT_USD))
        partner = float(
            os.environ.get("SPEND_LIMIT_USD_PARTNER_PER_RUN", DEFAULT_PARTNER_LIMIT_USD)
        )
        return cls(run_id=run_id, limit_usd=limit, log_path=log_path, partner_limit_usd=partner)

    @property
    def spent_usd(self) -> float:
        return sum(r.cost_usd for r in self.records if not r.partner)

    @property
    def partner_usd(self) -> float:
        return sum(r.cost_usd for r in self.records if r.partner)

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.limit_usd - self.spent_usd)

    def check(self, stage: str, estimated_usd: float, partner: bool = False) -> None:
        """Call before a model request with a worst-case estimate."""
        if estimated_usd < 0:
            raise ValueError("estimate must be >= 0")
        spent, limit = (
            (self.partner_usd, self.partner_limit_usd)
            if partner
            else (self.spent_usd, self.limit_usd)
        )
        if spent + estimated_usd > limit:
            raise SpendLimitExceeded(
                f"run {self.run_id}: {stage} would cost up to ${estimated_usd:.4f}; "
                f"spent ${spent:.4f} of ${limit:.2f} {'partner ' if partner else ''}limit"
            )

    def record(
        self,
        stage: str,
        model: str,
        cost_usd: float,
        units: dict[str, float],
        latency_s: float | None = None,
        partner: bool = False,
    ) -> UsageRecord:
        """Call after a model request with the actual billed usage."""
        rec = UsageRecord(self.run_id, stage, model, cost_usd, units, latency_s, partner=partner)
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
            "partner_usd": round(self.partner_usd, 6),
            "by_stage": {k: round(v, 6) for k, v in by_stage.items()},
            "by_model": {k: round(v, 6) for k, v in by_model.items()},
        }
