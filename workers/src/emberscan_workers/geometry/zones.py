"""Assign a measured distance range to a defensible-space zone (C3).

Zone bands come from the rule pack (docs/rules/us-ca.json ``zones``), never hard-coded. The
pack lists overlapping bands for legal reasons (Z1 is 0-30 ft today and becomes 5-30 ft once
Zone 0 takes effect), so we build *exclusive* bands: zones are ordered by their outer edge and
each starts where the previous one ends, giving Z0 0-5, Z1 5-30, Z2 30-100 ft.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..contracts import Range

DISTANCE_ZONE_IDS: tuple[str, ...] = ("Z0", "Z1", "Z2")  # pack zones that are distance bands


@dataclass(frozen=True)
class ZoneBand:
    """An exclusive distance band [min_ft, max_ft) from the wall; the last band is closed."""

    id: str
    min_ft: float
    max_ft: float


def zone_bands(
    zones: Iterable[Mapping[str, Any]], ids: Sequence[str] = DISTANCE_ZONE_IDS
) -> list[ZoneBand]:
    """Build exclusive, ordered distance bands from a pack's ``zones`` list."""
    picked = [z for z in zones if z.get("id") in ids]
    missing = set(ids) - {z["id"] for z in picked}
    if missing:
        raise ValueError(f"rule pack is missing zones {sorted(missing)}")
    picked.sort(key=lambda z: (float(z["max_ft"]), float(z["min_ft"])))
    bands: list[ZoneBand] = []
    prev = 0.0
    for z in picked:
        lo = max(float(z["min_ft"]), prev)
        hi = float(z["max_ft"])
        if hi <= lo:
            raise ValueError(f"zone {z['id']} is empty after removing overlaps")
        bands.append(ZoneBand(str(z["id"]), lo, hi))
        prev = hi
    return bands


def load_zone_bands(pack_path: str | Path) -> list[ZoneBand]:
    """Read a rule pack JSON file and return its exclusive distance bands."""
    pack = json.loads(Path(pack_path).read_text(encoding="utf-8"))
    return zone_bands(pack["zones"])


def _zone_at(d: float, bands: Sequence[ZoneBand]) -> str | None:
    for i, b in enumerate(bands):
        last = i == len(bands) - 1
        if b.min_ft <= d < b.max_ft or (last and d == b.max_ft):
            return b.id
    return None


def assign_zone(
    distance: Range, zones: Sequence[ZoneBand] | Iterable[Mapping[str, Any]]
) -> tuple[str | None, bool]:
    """Zone for a measured distance range, and whether that assignment is uncertain.

    Args:
        distance: distance from the wall in feet (``Range``).
        zones: bands from ``zone_bands``/``load_zone_bands``, or the pack's raw ``zones`` list.

    Returns ``(zone_id, uncertain)``. When the range straddles a boundary the zone nearer the
    house (holding ``distance.min``) is returned with ``uncertain=True``, so the stricter
    rules are checked and the rules engine can mark them needs-review. A range wholly beyond
    the outermost band returns ``(None, False)``; one that starts inside and runs past it
    returns the inner zone, uncertain. Bands are half-open: exactly 5.0 ft is Zone 1.
    """
    seq = list(zones)
    bands = [z for z in seq if isinstance(z, ZoneBand)]
    if len(bands) != len(seq):
        bands = zone_bands(z for z in seq if not isinstance(z, ZoneBand))
    lo, hi = sorted((max(distance.min, 0.0), max(distance.max, 0.0)))
    near = _zone_at(lo, bands)
    far = _zone_at(hi, bands)
    if near is None:
        return None, False
    return near, far != near
