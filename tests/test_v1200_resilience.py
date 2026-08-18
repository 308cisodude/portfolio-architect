"""v1.20.0 graceful-degradation, freshness, and accountability contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from resilience import (  # noqa: E402
    refresh_overdue_is_evidenced,
    snapshot_age_seconds,
    snapshot_expires_in_seconds,
    snapshot_within_retention,
)

APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway"
UTC = timezone.utc


def _at(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, 8, 12, hour, minute, second, tzinfo=UTC)


def test_snapshot_age_is_derived_from_accepted_timestamp() -> None:
    generated = _at(12)
    assert snapshot_age_seconds(generated, now=_at(12, 3, 33)) == 213
    assert snapshot_age_seconds(generated, now=_at(12, 14, 2)) == 842
    # Clock skew must not publish a negative age.
    assert snapshot_age_seconds(generated, now=_at(11, 59)) == 0
    assert snapshot_age_seconds(None, now=_at(12)) is None


def test_snapshot_expiry_and_bounded_retention_are_time_derived() -> None:
    generated = _at(12)
    assert snapshot_expires_in_seconds(
        generated,
        maximum_age_seconds=900,
        now=_at(12, 3, 33),
    ) == 687
    assert snapshot_expires_in_seconds(
        generated,
        maximum_age_seconds=900,
        now=_at(12, 20),
    ) == 0
    assert snapshot_expires_in_seconds(
        generated,
        maximum_age_seconds=None,
        now=_at(12),
    ) is None

    seven_days = 7 * 24 * 60 * 60
    assert snapshot_within_retention(
        generated,
        maximum_age_seconds=seven_days,
        now=generated + timedelta(days=6, hours=23, minutes=59),
    )
    assert not snapshot_within_retention(
        generated,
        maximum_age_seconds=seven_days,
        now=generated + timedelta(days=7, seconds=1),
    )


def test_resilience_helpers_reject_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone"):
        snapshot_age_seconds(datetime(2026, 8, 12, 12), now=_at(12))


def test_old_health_sample_cannot_create_false_refresh_overdue() -> None:
    due = _at(13, 54, 36)
    # Reproduces the live v1.19.1 phase-lock: PA observed health before the
    # Gateway's scheduled refresh and did not observe it again until later.
    observed_before_due = _at(13, 53, 38)
    assert refresh_overdue_is_evidenced(
        next_refresh_due_at=due,
        health_observed_at=observed_before_due,
        refresh_in_progress=False,
        grace_seconds=225,
        now=_at(14, 5),
    ) is False


def test_fresh_health_sample_can_prove_a_real_missed_refresh() -> None:
    due = _at(13, 54, 36)
    threshold = due + timedelta(seconds=225)
    observed_after_grace = threshold + timedelta(seconds=1)
    assert refresh_overdue_is_evidenced(
        next_refresh_due_at=due,
        health_observed_at=observed_after_grace,
        refresh_in_progress=False,
        grace_seconds=225,
        now=observed_after_grace,
    ) is True
    assert refresh_overdue_is_evidenced(
        next_refresh_due_at=due,
        health_observed_at=observed_after_grace,
        refresh_in_progress=True,
        grace_seconds=225,
        now=observed_after_grace,
    ) is False


def test_coordinator_preserves_trusted_lkg_and_requires_live_evidence_for_actions() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    assert "DEFAULT_HOME_ASSISTANT_LKG_MAX_AGE_SECONDS" in coordinator
    assert coordinator.count("snapshot_within_retention(") >= 2
    assert "refresh_overdue_is_evidenced(" in coordinator
    assert "self._gateway_health_observed_at = dt_util.utcnow()" in coordinator
    assert "snapshot_age_seconds(\n            self.gateway_snapshot_generated_at" in coordinator
    assert "def plan_actionable(self) -> bool:" in coordinator
    assert "if self._using_home_assistant_last_known_good:" in coordinator
    assert "if health is None or health.reauthentication_required:" in coordinator
    assert 'return self.gateway_operating_mode == "live"' in coordinator

    # Timestamp regression and integrity failures reject the incoming snapshot
    # but retain a previously validated cache instead of making all entities fail.
    regression = coordinator.split(
        '"Local REST source attempted to replace the accepted snapshot "', 1
    )[1].split("try:\n            integrity_verified", 1)[0]
    assert "return self._use_home_assistant_last_known_good(" in regression
    integrity = coordinator.split(
        "except PortfolioRestError as err:\n            self.rest_snapshot_integrity_error", 1
    )[1].split("if reuse_existing_data:", 1)[0]
    assert "return self._use_home_assistant_last_known_good(" in integrity


def test_stale_cash_and_recommendations_are_not_actionable() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")

    assert "requires_actionable_source: bool = False" in sensor
    for class_name in (
        "PortfolioRecommendedTotalSensor",
        "PortfolioUnallocatedContributionSensor",
        "PortfolioAvailableInvestmentReserveSensor",
        "PortfolioRemainingInvestmentReserveSensor",
        "PortfolioDeferredContributionSensor",
        "PortfolioEstimatedTransactionFeesSensor",
        "PortfolioEstimatedCashOutlaySensor",
        "PortfolioAdditionalInvestmentCashRequiredSensor",
        "PortfolioExecutionStateSensor",
        "PortfolioInvestmentReserveSourceSensor",
    ):
        block = sensor.split(f"class {class_name}", 1)[1].split("\nclass ", 1)[0]
        assert "requires_actionable_source = True" in block, class_name

    assert "and self.coordinator.plan_actionable" in sensor
    proposed = sensor.split("class PortfolioProposedBuySensor", 1)[1].split(
        "\nclass ", 1
    )[0]
    assert "self.coordinator.plan_actionable" in proposed
    explanation = sensor.split("class PortfolioPurchaseExplanationSensor", 1)[1].split(
        "\nclass ", 1
    )[0]
    assert "self.coordinator.plan_actionable" in explanation

    ready = binary.split("class PortfolioMonthlyPlanReady", 1)[1].split(
        "\nclass ", 1
    )[0]
    assert "self.coordinator.plan_actionable" in ready


def test_holdings_remain_informational_while_plan_values_are_gated() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    holding_block = sensor.split("class PortfolioHoldingValueSensor", 1)[1].split(
        "\nclass ", 1
    )[0]
    allocation_block = sensor.split("class PortfolioAllocationSensor", 1)[1].split(
        "\ndef _position_source_contributions", 1
    )[0]
    assert "plan_actionable" not in holding_block
    allocation_availability = allocation_block.split(
        "def available(self) -> bool:", 1
    )[1].split("def native_value", 1)[0]
    assert "plan_actionable" not in allocation_availability
    assert "_position_attributes(self.coordinator, position)" in allocation_block
    assert "_ACTIONABLE_POSITION_ATTRIBUTE_KEYS" in sensor
    for key in (
        "proposed_buy_eur",
        "estimated_fee_eur",
        "estimated_cash_outlay_eur",
        "recommendation_reason",
    ):
        assert f'"{key}"' in sensor

    # The readiness entity must not leak stale recommendation totals through
    # attributes when it is deliberately non-actionable.
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    ready = binary.split("class PortfolioMonthlyPlanReady", 1)[1].split(
        "\nclass ", 1
    )[0]
    assert "if self.coordinator.plan_actionable:" in ready
    assert '"recommended_total_eur"' in ready

    overview = (COMPONENT / "allocation_overview.py").read_text(encoding="utf-8")
    assert "include_actionable: bool = True" in overview
    assert "if include_actionable:" in overview
    overview_sensor = sensor.split("class PortfolioAllocationOverviewSensor", 1)[1].split(
        "\nclass ", 1
    )[0]
    assert "include_actionable=self.coordinator.plan_actionable" in overview_sensor

    isin_sensor = sensor.split("class PortfolioInstrumentIsinSensor", 1)[1].split(
        "\nclass ", 1
    )[0]
    assert "if self.coordinator.plan_actionable:" in isin_sensor
    assert 'attributes["proposed_buy_eur"]' in isin_sensor


def test_time_derived_gateway_entities_tick_locally() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    assert "class PortfolioGatewaySnapshotAgeSensor(\n    _MinuteTickEntity," in sensor
    assert "class PortfolioGatewaySnapshotExpiresInSensor(\n    _MinuteTickEntity," in sensor
    assert '"overdue_evidence_current"' in sensor


def test_ai_assistance_is_disclosed_without_claiming_ohf_compliance() -> None:
    policy = (ROOT / "AI_POLICY.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "generative AI" in policy
    assert "not claim compliance" in policy
    assert "Open Home Foundation" in policy
    assert "autonom" in policy.lower()
    assert "AI-assisted development" in readme
    assert "AI_POLICY.md" in readme
    assert "AI_POLICY.md" in contributing


def test_v1200_version_and_schema_compatibility() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    app = yaml.safe_load((APP / "config.yaml").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.33.1"
    assert app["version"] == "1.33.1"
    assert app["stage"] == "stable"
    # Resilience is integration-side; wire schemas stay backward compatible.
    init_source = (ROOT / "custom_components" / "portfolio_architect" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert "schema version 9" in init_source
    transport = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    assert '"requested_health_schema_version": 6' in transport
