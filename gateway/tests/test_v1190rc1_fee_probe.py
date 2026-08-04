from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path

from portfolio_architect_gateway.comdirect import ComdirectClient

from test_gateway_comdirect import FakeTransport, config


def test_instrument_probe_keeps_flags_opaque_and_venue_ids_private(tmp_path: Path) -> None:
    transport = FakeTransport()
    client = ComdirectClient(config(tmp_path), transport=transport, clock=lambda: 1000)
    client.bootstrap(prompt=lambda _message: "", output=lambda _message: None)
    result = client.probe_instrument("ie00bj0kdq92")
    assert result.fund_flags == ("FLAG_A", "FLAG_B")
    assert len(result.venues) == 1
    assert result.venues[0]["name"] == "Tradegate"
    public = result.public_dict()
    assert public["interpretation"] == "opaque_observation_only"
    assert "venue_id" not in json.dumps(public)
    assert "VENUE-PRIVATE-1" not in json.dumps(public)


def test_cost_probe_is_buy_market_only_and_redacts_private_identifiers(tmp_path: Path) -> None:
    transport = FakeTransport()
    client = ComdirectClient(config(tmp_path), transport=transport, clock=lambda: 1000)
    client.bootstrap(prompt=lambda _message: "", output=lambda _message: None)
    result = client.probe_cost_indication(
        depot_id="D1",
        isin="IE00BJ0KDQ92",
        venue_id="VENUE-PRIVATE-1",
        venue_name="Tradegate",
        quantity=Decimal("1"),
    ).public_dict()
    encoded = json.dumps(result)
    assert result["calculation_successful"] is True
    assert result["purchase_costs"]["costs"][0]["label"] == "Orderprovision"
    assert result["purchase_costs"]["sum"]["value"] == "9.9"
    assert result["total_costs_rel_pct"] == "24.57"
    assert "D1" not in encoded
    assert "VENUE-PRIVATE-1" not in encoded
    assert "linkCosts" not in encoded
    assert "inducement" not in encoded
    assert result["warning"].startswith("No order")
