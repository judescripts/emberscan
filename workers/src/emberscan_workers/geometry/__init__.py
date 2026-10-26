"""Ground-plane geometry: scale marker detection, SAM mask decoding, hazard distance, zones.

See docs/how-measurement-works.md and docs/adr/0003-distance-estimation.md.
"""

from .marker import (
    MARKER_COLS,
    MARKER_ROWS,
    PATTERN_SIZE,
    SQUARE_IN,
    MarkerPose,
    detect_marker,
    estimate_focal_px,
    marker_object_points,
    with_focal,
)
from .measure import (
    ContactMode,
    DistanceMeasurement,
    FrameMeasurement,
    aggregate,
    contact_mode_for,
    measure_frame,
    measure_track,
)
from .rle import RleError, decode_rle, mask_to_frame
from .zones import ZoneBand, assign_zone, load_zone_bands, zone_bands

__all__ = [
    "MARKER_COLS",
    "MARKER_ROWS",
    "PATTERN_SIZE",
    "SQUARE_IN",
    "ContactMode",
    "DistanceMeasurement",
    "FrameMeasurement",
    "MarkerPose",
    "RleError",
    "ZoneBand",
    "aggregate",
    "assign_zone",
    "contact_mode_for",
    "decode_rle",
    "detect_marker",
    "estimate_focal_px",
    "load_zone_bands",
    "mask_to_frame",
    "marker_object_points",
    "measure_frame",
    "measure_track",
    "with_focal",
    "zone_bands",
]
