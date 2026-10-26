import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from emberscan_workers.rules import RulePack, load_pack

TAXONOMY = Path(__file__).resolve().parents[2] / "docs" / "hazard-taxonomy.md"


@pytest.fixture(scope="module")
def pack() -> RulePack:
    return load_pack("us-ca")


def test_california_pack_loads(pack: RulePack) -> None:
    assert pack.pack_id == "us-ca"
    assert len(pack.rules) > 0


def test_every_rule_zone_is_defined(pack: RulePack) -> None:
    zone_ids = {z.id for z in pack.zones}
    missing = {r.id: r.zone for r in pack.rules if r.zone not in zone_ids}
    assert not missing, f"rules reference undefined zones: {missing}"


def test_proposed_zone0_rules_have_no_effective_date(pack: RulePack) -> None:
    # Zone 0 is not in force yet; a proposed rule must never look enforceable.
    for r in pack.rules:
        if r.status == "proposed":
            assert r.effective_date is None, r.id


def test_hazard_classes_are_in_the_taxonomy(pack: RulePack) -> None:
    documented = set(re.findall(r"^\| `([a-z_]+)` \|", TAXONOMY.read_text(encoding="utf-8"), re.M))
    undocumented = pack.hazard_classes - documented
    assert not undocumented, f"classes missing from hazard-taxonomy.md: {sorted(undocumented)}"


def test_rule_lookup(pack: RulePack) -> None:
    first = pack.rules[0]
    assert pack.rule(first.id) is first
    with pytest.raises(KeyError):
        pack.rule("NOPE-99")


def test_duplicate_ids_are_rejected(pack: RulePack) -> None:
    data = pack.model_dump(mode="json")
    data["rules"].append(data["rules"][0])
    with pytest.raises(ValidationError, match="duplicate rule ids"):
        RulePack.model_validate(data)


def test_citations_must_be_https(pack: RulePack) -> None:
    data = pack.model_dump(mode="json")
    data["rules"][0]["citation_url"] = "http://example.com/rule"
    with pytest.raises(ValidationError, match="https"):
        RulePack.model_validate(data)
