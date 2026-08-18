"""v1.35.0 provider-scoped cash and explicit funding-topology contracts."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import shutil
import sys

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.calculator import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.execution import ExecutionConfig, choose_funded_route_for_cash  # noqa: E402
from engine.funding import funding_transfers, transfer_for  # noqa: E402
from engine.importers import CsvSourceConfig, PROVIDER_COMDIRECT, read_positions  # noqa: E402
from model import parse_portfolio_data  # noqa: E402

D = Decimal
ROBOTICS_ISIN = "IE00BYZK4552"


def _broker(*, transfer_fee: str = "1.50", transfer_days: int = 2) -> dict:
    return {
        "schema_version": 3,
        "fee_data_max_age_days": 30,
        "providers": {
            "comdirect": {
                "name": "Comdirect",
                "source": "synthetic-v1350-regression",
                "as_of": "2026-08-18",
                "priority": 20,
                "savings_plans": {
                    ROBOTICS_ISIN: {"available": True, "fee_pct": 1.5},
                },
            },
            "trade_republic": {
                "name": "Trade Republic",
                "source": "synthetic-v1350-regression",
                "as_of": "2026-08-18",
                "priority": 10,
                "savings_plans": {
                    ROBOTICS_ISIN: {"available": True, "fee_pct": 0},
                },
            },
        },
        "funding_transfers": [
            {
                "from_provider": "comdirect",
                "to_provider": "trade_republic",
                "fee_eur": transfer_fee,
                "settlement_business_days": transfer_days,
            }
        ],
    }


def _config() -> ExecutionConfig:
    return ExecutionConfig(
        enabled=True,
        policy="efficiency_first",
        max_cost_ratio_pct=D("5"),
        max_orders_per_execution=1,
        reserve_mode="gateway_balance",
    )


def _funded_route(broker: dict, cash: dict[str, Decimal]) -> object:
    return choose_funded_route_for_cash(
        isin=ROBOTICS_ISIN,
        desired_amount_eur=D("350"),
        periodic_cash_budget_eur=D("350"),
        minimum_order_eur=D("20"),
        rounding_step_eur=D("10"),
        broker=broker,
        config=_config(),
        funding_cash_by_provider=cash,
        funding_provider_names={
            "comdirect": "Comdirect",
            "trade_republic": "Trade Republic",
        },
        evaluated_on=date(2026, 8, 18),
    )


def test_schema3_transfer_is_explicit_directed_and_bounded() -> None:
    broker = _broker()
    transfers = funding_transfers(broker)
    assert len(transfers) == 1
    transfer = transfers[0]
    assert transfer.from_provider == "comdirect"
    assert transfer.to_provider == "trade_republic"
    assert transfer.fee_eur == D("1.50")
    assert transfer.settlement_business_days == 2
    assert transfer_for(
        broker, from_provider="comdirect", to_provider="trade_republic"
    ) == transfer
    assert transfer_for(
        broker, from_provider="trade_republic", to_provider="comdirect"
    ) is None

    broken = _broker()
    broken["funding_transfers"][0]["to_provider"] = "unknown"
    with pytest.raises(ValueError, match="unknown provider"):
        funding_transfers(broken)

    broken = _broker()
    broken["funding_transfers"][0]["to_provider"] = "comdirect"
    with pytest.raises(ValueError, match="same-provider"):
        funding_transfers(broken)


def test_cross_provider_cash_is_unusable_without_exact_directed_edge() -> None:
    broker = _broker()
    broker["funding_transfers"] = []
    route = _funded_route(broker, {"comdirect": D("350")})
    assert route.provider_id == "comdirect"
    assert route.funding_provider_id == "comdirect"
    assert route.funding_transfer_required is False

    reverse_only = _broker()
    reverse_only["funding_transfers"] = [
        {
            "from_provider": "trade_republic",
            "to_provider": "comdirect",
            "fee_eur": 0,
            "settlement_business_days": 1,
        }
    ]
    route = _funded_route(reverse_only, {"comdirect": D("350")})
    assert route.provider_id == "comdirect"
    assert route.funding_provider_id == "comdirect"


def test_transfer_fee_participates_in_route_economics() -> None:
    cheap = _funded_route(_broker(transfer_fee="1.50"), {"comdirect": D("350")})
    assert cheap.provider_id == "trade_republic"
    assert cheap.funding_provider_id == "comdirect"
    assert cheap.funding_transfer_required is True
    assert cheap.funding_transfer_fee_eur == D("1.50")
    assert cheap.funding_transfer_business_days == 2
    assert cheap.order_amount_eur == D("348.50")
    assert cheap.cash_outlay_eur == D("350.00")
    assert cheap.cost_ratio_pct == D("0.4304")

    expensive = _funded_route(_broker(transfer_fee="10"), {"comdirect": D("350")})
    assert expensive.provider_id == "comdirect"
    assert expensive.funding_provider_id == "comdirect"
    assert expensive.funding_transfer_required is False
    assert expensive.cost_ratio_pct >= D("1.49")
    assert expensive.cost_ratio_pct > cheap.cost_ratio_pct


def test_local_cash_beats_equally_cheap_transfer_by_delay() -> None:
    route = _funded_route(
        _broker(transfer_fee="0", transfer_days=2),
        {"comdirect": D("350"), "trade_republic": D("350")},
    )
    assert route.provider_id == "trade_republic"
    assert route.funding_provider_id == "trade_republic"
    assert route.funding_transfer_required is False
    assert route.funding_transfer_business_days == 0



def test_invalid_unused_schema3_edge_still_fails_closed() -> None:
    broker = _broker()
    broker["funding_transfers"][0]["to_provider"] = "unknown"
    with pytest.raises(ValueError, match="unknown provider"):
        _funded_route(broker, {"trade_republic": D("350")})


def test_contribution_only_does_not_consume_gateway_cash(tmp_path: Path) -> None:
    config_dir = tmp_path / "plan"
    shutil.copytree(ROOT / "examples" / "current-plan", config_dir)
    portfolio = yaml.safe_load((config_dir / "portfolio.yaml").read_text(encoding="utf-8"))
    robotics = next(
        item for item in portfolio["portfolio"]["allocation"] if item["isin"] == ROBOTICS_ISIN
    )
    robotics["target_pct"] = 100
    portfolio["portfolio"]["allocation"] = [robotics]
    (config_dir / "portfolio.yaml").write_text(
        yaml.safe_dump(portfolio, sort_keys=False), encoding="utf-8"
    )
    (config_dir / "broker.yaml").write_text(
        yaml.safe_dump(_broker(), sort_keys=False), encoding="utf-8"
    )
    positions = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv",
        CsvSourceConfig(provider=PROVIDER_COMDIRECT),
    )
    payload = calculate_portfolio_payload_from_positions(
        positions,
        config_dir,
        evaluated_at=datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc),
        plan_override={
            "enabled": False,
            "execution": {
                "enabled": True,
                "policy": "efficiency_first",
                "max_cost_ratio_pct": 5,
                "max_deferral_periods": 3,
                "max_orders_per_execution": 1,
                "reserve_mode": "contribution_only",
            },
        },
        source_provider="multi_source",
        source_label="synthetic contribution-only regression",
        source_metadata={
            "provider_investment_cash": [
                {
                    "provider_id": "comdirect",
                    "provider_name": "Comdirect",
                    "available_eur": D("1"),
                    "as_of": "2026-08-18T19:59:00+00:00",
                }
            ]
        },
    )
    recommendation = payload["recommendations"][0]
    assert recommendation["proposed_buy_eur"] > D("1")
    assert recommendation["funding_provider"] is None
    assert recommendation["funding_transfer_required"] is False
    summary = payload["summary"]
    assert summary["investment_reserve_source"] == "contribution"
    assert summary["provider_investment_cash"][0]["remaining_eur"] == D("1.00")
    assert summary["funding_transfers"] == []
    parse_portfolio_data(
        payload["recommendations"], summary, payload["policy_findings"], payload["holdings"]
    )

def test_full_payload_exposes_provider_cash_and_advisory_transfer(tmp_path: Path) -> None:
    config_dir = tmp_path / "plan"
    shutil.copytree(ROOT / "examples" / "current-plan", config_dir)

    portfolio = yaml.safe_load((config_dir / "portfolio.yaml").read_text(encoding="utf-8"))
    robotics = next(
        item
        for item in portfolio["portfolio"]["allocation"]
        if item["isin"] == ROBOTICS_ISIN
    )
    robotics["target_pct"] = 100
    portfolio["portfolio"]["allocation"] = [robotics]
    (config_dir / "portfolio.yaml").write_text(
        yaml.safe_dump(portfolio, sort_keys=False), encoding="utf-8"
    )
    (config_dir / "broker.yaml").write_text(
        yaml.safe_dump(_broker(), sort_keys=False), encoding="utf-8"
    )

    positions = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv",
        CsvSourceConfig(provider=PROVIDER_COMDIRECT),
    )
    payload = calculate_portfolio_payload_from_positions(
        positions,
        config_dir,
        evaluated_at=datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc),
        plan_override={
            "enabled": False,
            "execution": {
                "enabled": True,
                "policy": "efficiency_first",
                "max_cost_ratio_pct": 5,
                "max_deferral_periods": 3,
                "max_orders_per_execution": 1,
                "reserve_mode": "gateway_balance",
            },
        },
        source_provider="multi_source",
        source_label="synthetic multi-source regression",
        source_metadata={
            "provider_investment_cash": [
                {
                    "provider_id": "comdirect",
                    "provider_name": "Comdirect",
                    "available_eur": D("350"),
                    "as_of": "2026-08-18T19:59:00+00:00",
                }
            ],
        },
    )

    recommendation = payload["recommendations"][0]
    assert recommendation["execution_provider"] == "trade_republic"
    assert recommendation["funding_provider"] == "comdirect"
    assert recommendation["funding_transfer_required"] is True
    assert recommendation["funding_transfer_fee_eur"] == D("1.50")
    assert recommendation["funding_transfer_business_days"] == 2

    summary = payload["summary"]
    assert summary["provider_investment_cash_source_count"] == 1
    assert summary["provider_investment_cash"][0]["available_eur"] == D("350.00")
    assert summary["provider_investment_cash"][0]["remaining_eur"] == D("0")
    assert summary["funding_transfer_count"] == 1
    assert summary["estimated_funding_transfer_fees_eur"] == D("1.50")
    assert summary["funding_transfers"] == [
        {
            "from_provider": "comdirect",
            "from_provider_name": "Comdirect",
            "to_provider": "trade_republic",
            "to_provider_name": "Trade Republic",
            "amount_eur": D("348.50"),
            "fee_eur": D("1.50"),
            "settlement_business_days": 2,
        }
    ]

    parsed = parse_portfolio_data(
        payload["recommendations"],
        summary,
        payload["policy_findings"],
        payload["holdings"],
    )
    assert parsed.monthly_plan.provider_investment_cash[0].remaining_eur == 0.0
    assert parsed.monthly_plan.funding_transfers[0].from_provider == "comdirect"
    assert parsed.monthly_plan.funding_transfers[0].to_provider == "trade_republic"
    assert parsed.monthly_plan.funding_transfers[0].amount_eur == 348.5
