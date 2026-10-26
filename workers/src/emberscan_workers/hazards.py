"""Hazard classes and the SAM 3.1 text concepts used to find them (docs/hazard-taxonomy.md).

One SAM request per concept (SAM takes one concept per request). The scan runs these
concurrently. `CORE` is the default set for a scan; `EXTENDED` adds rarer classes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    cls: str
    prompt: str
    label: str  # how a finding of this class is described


# Structure classes: distances are measured from these, they're not hazards.
STRUCTURE = [
    Concept("wall", "exterior wall of a house", "Wall"),
    Concept("window", "window", "Window"),
    Concept("door", "door", "Door"),
]

CORE = [
    Concept("wood_mulch", "bark mulch", "Bark or wood mulch"),
    Concept("shrub", "shrub", "Shrub"),
    Concept("dead_vegetation", "dead brown plant", "Dead or dying plant"),
    Concept("woodpile", "stacked firewood", "Stacked firewood"),
    Concept("combustible_fence", "wooden fence", "Wooden fence"),
    Concept("leaf_litter", "dry leaves on the ground", "Dry leaves or needles"),
    Concept("grass_tall", "tall dry grass", "Tall dry grass"),
    Concept("tree_branch", "tree branch near the roof", "Tree branch near the roof"),
    Concept("combustible_furniture", "outdoor furniture cushion", "Patio cushions or furniture"),
    Concept("propane_tank", "propane tank", "Propane tank"),
    Concept("open_vent", "house vent", "Vent"),
    Concept("gutter_debris", "leaves in a rain gutter", "Debris in the gutter"),
]

EXTENDED = [
    Concept("tree", "tree trunk", "Tree"),
    Concept("potted_plant", "potted plant", "Potted plant"),
    Concept("outbuilding", "garden shed", "Shed"),
    Concept("vehicle_or_boat", "car", "Vehicle"),
    Concept("roof_debris", "leaves on a roof", "Debris on the roof"),
]

BY_CLASS = {c.cls: c for c in STRUCTURE + CORE + EXTENDED}
