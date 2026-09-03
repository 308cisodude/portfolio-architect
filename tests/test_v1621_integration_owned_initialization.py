"""Regression contract for v1.62.2 integration-owned first-run initialization."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib
import json
from pathlib import Path
import sys
import types

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
CONFIG_FLOW = COMPONENT / "config_flow.py"
INIT = COMPONENT / "__init__.py"
CONST = COMPONENT / "const.py"

TEST_PACKAGE = "portfolio_architect_v1621_component_test"
if TEST_PACKAGE not in sys.modules:
    package = types.ModuleType(TEST_PACKAGE)
    package.__path__ = [str(COMPONENT)]
    package.__package__ = TEST_PACKAGE
    sys.modules[TEST_PACKAGE] = package

bootstrap = importlib.import_module(f"{TEST_PACKAGE}.bootstrap")
execution = importlib.import_module(f"{TEST_PACKAGE}.engine.execution")
models = importlib.import_module(f"{TEST_PACKAGE}.engine.models")

BootstrapInstrument = bootstrap.BootstrapInstrument
BootstrapPlan = bootstrap.BootstrapPlan
Position = models.Position


def _position(*, identifier: str, isin: str, name: str) -> Position:
    return Position(
        wkn="A1XB5U",
        isin=isin,
        name=name,
        instrument_type="etf",
        source_type="generic_csv",
        value_eur=Decimal("1000"),
    )


def _plan(position: Position) -> BootstrapPlan:
    return BootstrapPlan(
        name="Clean-room plan",
        budget_amount_eur=Decimal("100"),
        corridor_pp=Decimal("1"),
        minimum_trade_eur=Decimal("20"),
        rounding_step_eur=Decimal("10"),
        instruments=(
            BootstrapInstrument(
                position=position,
                target_pct=Decimal("100"),
                buy_enabled=True,
                ucits=True,
                domicile="IE",
                distribution="accumulating",
                fund_currency="EUR",
                ter_pct=Decimal("0.12"),
                fund_size_eur=Decimal("1000000000"),
                metadata_source="Synthetic clean-room evidence",
            ),
        ),
        ucits_required=True,
        accumulating_preferred=True,
        ireland_preferred=False,
        max_ter_pct=Decimal("0.70"),
        minimum_fund_size_eur=Decimal("100000000"),
        savings_plan_required=False,
        free_savings_plan_preferred=False,
    )


def test_initialize_creates_only_empty_owned_directory_and_refuses_partial_state(tmp_path: Path) -> None:
    target = tmp_path / "portfolio-architect"
    assert bootstrap.configuration_state(target) == "missing"
    assert bootstrap.initialize_configuration_directory(target) == "empty"
    assert target.is_dir()
    assert list(target.iterdir()) == []

    (target / "portfolio.yaml").write_text("schema_version: 2\n", encoding="utf-8")
    assert bootstrap.configuration_state(target) == "partial"
    with pytest.raises(ValueError, match="partially populated"):
        bootstrap.initialize_configuration_directory(target)


def test_initial_documents_are_user_owned_and_create_no_execution_provider() -> None:
    position = _position(
        identifier="TESTETF1",
        isin="IE00BJ0KDQ92",
        name="Synthetic Global ETF",
    )
    documents = bootstrap.build_configuration_documents(_plan(position))
    assert set(documents) == set(bootstrap.REQUIRED_CONFIGURATION_FILES)
    portfolio = documents["portfolio.yaml"]
    assert portfolio["portfolio"]["allocation"][0]["isin"] == "IE00BJ0KDQ92"
    assert portfolio["portfolio"]["allocation"][0]["target_pct"] == 100.0
    assert documents["instruments.yaml"]["instruments"]["IE00BJ0KDQ92"]["metadata_status"] == "user_confirmed"
    broker = documents["broker.yaml"]
    assert broker == {
        "schema_version": 3,
        "fee_data_max_age_days": 30,
        "providers": {},
        "funding_transfers": [],
    }
    assert execution.execution_providers(broker, evaluated_on=datetime(2026, 9, 1).date()) == ()


def test_initial_configuration_validates_before_install_and_never_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "portfolio-architect"
    bootstrap.initialize_configuration_directory(target)
    position = _position(
        identifier="TESTETF1",
        isin="IE00BJ0KDQ92",
        name="Synthetic Global ETF",
    )
    positions = {"TESTETF1": position}
    documents = bootstrap.build_configuration_documents(_plan(position))
    payload = bootstrap.write_initial_configuration(
        target,
        documents,
        positions=positions,
        evaluated_at=datetime(2026, 9, 1, 14, 31, 39, tzinfo=timezone.utc),
        source_provider="generic_60319d543354",
        source_label="Test Broker",
    )
    assert payload["schema_version"] == 8
    assert bootstrap.configuration_state(target) == "configured"
    assert set(path.name for path in target.iterdir()) == set(bootstrap.REQUIRED_CONFIGURATION_FILES)
    assert yaml.safe_load((target / "broker.yaml").read_text(encoding="utf-8"))["providers"] == {}
    with pytest.raises(ValueError, match="refuses to overwrite"):
        bootstrap.write_initial_configuration(
            target,
            documents,
            positions=positions,
            evaluated_at=datetime(2026, 9, 1, 14, 31, 39, tzinfo=timezone.utc),
            source_provider="generic_60319d543354",
            source_label="Test Broker",
        )


def test_config_flow_is_integration_first_and_gateway_discovery_never_bootstraps_service() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    user = source.split("async def async_step_user", 1)[1].split("async def async_step_initialize", 1)[0]
    initialize = source.split("async def async_step_initialize", 1)[1].split("async def async_step_reconfigure", 1)[0]
    hassio = source.split("async def async_step_hassio", 1)[1].split("async def async_step_hassio_comdirect", 1)[0]
    assert "return await self.async_step_initialize(user_input)" in user
    assert "initialize_configuration_directory" in initialize
    assert "SETUP_STATE_SOURCE_REQUIRED" in initialize
    assert 'return self.async_abort(reason="pa_not_initialized")' in hassio
    assert "async_step_hassio_confirm" not in hassio
    assert "_remember_hassio_discovery_candidate(self.hass, discovery)" in hassio


def test_setup_required_entry_loads_without_coordinator_or_entities() -> None:
    source = INIT.read_text(encoding="utf-8")
    setup = source.split("async def async_setup_entry", 1)[1].split("async def async_unload_entry", 1)[0]
    assert "setup_state != SETUP_STATE_CONFIGURED" in setup
    assert "entry.runtime_data = None" in setup
    before_coordinator = setup.split("coordinator = PortfolioArchitectCoordinator", 1)[0]
    assert "return True" in before_coordinator


def test_existing_source_migrations_and_discovery_suppression_remain_present() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    assert "matches_comdirect_slug_successor" in source
    assert "_async_migrate_primary_tls" in source
    assert "_async_migrate_supplemental_tls" in source
    assert "add_discovered_rest_gateway" in source
    assert "add_discovered_primary_rest_gateway" in source
    assert "health.snapshot_sha256 != result.snapshot_sha256" in source


def test_bilingual_onboarding_copy_states_integration_ownership_and_no_invented_plan() -> None:
    for language in ("en", "de"):
        payload = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        initialize = payload["config"]["step"]["initialize"]
        assert "config_directory" in initialize["data"]
        assert "pa_not_initialized" in payload["config"]["abort"]
        options = payload["options"]["step"]
        for step in (
            "add_discovered_primary_rest_gateway",
            "add_discovered_primary_rest_gateway_details",
            "initial_setup",
            "initial_setup_instrument",
            "initial_setup_policy",
        ):
            assert step in options
        assert "initial_setup_invalid" in payload["options"]["error"]


def test_release_version_and_changelog_target_v1621() -> None:
    const = CONST.read_text(encoding="utf-8")
    assert 'VERSION: Final = "1.62.2"' in const
    # Release metadata is finalized before the candidate is frozen.


def test_empty_execution_provider_topology_is_valid_only_without_edges() -> None:
    broker = {
        "schema_version": 3,
        "fee_data_max_age_days": 30,
        "providers": {},
        "funding_transfers": [],
    }
    funding = importlib.import_module(f"{TEST_PACKAGE}.engine.funding")
    assert funding.funding_transfers(broker, evaluated_on=datetime(2026, 9, 1).date()) == ()
    broker["funding_transfers"] = [
        {
            "from_provider": "a",
            "to_provider": "b",
            "fee_eur": 0,
            "settlement_business_days": 0,
        }
    ]
    with pytest.raises(ValueError, match="require configured providers"):
        funding.funding_transfers(broker, evaluated_on=datetime(2026, 9, 1).date())


def test_config_entry_schema_13_preserves_existing_entries_as_configured() -> None:
    flow = CONFIG_FLOW.read_text(encoding="utf-8")
    setup = INIT.read_text(encoding="utf-8")
    assert "VERSION = 13" in flow
    assert "if entry.version > 13:" in setup
    schema13 = setup.split("if entry.version < 13:", 1)[1].split("if migrated_entities:", 1)[0]
    assert "CONF_SETUP_STATE" in schema13
    assert "SETUP_STATE_CONFIGURED" in schema13
    assert "version=13" in schema13


def test_incomplete_entry_diagnostics_are_bounded_and_coordinator_free() -> None:
    source = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
    branch = source.split("setup_state =", 1)[1].split("coordinator: PortfolioArchitectCoordinator", 1)[0]
    assert "runtime_loaded" in branch
    assert "source_configured" in branch
    assert "config_directory" in branch
    assert "entry.runtime_data is None" in branch


def test_stale_v1620_hassio_confirm_cannot_create_the_service() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    step = source.split("async def async_step_hassio_confirm", 1)[1].split(
        "async def _async_migrate_primary_tls", 1
    )[0]
    assert 'return self.async_abort(reason="pa_not_initialized")' in step
    assert "async_create_entry" not in step
    assert "async_fetch_rest_snapshot" not in step


def test_initialization_creates_no_plan_or_source_material() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    initialize = source.split("async def async_step_initialize", 1)[1].split(
        "async def async_step_reconfigure", 1
    )[0]
    assert "initialize_configuration_directory" in initialize
    assert "build_configuration_documents" not in initialize
    assert "write_initial_configuration" not in initialize
    assert "CONF_REST_ENDPOINT_URL" not in initialize
    assert "CONF_REST_API_TOKEN" not in initialize


def test_initial_setup_does_not_prefill_investment_assumptions() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    plan_step = source.split("async def async_step_initial_setup(", 1)[1].split(
        "async def async_step_initial_setup_instrument", 1
    )[0]
    instrument_step = source.split("async def async_step_initial_setup_instrument", 1)[1].split(
        "async def async_step_initial_setup_review", 1
    )[0]
    policy_step = source.split("async def async_step_initial_setup_policy", 1)[1].split(
        "@staticmethod", 1
    )[0]
    assert "suggested: dict[str, Any] = {}" in plan_step
    assert "suggested: dict[str, Any] = {}" in instrument_step
    assert "suggested: dict[str, Any] = {}" in policy_step
    for invented in ('"domicile": "IE"', '"ter_pct": 0.25', '"max_ter_pct": 0.70'):
        assert invented not in plan_step + instrument_step + policy_step


def test_setup_completion_explicitly_reloads_the_previously_incomplete_entry() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    first_source = source.split("async def _async_commit_first_source", 1)[1].split(
        "async def async_step_add_discovered_primary_rest_gateway", 1
    )[0]
    policy = source.split("async def async_step_initial_setup_policy", 1)[1].split(
        "@staticmethod", 1
    )[0]
    assert "if complete:" in first_source
    assert "async_reload(self.config_entry.entry_id)" in first_source
    assert "async_reload(self.config_entry.entry_id)" in policy
