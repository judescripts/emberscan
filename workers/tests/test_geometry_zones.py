"""Zone assignment from distance ranges, with bands read from the real rule pack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from emberscan_workers.contracts import Range
from emberscan_workers.geometry import ZoneBand, assign_zone, load_zone_bands, zone_bands

PACK = Path(__file__).resolve().parents[2] / "docs" / "rules" / "us-ca.json"


@pytest.fixture(scope="module")
def bands() -> list[ZoneBand]:
    return load_zone_bands(PACK)


def test_bands_from_pack_are_exclusive(bands: list[ZoneBand]) -> None:
    assert [(b.id, b.min_ft, b.max_ft) for b in bands] == [
        ("Z0", 0, 5),
        ("Z1", 5, 30),
        ("Z2", 30, 100),
    ]


@pytest.mark.parametrize(
    ("lo", "hi", "zone", "uncertain"),
    [
        (0.0, 0.0, "Z0", False),
        (2.5, 3.5, "Z0", False),
        (4.0, 4.9, "Z0", False),
        (4.0, 6.0, "Z0", True),  # straddles 5 ft: nearer zone, uncertain
        (4.5, 5.0, "Z0", True),  # touches the boundary: 5.0 belongs to Z1
        (5.0, 7.0, "Z1", False),
        (12.0, 29.9, "Z1", False),
        (28.0, 32.0, "Z1", True),
        (3.0, 40.0, "Z0", True),  # spans two boundaries
        (30.0, 100.0, "Z2", False),  # outer edge is inclusive
        (90.0, 120.0, "Z2", True),  # runs past the defensible space
        (101.0, 140.0, None, False),
    ],
)
def test_assign_zone(bands, lo: float, hi: float, zone: str | None, uncertain: bool) -> None:
    assert assign_zone(Range(min=lo, max=hi), bands) == (zone, uncertain)


def test_accepts_raw_pack_zones_and_bad_ranges() -> None:
    zones = json.loads(PACK.read_text(encoding="utf-8"))["zones"]
    assert assign_zone(Range(min=4.0, max=6.0), zones) == ("Z0", True)
    assert assign_zone(Range(min=6.0, max=4.0), zones) == ("Z0", True)  # swapped
    assert assign_zone(Range(min=-1.0, max=2.0), zones) == ("Z0", False)  # clamped at 0


def test_missing_zone_is_an_error() -> None:
    with pytest.raises(ValueError):
        zone_bands([{"id": "Z0", "min_ft": 0, "max_ft": 5}])
