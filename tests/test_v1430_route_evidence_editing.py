"""Regression coverage for v1.43.0 route-level evidence and native editing."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
package = types.ModuleType("portfolio_architect")
package.__path__ = [str(COMPONENT)]
sys.modules.setdefault("portfolio_architect", package)

from portfolio_architect.broker_editor import (  # noqa: E402
    edit_funding_transfer,
    upsert_savings_plan,
)
from portfolio_architect.engine.execution import (  # noqa: E402
    ExecutionConfig,
    choose_route,
    savings_plan_routes,
)

D = Decimal
ISIN_A = "IE0000000001"
ISIN_B = "IE0000000002"


def _broker() -> dict:
    return {
        "schema_version": 3,
        "fee_data_max_age_days": 30,
        "providers": {
            "source": {
                "name": "Source Broker",
                "source": "Synthetic provider tariff evidence",
                "as_of": "2026-07-01",
                "savings_plans": {
                    ISIN_A: {
                        "available": True,
                        "fee_pct": 0,
                        "source": "Synthetic route-specific evidence",
                        "as_of": "2026-08-20",
                    },
                    ISIN_B: {"available": True, "fee_pct": 1.5},
                },
            },
            "destination": {
                "name": "Destination Broker",
                "source": "Synthetic provider tariff evidence",
                "as_of": "2026-08-20",
                "savings_plans": {},
            },
        },
        "funding_transfers": [
            {
                "from_provider": "source",
                "to_provider": "destination",
                "fee_eur": 1.0,
                "settlement_business_days": 2,
                "source": "Synthetic transfer evidence",
                "as_of": "2026-08-20",
            }
        ],
    }


def test_route_evidence_is_independently_fresh_from_provider_evidence() -> None:
    broker = _broker()
    routes = savings_plan_routes(broker, ISIN_A, evaluated_on=date(2026, 8, 22))
    assert len(routes) == 1
    route = routes[0]
    assert route.provider_id == "source"
    assert route.fee_pct == D("0.0000")
    assert route.source == "Synthetic route-specific evidence"
    assert route.as_of == date(2026, 8, 20)

    chosen = choose_route(
        isin=ISIN_A,
        savings_plan_amount_eur=D("100"),
        manual_order_amount_eur=D("0"),
        broker=broker,
        config=ExecutionConfig(enabled=True),
        evaluated_on=date(2026, 8, 22),
    )
    assert chosen.provider_id == "source"
    assert chosen.fee_data_as_of == "2026-08-20"

    # The sibling legacy route has no route-level provenance, so it still falls
    # back to the provider-level evidence and therefore fails closed as stale.
    assert savings_plan_routes(broker, ISIN_B, evaluated_on=date(2026, 8, 22)) == ()


def test_stale_route_evidence_fails_closed_even_when_provider_is_fresh() -> None:
    broker = _broker()
    broker["providers"]["source"]["as_of"] = "2026-08-22"
    broker["providers"]["source"]["savings_plans"][ISIN_A]["as_of"] = "2026-07-01"
    assert savings_plan_routes(broker, ISIN_A, evaluated_on=date(2026, 8, 22)) == ()


def test_legacy_route_inherits_provider_evidence_for_backward_compatibility() -> None:
    broker = _broker()
    broker["providers"]["source"]["as_of"] = "2026-08-21"
    routes = savings_plan_routes(broker, ISIN_B, evaluated_on=date(2026, 8, 22))
    assert len(routes) == 1
    assert routes[0].source == "Synthetic provider tariff evidence"
    assert routes[0].as_of == date(2026, 8, 21)


def test_partial_or_future_route_evidence_is_rejected() -> None:
    broker = _broker()
    del broker["providers"]["source"]["savings_plans"][ISIN_A]["source"]
    with pytest.raises(ValueError, match="savings-plan evidence"):
        savings_plan_routes(broker, ISIN_A, evaluated_on=date(2026, 8, 22))

    broker = _broker()
    broker["providers"]["source"]["savings_plans"][ISIN_A]["as_of"] = "2026-08-23"
    with pytest.raises(ValueError, match="in the future"):
        savings_plan_routes(broker, ISIN_A, evaluated_on=date(2026, 8, 22))


def test_native_route_editor_writes_explicit_route_provenance() -> None:
    broker = _broker()
    broker["providers"]["destination"]["savings_plans"][ISIN_A] = {
        "available": True,
        "fee_pct": 1.5,
    }
    updated = upsert_savings_plan(
        broker,
        provider_id="destination",
        isin=ISIN_A,
        available=True,
        fee_pct=0,
        promotional=False,
        status="user_verified",
        source="Synthetic route PDF",
        as_of="2026-08-22",
        create=False,
        evaluated_on=date(2026, 8, 22),
    )
    assert updated["providers"]["destination"]["savings_plans"][ISIN_A] == {
        "available": True,
        "promotional": False,
        "fee_pct": 0.0,
        "status": "user_verified",
        "source": "Synthetic route PDF",
        "as_of": "2026-08-22",
    }


def test_native_funding_editor_updates_exact_edge_without_changing_identity() -> None:
    updated = edit_funding_transfer(
        _broker(),
        from_provider="source",
        to_provider="destination",
        fee_eur=0,
        settlement_business_days=0,
        source="New synthetic transfer evidence",
        as_of="2026-08-22",
        evaluated_on=date(2026, 8, 22),
    )
    assert updated["funding_transfers"] == [
        {
            "from_provider": "source",
            "to_provider": "destination",
            "fee_eur": 0.0,
            "settlement_business_days": 0,
            "source": "New synthetic transfer evidence",
            "as_of": "2026-08-22",
        }
    ]


def test_configure_surface_exposes_route_evidence_and_funding_editing_bilingually() -> None:
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    assert 'CONF_BROKER_ROUTE_SOURCE = "broker_route_source"' in flow
    assert 'CONF_BROKER_ROUTE_AS_OF = "broker_route_as_of"' in flow
    assert "vol.Required(CONF_BROKER_ROUTE_AS_OF): DateSelector(DateSelectorConfig())" in flow
    assert 'menu.append("edit_funding_transfer")' in flow
    assert "async def async_step_edit_funding_transfer(" in flow
    assert "async def async_step_edit_funding_transfer_details(" in flow

    for language, source_label, date_label, edit_label in (
        ("en", "Evidence source", "Evidence date", "Edit funding transfer"),
        ("de", "Evidenzquelle", "Evidenzdatum", "Finanzierungsbeziehung bearbeiten"),
    ):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        steps = translations["options"]["step"]
        assert steps["add_savings_plan_route"]["data"]["broker_route_source"] == source_label
        assert steps["add_savings_plan_route"]["data"]["broker_route_as_of"] == date_label
        assert steps["funding_topology"]["menu_options"]["edit_funding_transfer"] == edit_label
        assert steps["edit_funding_transfer_details"]["data"]["broker_transfer_source"] == source_label
        assert steps["edit_funding_transfer_details"]["data"]["broker_transfer_as_of"] == date_label
