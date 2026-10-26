"""Hazard sides from tagged clips and from narration."""

from emberscan_workers.contracts import Hazard
from emberscan_workers.meta.voice import Transcript, Turn
from emberscan_workers.pipeline import assign_sides, narration_sides


def _h(hid: str, frames: list[int]) -> Hazard:
    return Hazard(
        id=hid,
        cls="shrub",
        concept="shrub",
        track_id="0",
        label="Shrub",
        frames=frames,
        confidence="high",
    )


CLIPS = [
    {"name": "a", "start_s": 0.0, "duration_s": 10.0},
    {"name": "b", "start_s": 10.0, "duration_s": 10.0},
]


def test_side_from_the_clip_it_was_mostly_seen_in() -> None:
    hs = [_h("h1", [3, 6, 9]), _h("h2", [27, 30, 33, 36]), _h("h3", [28, 31, 34])]
    # 3 fps: h1 is in clip a (0-10 s); h2 straddles the cut but mostly in b
    n = assign_sides(hs, 3.0, CLIPS, ["N", "E"], [])
    assert n == 3 and [h.side for h in hs] == ["N", "E", "E"]


def test_untagged_clips_fall_back_to_narration() -> None:
    tr = Transcript(
        text="",
        duration_ms=20000,
        turns=[
            Turn(start_ms=0, end_ms=2000, text="Starting on the north side by the door"),
            Turn(start_ms=11000, end_ms=13000, text="Now the West wall, ivy here"),
        ],
    )
    spoken = narration_sides(tr)
    assert spoken == [(0, "N"), (11000, "W")]
    hs = [_h("h1", [6]), _h("h2", [36])]
    assign_sides(hs, 3.0, CLIPS, ["", ""], spoken)
    assert [h.side for h in hs] == ["N", "W"]


def test_nothing_known_leaves_sides_unknown() -> None:
    hs = [_h("h1", [6])]
    assert assign_sides(hs, 3.0, [], [], []) == 0 and hs[0].side == "unknown"
    # one untagged-but-named single clip
    assert assign_sides(hs, 3.0, [], ["S"], []) == 1 and hs[0].side == "S"
