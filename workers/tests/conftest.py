import pytest


@pytest.fixture(autouse=True)
def _no_partner_keys(monkeypatch):
    """Tests never reach Baseten: the open-weight path only runs when a test passes a client."""
    monkeypatch.delenv("BASETEN_API_KEY", raising=False)
