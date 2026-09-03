"""v1.18.1 execution-state and reserve terminology contracts."""

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))
sys.path.insert(0, str(ROOT / "tests"))

from reference_portfolio import (  # noqa: E402
    REFERENCE_LABEL,
    REFERENCE_PROVIDER,
    read_reference_positions,
)

from engine.calculator import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.rest import PROVIDER_LOCAL_REST_JSON  # noqa: E402
from model import parse_portfolio_data  # noqa: E402


def _payload(reserve: str) -> dict:
    positions = read_reference_positions()
    return calculate_portfolio_payload_from_positions(
        positions,
        ROOT / "examples" / "current-plan",
        evaluated_at=datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc),
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
            "investment_reserve_eur": Decimal(reserve),
            "investment_reserve_as_of": "2026-08-02T07:59:00+00:00",
        },
    )


def test_small_live_reserve_reports_waiting_state_and_required_cash() -> None:
    payload = _payload("1.46")
    summary = payload["summary"]
    assert summary["execution_state"] == "waiting_for_reserve"
    assert summary["purchase_count"] == 0
    assert summary["additional_investment_cash_required_eur"] > Decimal("0")
    parsed = parse_portfolio_data(payload["recommendations"], payload["summary"], payload["policy_findings"], payload["holdings"])
    assert parsed.monthly_plan.execution_state == "waiting_for_reserve"
    assert parsed.monthly_plan.additional_investment_cash_required_eur > 0


def test_execution_ux_contract_is_additive_for_old_v1162_payloads() -> None:
    payload = _payload("350")
    payload["summary"].pop("execution_state")
    payload["summary"].pop("additional_investment_cash_required_eur")
    parsed = parse_portfolio_data(payload["recommendations"], payload["summary"], payload["policy_findings"], payload["holdings"])
    assert parsed.monthly_plan.execution_state in {
        "ready", "deferred_for_cost_efficiency", "no_eligible_purchase"
    }
    assert parsed.monthly_plan.additional_investment_cash_required_eur == 0


def test_translations_use_clear_investment_cash_terminology() -> None:
    en = json.loads((COMPONENT / "translations/en.json").read_text())
    de = json.loads((COMPONENT / "translations/de.json").read_text())
    assert en["entity"]["sensor"]["available_investment_reserve"]["name"] == "Authorized investment cash"
    assert en["entity"]["sensor"]["remaining_investment_reserve"]["name"] == "Cash after recommended purchases"
    assert de["entity"]["sensor"]["available_investment_reserve"]["name"] == "Freigegebenes Anlageguthaben"
    assert "execution_state" in en["entity"]["sensor"]
    assert "execution_state" in de["entity"]["sensor"]


def test_dashboard_uses_execution_state_not_ambiguous_plan_not_ready() -> None:
    dashboard = (ROOT / "dashboard/bilingual-dashboard.yaml").read_text()
    assert "sensor.portfolio_architect_execution_state" in dashboard
    assert "Plan not ready" not in dashboard
    assert "Plan nicht bereit" not in dashboard
    assert "Waiting for investment cash" in dashboard
    assert "Warten auf Anlageguthaben" in dashboard
    assert "Authorized investment cash" in dashboard
    assert "Cash after recommended purchases" in dashboard
    assert "sensor.portfolio_architect_additional_investment_cash_required" in dashboard


def test_v1163_version_metadata_is_aligned() -> None:
    assert 'version = "1.62.2"' in (ROOT / "pyproject.toml").read_text()
