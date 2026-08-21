"""v1.41.1 regression for zero-fee/zero-day local-cash funding parity."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import types

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
package = types.ModuleType("portfolio_architect")
package.__path__ = [str(COMPONENT)]
sys.modules.setdefault("portfolio_architect", package)

from portfolio_architect.engine.execution import ExecutionConfig, choose_funded_route_for_cash

D = Decimal
ISIN = "IE0000001411"


def _broker() -> dict:
    return {
        "schema_version": 3,
        "fee_data_max_age_days": 30,
        "providers": {
            "comdirect": {
                "name": "Synthetic Source Broker",
                "source": "Synthetic tariff evidence",
                "as_of": "2026-08-21",
                "priority": 20,
                "savings_plans": {ISIN: {"available": True, "fee_pct": 1.5}},
            },
            "trade_republic": {
                "name": "Synthetic Destination Broker",
                "source": "Synthetic tariff evidence",
                "as_of": "2026-08-21",
                "priority": 10,
                "savings_plans": {ISIN: {"available": True, "fee_pct": 0}},
            },
        },
        "funding_transfers": [
            {
                "from_provider": "comdirect",
                "to_provider": "trade_republic",
                "fee_eur": 0,
                "settlement_business_days": 0,
                "source": "Synthetic zero-fee same-business-day transfer evidence",
                "as_of": "2026-08-21",
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


def test_local_cash_wins_zero_fee_zero_day_funding_tie() -> None:
    """Do not invent a transfer when the execution provider already has enough cash."""

    route = choose_funded_route_for_cash(
        isin=ISIN,
        desired_amount_eur=D("350"),
        periodic_cash_budget_eur=D("350"),
        minimum_order_eur=D("20"),
        rounding_step_eur=D("10"),
        broker=_broker(),
        config=_config(),
        funding_cash_by_provider={
            "comdirect": D("2574.97"),
            "trade_republic": D("3009.68"),
        },
        funding_provider_names={
            "comdirect": "Synthetic Source Broker",
            "trade_republic": "Synthetic Destination Broker",
        },
        evaluated_on=date(2026, 8, 21),
    )

    assert route.provider_id == "trade_republic"
    assert route.order_amount_eur == D("350")
    assert route.funding_provider_id == "trade_republic"
    assert route.funding_transfer_required is False
    assert route.funding_transfer_fee_eur == D("0")
    assert route.funding_transfer_business_days == 0
    assert route.cash_outlay_eur == D("350")
    assert route.cost_ratio_pct == D("0.0000")
