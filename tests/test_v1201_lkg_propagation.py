"""v1.20.1 LKG propagation and repair-lifecycle regression contracts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_comdirect"


def test_coordinator_notifies_entities_when_only_degraded_metadata_changes() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

    # v1.20.0 could return the exact same trusted PortfolioData while changing
    # coordinator-side LKG/actionability/health metadata. Suppressing callbacks
    # on PortfolioData equality therefore left ordinary entities frozen in the
    # previous live state. Every completed coordinator cycle must notify them.
    constructor = coordinator.split("super().__init__(", 1)[1].split(")\n\n", 1)[0]
    assert "always_update=True" in constructor
    assert "always_update=False" not in constructor


def test_lkg_actionability_entities_remain_fail_closed() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")

    assert "if self._using_home_assistant_last_known_good:" in coordinator
    assert "return False" in coordinator.split(
        "def plan_actionable(self) -> bool:", 1
    )[1].split("def plan_actionability_reason", 1)[0]

    available_cash = sensor.split(
        "class PortfolioAvailableInvestmentReserveSensor", 1
    )[1].split("\nclass ", 1)[0]
    recommended = sensor.split("class PortfolioRecommendedTotalSensor", 1)[1].split(
        "\nclass ", 1
    )[0]
    ready = binary.split("class PortfolioMonthlyPlanReady", 1)[1].split(
        "\nclass ", 1
    )[0]
    assert "requires_actionable_source = True" in available_cash
    assert "requires_actionable_source = True" in recommended
    assert "self.coordinator.plan_actionable" in ready


def test_unrelated_lkg_failure_does_not_republish_stale_integrity_error() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    lkg = coordinator.split(
        "def _use_home_assistant_last_known_good(", 1
    )[1].split("def _apply_aggregation", 1)[0]

    assert "integrity_failure: bool = False" in lkg
    assert "if not integrity_failure:" in lkg
    assert "self.rest_snapshot_integrity_error = None" in lkg

    regression = coordinator.split(
        '"Local REST source attempted to replace the accepted snapshot "', 1
    )[1].split("try:\n            integrity_verified", 1)[0]
    assert "integrity_failure=True" in regression

    validation_failure = coordinator.split(
        "except PortfolioRestError as err:\n            self.rest_snapshot_integrity_error", 1
    )[1].split("if reuse_existing_data:", 1)[0]
    assert "integrity_failure=True" in validation_failure


def test_gateway_reauthentication_contract_keeps_cached_integrity_evidence() -> None:
    server_test = (ROOT / "gateway" / "tests" / "test_gateway_server.py").read_text(
        encoding="utf-8"
    )
    assert "test_reauthentication_health_retains_cached_snapshot_integrity_metadata" in server_test
    assert 'health["snapshot_sha256"] == cached.sha256' in server_test
    assert 'health["snapshot_position_count"] == cached.position_count' in server_test


def test_v1201_version_alignment_and_wire_compatibility() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    app = yaml.safe_load((APP / "config.yaml").read_text(encoding="utf-8"))
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    engine = (COMPONENT / "engine" / "__init__.py").read_text(encoding="utf-8")
    gateway = (APP / "src" / "portfolio_architect_gateway" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert manifest["version"] == "1.62.0"
    assert app["version"] == "1.62.0"
    assert 'VERSION: Final = "1.62.0"' in const
    assert '__version__ = "1.62.0"' in engine
    assert '__version__ = "1.62.0"' in gateway
    assert app["stage"] == "stable"

    # v1.20.1 is propagation/repair hygiene only. No payload or wire-schema bump.
    integration_init = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    rest_client = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    assert "schema version 12" in integration_init
    assert '"requested_health_schema_version": 10' in rest_client
