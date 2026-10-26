from emberscan_workers.eave import parse_answer


def test_parses_range_and_caps_confidence() -> None:
    e = parse_answer(
        '{"visible": true, "min_ft": 2.0, "max_ft": 1.0, "confidence": "medium", '
        '"reason": "rafter tails"}'
    )
    assert e is not None and (e.depth_ft.min, e.depth_ft.max) == (1.0, 2.0)
    assert e.confidence == "medium" and e.method == "visual"


def test_wide_range_is_low_confidence_and_clamped() -> None:
    e = parse_answer('Sure: {"visible": true, "min_ft": 0, "max_ft": 9, "confidence": "medium"}')
    assert e is not None and e.confidence == "low"
    assert (e.depth_ft.min, e.depth_ft.max) == (0.25, 6.0)


def test_not_visible_or_garbage_is_none() -> None:
    assert parse_answer('{"visible": false, "min_ft": 0, "max_ft": 0}') is None
    assert parse_answer("no json here") is None
    assert parse_answer('{"visible": true, "min_ft": "a", "max_ft": 2}') is None
