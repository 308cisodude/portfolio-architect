"""v1.42.0 normalized execution-path presentation contracts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
DASHBOARD = ROOT / "dashboard" / "bilingual-dashboard.yaml"


def _load_execution_path():
    path = COMPONENT / "execution_path.py"
    spec = importlib.util.spec_from_file_location("pa_v142_execution_path", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _position(
    *,
    fund_id: str,
    isin: str,
    name: str,
    amount: float,
    execution_provider: str,
    execution_provider_name: str,
    funding_provider: str | None,
    funding_provider_name: str | None,
    transfer_required: bool,
    execution_fee: float = 0.0,
    cash_outlay: float | None = None,
    route: str = "free_savings_plan",
):
    return SimpleNamespace(
        fund_id=fund_id,
        isin=isin,
        name=name,
        buy_enabled=True,
        deferred=False,
        proposed_buy_eur=amount,
        execution_route=route,
        execution_provider=execution_provider,
        execution_provider_name=execution_provider_name,
        funding_provider=funding_provider,
        funding_provider_name=funding_provider_name,
        funding_transfer_required=transfer_required,
        estimated_fee_eur=execution_fee,
        estimated_cash_outlay_eur=(
            cash_outlay if cash_outlay is not None else amount + execution_fee
        ),
    )


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_local_cash_path_is_normalized_without_reinferring_routing() -> None:
    module = _load_execution_path()
    plan = SimpleNamespace(funding_transfers=())
    position = _position(
        fund_id="synthetic_global",
        isin="IE0000001420",
        name="Synthetic Global Equity ETF",
        amount=420.00,
        execution_provider="destination_broker",
        execution_provider_name="Synthetic Destination Broker",
        funding_provider="destination_broker",
        funding_provider_name="Synthetic Destination Broker",
        transfer_required=False,
    )

    result = module.build_execution_path(plan, (position,))

    assert result is not None
    assert result.mode == "local_cash"
    assert [step["action"] for step in result.steps] == ["use_local_cash", "purchase"]
    assert result.steps[0] == {
        "sequence": 1,
        "action": "use_local_cash",
        "provider_id": "destination_broker",
        "provider_name": "Synthetic Destination Broker",
        "amount_eur": 420.0,
    }
    assert result.steps[1]["funding_mode"] == "local_cash"
    assert result.steps[1]["execution_provider"] == "destination_broker"
    assert "Use €420.00 already available at Synthetic Destination Broker." in result.instruction
    assert "420,00 € bereits verfügbares Guthaben bei Synthetic Destination Broker verwenden." in result.instruction_de
    assert "**Use local cash:** €420.00 already available at Synthetic Destination Broker" in result.markdown
    assert "**Buy:** €420.00 of Synthetic Global Equity ETF at Synthetic Destination Broker via savings plan" in result.markdown
    assert "Transfer:" not in result.markdown

    source = (COMPONENT / "execution_path.py").read_text(encoding="utf-8")
    assert "engine.execution" not in source
    assert "engine.rebalance" not in source
    assert "choose_route" not in source
    assert "choose_funded_route" not in source


def test_transfer_path_renders_decided_transfer_then_purchase_with_conservative_delay() -> None:
    module = _load_execution_path()
    transfer = SimpleNamespace(
        from_provider="source_broker",
        from_provider_name="Synthetic Source Broker",
        to_provider="destination_broker",
        to_provider_name="Synthetic Destination Broker",
        amount_eur=420.25,
        fee_eur=0.75,
        settlement_business_days=0,
    )
    plan = SimpleNamespace(funding_transfers=(transfer,))
    position = _position(
        fund_id="synthetic_global",
        isin="IE0000001420",
        name="Synthetic Global Equity ETF",
        amount=420.00,
        execution_provider="destination_broker",
        execution_provider_name="Synthetic Destination Broker",
        funding_provider="source_broker",
        funding_provider_name="Synthetic Source Broker",
        transfer_required=True,
        execution_fee=0.25,
        cash_outlay=421.00,
        route="paid_savings_plan",
    )

    result = module.build_execution_path(plan, (position,))

    assert result is not None
    assert result.mode == "transfer"
    assert [step["action"] for step in result.steps] == ["funding_transfer", "purchase"]
    assert result.steps[0]["amount_eur"] == 420.25
    assert result.steps[0]["fee_eur"] == 0.75
    assert result.steps[0]["settlement_business_days"] == 0
    assert result.steps[1]["funding_mode"] == "transfer"
    assert "Transfer €420.25 from Synthetic Source Broker to Synthetic Destination Broker" in result.instruction
    assert "available same business day" in result.instruction
    assert "**Transfer:** €420.25 from Synthetic Source Broker to Synthetic Destination Broker" in result.markdown
    assert "available same business day" in result.markdown
    assert "Ausführungsgebühr 0,25 €" in result.markdown_de


def test_mixed_path_aggregates_local_cash_by_provider_and_keeps_bounded_sequence() -> None:
    module = _load_execution_path()
    transfer = SimpleNamespace(
        from_provider="source_broker",
        from_provider_name="Synthetic Source Broker",
        to_provider="destination_broker_b",
        to_provider_name="Synthetic Destination B",
        amount_eur=210.00,
        fee_eur=0.00,
        settlement_business_days=2,
    )
    plan = SimpleNamespace(funding_transfers=(transfer,))
    positions = (
        _position(
            fund_id="local_a",
            isin="IE0000001421",
            name="Synthetic Local ETF A",
            amount=100.00,
            execution_provider="destination_broker_a",
            execution_provider_name="Synthetic Destination A",
            funding_provider="destination_broker_a",
            funding_provider_name="Synthetic Destination A",
            transfer_required=False,
        ),
        _position(
            fund_id="local_b",
            isin="IE0000001422",
            name="Synthetic Local ETF B",
            amount=120.00,
            execution_provider="destination_broker_a",
            execution_provider_name="Synthetic Destination A",
            funding_provider="destination_broker_a",
            funding_provider_name="Synthetic Destination A",
            transfer_required=False,
        ),
        _position(
            fund_id="transfer_c",
            isin="IE0000001423",
            name="Synthetic Transfer ETF C",
            amount=210.00,
            execution_provider="destination_broker_b",
            execution_provider_name="Synthetic Destination B",
            funding_provider="source_broker",
            funding_provider_name="Synthetic Source Broker",
            transfer_required=True,
        ),
    )

    result = module.build_execution_path(plan, positions)

    assert result is not None
    assert result.mode == "mixed"
    assert [step["action"] for step in result.steps] == [
        "funding_transfer",
        "use_local_cash",
        "purchase",
        "purchase",
        "purchase",
    ]
    assert result.steps[1]["provider_id"] == "destination_broker_a"
    assert result.steps[1]["amount_eur"] == 220.0
    assert [step["sequence"] for step in result.steps] == [1, 2, 3, 4, 5]
    assert "available in 2 business days" in result.markdown
    assert "verfügbar in 2 Geschäftstagen" in result.markdown_de


def test_reference_dashboard_only_renders_integration_owned_execution_text() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    assert len(doc["views"]) == 2
    expected = (
        ("Execution path", "markdown"),
        ("Ausführungsweg", "markdown_de"),
    )
    for view, (title, attribute) in zip(doc["views"], expected, strict=True):
        cards = [
            item
            for item in _walk(view)
            if item.get("type") == "markdown" and item.get("title") == title
        ]
        assert len(cards) == 1
        card = cards[0]
        assert card["content"] == (
            f"{{{{ state_attr('sensor.portfolio_architect_execution_path', '{attribute}') or '' }}}}"
        )
        content = card["content"]
        for forbidden in ("funding_transfers", "provider_investment_cash", "execution_provider", "{%", " for ", " if "):
            assert forbidden not in content

        wrappers = [
            item
            for item in _walk(view)
            if item.get("type") == "conditional" and item.get("card") is card
        ]
        assert len(wrappers) == 1
        assert wrappers[0]["conditions"] == [
            {
                "condition": "state",
                "entity": "sensor.portfolio_architect_execution_path",
                "state_not": "unavailable",
            },
            {
                "condition": "state",
                "entity": "sensor.portfolio_architect_execution_path",
                "state_not": "unknown",
            },
        ]

    source = DASHBOARD.read_text(encoding="utf-8").casefold()
    for forbidden in ("auto-entities", "card-mod", "custom:", "javascript"):
        assert forbidden not in source
    assert source.count("type: markdown") == 2


def test_execution_path_entity_is_bilingual_bounded_and_wire_schemas_stay_unchanged() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    helper = (COMPONENT / "execution_path.py").read_text(encoding="utf-8")
    assert "PortfolioExecutionPathSensor(coordinator, entry)" in sensor
    assert 'self._attr_unique_id = f"{source_key}_execution_path"' in sensor
    assert '"steps": [dict(item) for item in presentation.steps]' in sensor
    assert '"markdown": presentation.markdown' in sensor
    assert '"markdown_de": presentation.markdown_de' in sensor
    assert "_MAX_EXECUTION_PATH_STEPS = 80" in helper
    assert "EXECUTION_PATH_SCHEMA_VERSION = 1" in helper

    for locale in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{locale}.json").read_text(encoding="utf-8")
        )
        entity = translations["entity"]["sensor"]["execution_path"]
        assert set(entity["state"]) == {
            "local_cash",
            "transfer",
            "mixed",
            "purchase_only",
        }
        assert set(entity["state_attributes"]) == {
            "execution_path_schema_version",
            "step_count",
            "steps",
            "instruction",
            "instruction_de",
            "markdown",
            "markdown_de",
        }

    release_notes = (ROOT / "docs" / "RELEASE-NOTES.md").read_text(encoding="utf-8")
    for contract in (
        "payload schema 8: unchanged",
        "REST portfolio schema 1: unchanged",
        "Gateway health schema 9 current; schemas 1–8 remain supported",
        "presentation schema 2",
        "broker schemas 1/2/3",
    ):
        assert contract in release_notes
