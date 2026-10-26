import json

import pytest

from emberscan_workers.spend import (
    SpendLedger,
    SpendLimitExceeded,
    image_cost,
    sam_video_cost,
    token_cost,
    voice_cost,
)


def test_token_cost_matches_first_live_call() -> None:
    # Oct 26 smoke test: 13 input, 16 output (14 of them reasoning) on the contributor model.
    assert token_cost("muse-spark-1.3-contributor", 13, 16) == pytest.approx(
        (13 * 0.10 + 16 * 0.20) / 1e6
    )


def test_cached_tokens_are_cheaper() -> None:
    full = token_cost("muse-spark-1.3", 1_000_000, 0)
    half_cached = token_cost("muse-spark-1.3", 1_000_000, 0, cached_tokens=500_000)
    assert full == pytest.approx(1.25)
    assert half_cached == pytest.approx(0.5 * 1.25 + 0.5 * 0.15)


def test_unknown_model_has_no_silent_price() -> None:
    with pytest.raises(KeyError, match="no price"):
        token_cost("some-new-model", 10, 10)


def test_invalid_token_counts() -> None:
    with pytest.raises(ValueError):
        token_cost("muse-spark-1.3", 10, 10, cached_tokens=11)


def test_sam_minimum_50_frames_per_request() -> None:
    assert sam_video_cost(10) == pytest.approx(50 * 0.20 / 1000)
    assert sam_video_cost(3600, requests=12) == pytest.approx(3600 * 12 * 0.20 / 1000)
    assert sam_video_cost(3600, requests=0) == 0


def test_voice_rounds_down_to_whole_seconds() -> None:
    assert voice_cost(59.9) == pytest.approx(59 * 0.18 / 3600)


def test_image_cost() -> None:
    assert image_cost(3) == pytest.approx(0.03)


def test_ledger_blocks_before_overspend(tmp_path) -> None:
    log = tmp_path / "spend.jsonl"
    ledger = SpendLedger(run_id="r1", limit_usd=0.10, log_path=log)
    ledger.check("segment", 0.06)
    ledger.record("segment", "sam-3.1", 0.06, {"frames": 300})
    with pytest.raises(SpendLimitExceeded, match="r1"):
        ledger.check("segment", 0.05)
    ledger.check("agent", 0.04)  # exactly reaches the limit: allowed
    assert ledger.remaining_usd == pytest.approx(0.04)
    lines = [json.loads(x) for x in log.read_text().splitlines()]
    assert lines[0]["model"] == "sam-3.1" and lines[0]["units"] == {"frames": 300}


def test_ledger_summary_groups_by_stage_and_model() -> None:
    ledger = SpendLedger(run_id="r2", limit_usd=1.0)
    ledger.record("segment", "sam-3.1", 0.02, {"frames": 100})
    ledger.record("segment", "sam-3.1", 0.03, {"frames": 150})
    ledger.record("agent", "muse-spark-1.3", 0.01, {"input_tokens": 1000})
    s = ledger.summary()
    assert s["calls"] == 3
    assert s["by_stage"] == {"segment": 0.05, "agent": 0.01}
    assert s["by_model"] == {"sam-3.1": 0.05, "muse-spark-1.3": 0.01}


def test_limit_from_env(monkeypatch) -> None:
    monkeypatch.setenv("SPEND_LIMIT_USD_PER_RUN", "0.25")
    assert SpendLedger.from_env("r3").limit_usd == 0.25
