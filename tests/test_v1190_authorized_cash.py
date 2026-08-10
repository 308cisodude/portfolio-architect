"""v1.19.0 provider-owned authorized investment cash contracts."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.calculator import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.importers import CsvSourceConfig, PROVIDER_COMDIRECT, read_positions  # noqa: E402
from engine.rest import PROVIDER_LOCAL_REST_JSON  # noqa: E402
from model import parse_portfolio_data  # noqa: E402


def _payload(*, authorized: str, eligible: str, policy: str, cap: str | None) -> dict:
    positions = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv",
        CsvSourceConfig(provider=PROVIDER_COMDIRECT),
    )
    return calculate_portfolio_payload_from_positions(
        positions,
        ROOT / "examples" / "current-plan",
        evaluated_at=datetime(2026, 8, 10, 21, 0, tzinfo=timezone.utc),
        plan_override={
            "enabled": False,
            "execution": {
                "enabled": True,
                "policy": "balanced",
                "max_cost_ratio_pct": 1.5,
                "max_deferral_periods": 3,
                "max_orders_per_execution": 1,
                "reserve_mode": "gateway_balance",
            },
        },
        source_provider=PROVIDER_LOCAL_REST_JSON,
        source_label="Comdirect REST",
        source_metadata={
            "investment_reserve_eur": Decimal(authorized),
            "investment_reserve_as_of": "2026-08-10T20:59:00+00:00",
            "investment_account_balance_eur": Decimal(eligible),
            "eligible_investment_cash_eur": Decimal(eligible),
            "authorized_investment_cash_eur": Decimal(authorized),
            "investment_cash_authorization_policy": policy,
            "investment_cash_authorization_cap_eur": Decimal(cap) if cap is not None else None,
        },
    )


def test_capped_gateway_cash_controls_allocation_not_raw_balance() -> None:
    payload = _payload(
        authorized="100",
        eligible="8601.53",
        policy="capped",
        cap="100",
    )
    summary = payload["summary"]
    assert summary["available_investment_reserve_eur"] == Decimal("100")
    assert summary["investment_account_balance_eur"] == Decimal("8601.53")
    assert summary["eligible_investment_cash_eur"] == Decimal("8601.53")
    assert summary["authorized_investment_cash_eur"] == Decimal("100")
    assert summary["investment_cash_authorization_policy"] == "capped"
    assert summary["investment_cash_authorization_cap_eur"] == Decimal("100")
    assert summary["estimated_cash_outlay_eur"] <= Decimal("100")

    parsed = parse_portfolio_data(
        payload["recommendations"],
        payload["summary"],
        payload["policy_findings"],
        payload["holdings"],
    )
    plan = parsed.monthly_plan
    assert plan.available_reserve_eur == 100.0
    assert plan.investment_account_balance_eur == 8601.53
    assert plan.eligible_investment_cash_eur == 8601.53
    assert plan.authorized_investment_cash_eur == 100.0
    assert plan.investment_cash_authorization_policy == "capped"
    assert plan.investment_cash_authorization_cap_eur == 100.0


def test_all_available_gateway_cash_preserves_existing_comdirect_behavior() -> None:
    payload = _payload(
        authorized="8601.53",
        eligible="8601.53",
        policy="all_available",
        cap=None,
    )
    summary = payload["summary"]
    assert summary["available_investment_reserve_eur"] == Decimal("8601.53")
    assert summary["authorized_investment_cash_eur"] == Decimal("8601.53")
    assert summary["investment_cash_authorization_cap_eur"] is None
    assert summary["investment_cash_authorization_policy"] == "all_available"
