"""Regression coverage for v1.40.0 evidence-backed funding transfers."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
package = types.ModuleType("portfolio_architect")
package.__path__ = [str(COMPONENT)]
sys.modules.setdefault("portfolio_architect", package)

from portfolio_architect.broker_editor import add_funding_transfer
from portfolio_architect.engine.execution import ExecutionConfig, choose_funded_route_for_cash
from portfolio_architect.engine.funding import funding_transfers, transfer_for

D = Decimal
ISIN = "IE0000000001"


def _broker() -> dict:
    return {
        "schema_version": 3,
        "fee_data_max_age_days": 30,
        "providers": {
            "source": {
                "name": "Source Broker",
                "source": "Synthetic tariff evidence",
                "as_of": "2026-08-18",
                "savings_plans": {ISIN: {"available": True, "fee_pct": 1.5}},
            },
            "destination": {
                "name": "Destination Broker",
                "source": "Synthetic tariff evidence",
                "as_of": "2026-08-18",
                "savings_plans": {ISIN: {"available": True, "fee_pct": 0}},
            },
        },
        "funding_transfers": [
            {
                "from_provider": "source",
                "to_provider": "destination",
                "fee_eur": 0,
                "settlement_business_days": 0,
                "source": "Synthetic user-verified instant transfer",
                "as_of": "2026-08-18",
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


def test_evidenced_transfer_parses_provenance_and_freshness() -> None:
    edge = funding_transfers(_broker(), evaluated_on=date(2026, 8, 20))[0]
    assert edge.evidence_source == "Synthetic user-verified instant transfer"
    assert edge.evidence_as_of == date(2026, 8, 18)
    assert edge.evidence_fresh is True
    assert edge.fee_eur == D("0.00")
    assert edge.settlement_business_days == 0


def test_evidenced_transfer_fails_closed_when_stale() -> None:
    broker = _broker()
    edge = funding_transfers(broker, evaluated_on=date(2026, 9, 18))[0]
    assert edge.evidence_fresh is False
    assert transfer_for(
        broker,
        from_provider="source",
        to_provider="destination",
        evaluated_on=date(2026, 9, 18),
    ) is None

    # Keep execution-fee evidence fresh so only the transfer edge is stale.
    broker["providers"]["source"]["as_of"] = "2026-09-18"
    broker["providers"]["destination"]["as_of"] = "2026-09-18"
    route = choose_funded_route_for_cash(
        isin=ISIN,
        desired_amount_eur=D("350"),
        periodic_cash_budget_eur=D("350"),
        minimum_order_eur=D("20"),
        rounding_step_eur=D("10"),
        broker=broker,
        config=_config(),
        funding_cash_by_provider={"source": D("350")},
        funding_provider_names={"source": "Source Broker"},
        evaluated_on=date(2026, 9, 18),
    )
    assert route.provider_id == "source"
    assert route.funding_transfer_required is False


def test_future_or_partial_transfer_evidence_is_rejected() -> None:
    broker = _broker()
    broker["funding_transfers"][0]["as_of"] = "2026-08-21"
    with pytest.raises(ValueError, match="in the future"):
        funding_transfers(broker, evaluated_on=date(2026, 8, 20))

    broker = _broker()
    del broker["funding_transfers"][0]["source"]
    with pytest.raises(ValueError, match=r"funding_transfers\[0\] is invalid"):
        funding_transfers(broker, evaluated_on=date(2026, 8, 20))


def test_legacy_schema3_edge_remains_compatible() -> None:
    broker = _broker()
    broker["funding_transfers"][0].pop("source")
    broker["funding_transfers"][0].pop("as_of")
    edge = transfer_for(
        broker,
        from_provider="source",
        to_provider="destination",
        evaluated_on=date(2027, 8, 20),
    )
    assert edge is not None
    assert edge.evidence_source is None
    assert edge.evidence_as_of is None
    assert edge.evidence_fresh is True


def test_native_editor_creates_evidence_backed_edge() -> None:
    broker = _broker()
    broker["schema_version"] = 2
    broker.pop("funding_transfers")
    updated = add_funding_transfer(
        broker,
        from_provider="source",
        to_provider="destination",
        fee_eur=0,
        settlement_business_days=0,
        source="User verified transfer",
        as_of="2026-08-18",
    )
    assert updated["schema_version"] == 3
    assert updated["funding_transfers"] == [
        {
            "from_provider": "source",
            "to_provider": "destination",
            "fee_eur": 0.0,
            "settlement_business_days": 0,
            "source": "User verified transfer",
            "as_of": "2026-08-18",
        }
    ]

    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    assert 'CONF_BROKER_TRANSFER_SOURCE = "broker_transfer_source"' in flow
    assert 'CONF_BROKER_TRANSFER_AS_OF = "broker_transfer_as_of"' in flow
    en = (COMPONENT / "translations" / "en.json").read_text(encoding="utf-8")
    de = (COMPONENT / "translations" / "de.json").read_text(encoding="utf-8")
    assert "Evidence source" in en and "Evidence date (YYYY-MM-DD)" in en
    assert "Evidenzquelle" in de and "Evidenzdatum (JJJJ-MM-TT)" in de
