"""Load and validate a defensible-space rule pack (e.g. docs/rules/us-ca.json).

Rules are data (ADR 0004): the engine never hard-codes thresholds, and every rule must carry
a citation so each result in a report can point to its source.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

REPO_ROOT = Path(__file__).resolve().parents[4]
RULES_DIR = REPO_ROOT / "docs" / "rules"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class AbsentWithin(_Strict):
    type: Literal["absent_within"]
    # A number of feet, or "eave" for the eave-depth strip (clamped to min_ft..max_ft).
    ft: float | Literal["eave"]


class MinClearance(_Strict):
    type: Literal["min_clearance"]
    ft: float


class MaxHeight(_Strict):
    type: Literal["max_height"]
    inches: float


class Present(_Strict):
    type: Literal["present"]


class ManualReview(_Strict):
    type: Literal["manual_review"]


Check = Annotated[
    AbsentWithin | MinClearance | MaxHeight | Present | ManualReview,
    Field(discriminator="type"),
]


class Zone(_Strict):
    id: str
    name: str
    min_ft: float | None = None
    max_ft: float | None = None


class Rule(_Strict):
    id: str
    zone: str
    title: str
    hazard_classes: list[str] = Field(min_length=1)
    check: Check
    plain_language: str = Field(min_length=1)
    status: Literal["adopted", "proposed", "guidance"]
    effective_date: str | None
    applies_to: Literal["new", "existing", "all"]
    citation_url: HttpUrl
    citation_label: str = Field(min_length=1)

    @field_validator("citation_url")
    @classmethod
    def _https_only(cls, url: HttpUrl) -> HttpUrl:
        if url.scheme != "https":
            raise ValueError("citation_url must use https")
        return url


class RulePack(_Strict):
    pack_id: str
    version: str
    checked_on: str
    zones: list[Zone]
    rules: list[Rule] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> RulePack:
        ids = [r.id for r in self.rules]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate rule ids: {dupes}")
        return self

    def rule(self, rule_id: str) -> Rule:
        for r in self.rules:
            if r.id == rule_id:
                return r
        raise KeyError(rule_id)

    @property
    def hazard_classes(self) -> set[str]:
        return {c for r in self.rules for c in r.hazard_classes}


def load_pack(pack_id: str = "us-ca", rules_dir: Path = RULES_DIR) -> RulePack:
    """Load a rule pack by id from the rules directory and validate it."""
    path = rules_dir / f"{pack_id}.json"
    with path.open(encoding="utf-8-sig") as f:
        return RulePack.model_validate(json.load(f))
