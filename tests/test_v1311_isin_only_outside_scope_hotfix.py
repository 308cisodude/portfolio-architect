"""v1.31.1 ISIN-only outside-scope holding live-recovery contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.aggregation import PortfolioSourceSnapshot, aggregate_sources  # noqa: E402
from engine.calculator import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.importers import CsvSourceConfig, PROVIDER_COMDIRECT, read_positions  # noqa: E402
from engine.models import Position  # noqa: E402

MODEL_PATH = COMPONENT / "model.py"
SPEC = importlib.util.spec_from_file_location("v1311_model", MODEL_PATH)
assert SPEC and SPEC.loader
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)

CONFIG = ROOT / "examples" / "current-plan"
OLD_ROBOTICS_ISIN = "IE00BYWZ0333"
NOW = datetime(2026, 8, 17, 17, 0, tzinfo=timezone.utc)
D = Decimal


def _live_failure_payload() -> dict:
    """Reproduce the v1.31.0 live topology that exposed the parser mismatch."""
    comdirect = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv",
        CsvSourceConfig(provider=PROVIDER_COMDIRECT),
    )
    # The live distributing Robotics purchase exists only in Trade Republic.
    # Remove the historical synthetic Comdirect copy from this fixture so no WKN
    # evidence exists for the ISIN during aggregation.
    comdirect = {key: value for key, value in comdirect.items() if value.isin != OLD_ROBOTICS_ISIN}
    trade_republic = {
        OLD_ROBOTICS_ISIN: Position(
            wkn="",
            isin=OLD_ROBOTICS_ISIN,
            name="iShares Automation & Robotics UCITS ETF USD Dist",
            instrument_type="etf",
            source_type="ETF",
            value_eur=D("500.00"),
            quantity=D("1"),
        )
    }
    aggregate = aggregate_sources(
        (
            PortfolioSourceSnapshot("comdirect", "comdirect", "Comdirect", NOW, comdirect),
            PortfolioSourceSnapshot(
                "trade_republic",
                "trade_republic",
                "Trade Republic",
                NOW,
                trade_republic,
            ),
        )
    )
    return calculate_portfolio_payload_from_positions(
        aggregate.positions,
        CONFIG,
        evaluated_at=NOW,
        source_provider="multi_source",
        source_label="2 sources",
    )


def test_live_isin_only_trade_republic_outside_scope_holding_parses_end_to_end() -> None:
    payload = _live_failure_payload()

    old = next(item for item in payload["holdings"] if item["isin"] == OLD_ROBOTICS_ISIN)
    assert old["position_id"] == "holding_ie00bywz0333"
    assert old["strategy_scope"] == "outside_scope"
    assert old["wkn"] == ""
    assert old["source_ids"] == ["trade_republic"]

    data = MODEL.parse_portfolio_data(
        payload["recommendations"],
        payload["summary"],
        payload["policy_findings"],
        holdings=payload["holdings"],
    )
    parsed = data.holdings["holding_ie00bywz0333"]
    assert parsed.wkn == ""
    assert parsed.isin == OLD_ROBOTICS_ISIN
    assert parsed.strategy_scope == "outside_scope"
    assert data.coverage.held == 6
    assert data.coverage.total == 7



def test_multiple_isin_only_holdings_do_not_collide_on_empty_wkn() -> None:
    recommendations = [{
        "fund_id": "world", "wkn": "A1XB5U", "isin": "IE00BJ0KDQ92", "name": "World",
        "target_pct": 100, "current_value_eur": 0, "target_value_eur": 200,
        "deviation_eur": 200, "current_pct": 0, "whole_portfolio_pct": 0,
        "deviation_pp": -100, "allocation_status": "underweight", "buy_enabled": True,
        "proposed_buy_eur": 0,
    }]
    positions = MODEL.parse_recommendations(recommendations)
    holdings = [
        {
            "position_id": "holding_ie00bywz0333", "wkn": "", "isin": OLD_ROBOTICS_ISIN,
            "name": "Robotics Dist", "instrument_type": "etf", "source_type": "ETF",
            "current_value_eur": 100, "whole_portfolio_pct": 50,
            "strategy_scope": "outside_scope", "plan_fund_id": None, "plan_current_pct": None,
        },
        {
            "position_id": "holding_ie00test0001", "wkn": "", "isin": "IE00TEST0001",
            "name": "Other ISIN-only holding", "instrument_type": "etf", "source_type": "ETF",
            "current_value_eur": 100, "whole_portfolio_pct": 50,
            "strategy_scope": "outside_scope", "plan_fund_id": None, "plan_current_pct": None,
        },
    ]
    parsed = MODEL.parse_holdings(holdings, positions)
    assert set(parsed) == {"holding_ie00bywz0333", "holding_ie00test0001"}
    assert all(item.wkn == "" for item in parsed.values())

def test_holdings_require_at_least_one_instrument_identity() -> None:
    recommendations = [{
        "fund_id": "world", "wkn": "A1XB5U", "isin": "IE00BJ0KDQ92", "name": "World",
        "target_pct": 100, "current_value_eur": 100, "target_value_eur": 100,
        "deviation_eur": 0, "current_pct": 100, "whole_portfolio_pct": 100,
        "deviation_pp": 0, "allocation_status": "on_target", "buy_enabled": True,
        "proposed_buy_eur": 0,
    }]
    positions = MODEL.parse_recommendations(recommendations)
    holdings = [{
        "position_id": "holding_unknown", "wkn": "", "isin": "", "name": "Unknown",
        "instrument_type": "other", "source_type": "Other", "current_value_eur": 100,
        "whole_portfolio_pct": 100, "strategy_scope": "outside_scope",
        "plan_fund_id": None, "plan_current_pct": None,
    }]
    with pytest.raises(MODEL.PortfolioArchitectDataError, match="ISIN or WKN identity"):
        MODEL.parse_holdings(holdings, positions)
