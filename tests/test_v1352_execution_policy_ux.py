"""Regression coverage for v1.35.2 execution-policy UX and semantics."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import stat
import sys
import types

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
# Load the pure engine/editor modules without importing the Home Assistant integration
# package __init__, because the preparation environment intentionally has no HA runtime.
package = types.ModuleType("portfolio_architect")
package.__path__ = [str(COMPONENT)]
sys.modules.setdefault("portfolio_architect", package)

from portfolio_architect.broker_editor import (
    TIE_BREAK_FALLBACK,
    TIE_BREAK_NEUTRAL,
    TIE_BREAK_PREFERRED,
    add_funding_transfer,
    load_broker_editor_context,
    remove_provider,
    tie_break_mode,
    upsert_provider,
    upsert_savings_plan,
    write_broker_document_atomic,
)
from portfolio_architect.engine.execution import (
    execution_providers,
    preferred_savings_plan_route,
)

ISIN = "IE0000000001"


def _broker(*, schema: int = 2) -> dict:
    document = {
        "schema_version": schema,
        "fee_data_max_age_days": 366,
        "providers": {
            "broker_a": {
                "name": "Broker A",
                "source": "Synthetic tariff evidence",
                "as_of": "2026-08-19",
                "savings_plans": {
                    ISIN: {
                        "available": True,
                        "fee_pct": 1.5,
                        "promotional": True,
                        "status": "synthetic_promotion",
                    }
                },
            },
            "broker_b": {
                "name": "Broker B",
                "source": "Synthetic tariff evidence",
                "as_of": "2026-08-19",
                "savings_plans": {
                    ISIN: {
                        "available": True,
                        "fee_pct": 0,
                        "promotional": False,
                        "status": "synthetic_standard_tariff",
                    }
                },
            },
        },
    }
    if schema == 3:
        document["funding_transfers"] = []
    return document


def test_promotional_is_validated_but_never_beats_lower_cost() -> None:
    broker = _broker()
    route = preferred_savings_plan_route(broker, ISIN, evaluated_on=date(2026, 8, 19))
    assert route is not None
    assert route.provider_id == "broker_b"
    assert route.fee_pct == Decimal("0")

    broker["providers"]["broker_b"]["savings_plans"][ISIN]["promotional"] = "no"
    with pytest.raises(ValueError, match="promotional flag"):
        execution_providers(broker, evaluated_on=date(2026, 8, 19))


def test_equal_fees_ignore_promotional_status_and_use_tie_break_only() -> None:
    broker = _broker()
    broker["providers"]["broker_a"]["savings_plans"][ISIN]["fee_pct"] = 0
    broker["providers"]["broker_a"]["priority"] = 50
    broker["providers"]["broker_b"]["priority"] = 150
    route = preferred_savings_plan_route(broker, ISIN, evaluated_on=date(2026, 8, 19))
    assert route is not None
    assert route.provider_id == "broker_a"


def test_native_editor_tie_break_is_neutral_by_default_and_preserves_legacy_number() -> None:
    broker = _broker()
    assert tie_break_mode(broker["providers"]["broker_a"]) == TIE_BREAK_NEUTRAL
    neutral = upsert_provider(
        broker,
        provider_id="broker_a",
        name="Broker A",
        source="Synthetic tariff evidence",
        as_of="2026-08-19",
        tie_break=TIE_BREAK_NEUTRAL,
        create=False,
    )
    assert "priority" not in neutral["providers"]["broker_a"]

    broker["providers"]["broker_a"]["priority"] = 10
    preserved = upsert_provider(
        broker,
        provider_id="broker_a",
        name="Broker A updated",
        source="Synthetic tariff evidence",
        as_of="2026-08-19",
        tie_break=TIE_BREAK_PREFERRED,
        create=False,
    )
    assert preserved["providers"]["broker_a"]["priority"] == 10
    changed = upsert_provider(
        preserved,
        provider_id="broker_a",
        name="Broker A updated",
        source="Synthetic tariff evidence",
        as_of="2026-08-19",
        tie_break=TIE_BREAK_FALLBACK,
        create=False,
    )
    assert changed["providers"]["broker_a"]["priority"] == 150


def test_native_editor_adds_exact_directed_edge_and_blocks_referenced_provider_removal() -> None:
    broker = add_funding_transfer(
        _broker(),
        from_provider="broker_a",
        to_provider="broker_b",
        fee_eur=0,
        settlement_business_days=0,
        source="Synthetic verified transfer",
        as_of="2026-08-19",
    )
    assert broker["schema_version"] == 3
    assert broker["funding_transfers"] == [{
        "from_provider": "broker_a",
        "to_provider": "broker_b",
        "fee_eur": 0.0,
        "settlement_business_days": 0,
        "source": "Synthetic verified transfer",
        "as_of": "2026-08-19",
    }]
    with pytest.raises(ValueError, match="funding transfers"):
        remove_provider(broker, provider_id="broker_b")


def test_native_editor_atomic_round_trip_and_schema1_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "broker.yaml"
    path.write_text(yaml.safe_dump(_broker(schema=3), sort_keys=False), encoding="utf-8")
    path.chmod(0o640)
    context = load_broker_editor_context(tmp_path)
    updated = upsert_savings_plan(
        context.document,
        provider_id="broker_b",
        isin="IE0000000002",
        available=True,
        fee_pct=0.25,
        promotional=False,
        status="synthetic_standard_tariff",
        create=True,
    )
    write_broker_document_atomic(path, updated)
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    reloaded = load_broker_editor_context(tmp_path)
    assert reloaded.document["providers"]["broker_b"]["savings_plans"]["IE0000000002"]["promotional"] is False

    legacy = {"schema_version": 1, "broker": {"id": "legacy", "name": "Legacy", "savings_plans": {}}}
    path.write_text(yaml.safe_dump(legacy, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="schema 2 or 3"):
        load_broker_editor_context(tmp_path)


def test_options_flow_exposes_native_broker_editor_and_explains_semantics() -> None:
    flow = (ROOT / "custom_components" / "portfolio_architect" / "config_flow.py").read_text(encoding="utf-8")
    assert '"execution_providers"' in flow
    assert "async_step_funding_topology" in flow
    assert "async_step_broker_savings_plans" in flow
    en = (ROOT / "custom_components" / "portfolio_architect" / "translations" / "en.json").read_text(encoding="utf-8")
    assert "Tie-break preference" in en
    assert "Promotional status" in en
    assert "reverse direction is never inferred" in en
