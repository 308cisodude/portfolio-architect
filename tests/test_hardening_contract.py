"""Static contract tests for Home Assistant integration hardening."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def test_config_entry_schema_migration_is_versioned() -> None:
    config_flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    setup = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "VERSION = 9" in config_flow
    assert "async def async_migrate_entry" in setup
    assert "version=5" in setup
    assert "entry.version < 8" in setup


def test_migration_uses_config_entry_scoped_registry_entries() -> None:
    source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "async_entries_for_config_entry(registry, entry.entry_id)" in source
    assert "plan_legacy_entity_id_migrations(entries)" in source
    assert "new_entity_id=migration.new_entity_id" in source


def test_post_setup_migration_safety_net_is_present() -> None:
    source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    setup_start = source.index("async def async_setup_entry")
    setup_source = source[setup_start:]
    forward = setup_source.index("async_forward_entry_setups")
    migrate = setup_source.index("_migrate_legacy_entity_ids(hass, entry)")
    assert migrate > forward


def test_legacy_source_state_changes_trigger_refresh() -> None:
    source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "async_track_state_change_event" in source
    assert "coordinator.async_request_refresh()" in source


def test_timestamp_coordinator_and_diagnostics_are_present() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    diagnostics = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
    assert "TimestampDataUpdateCoordinator" in coordinator
    assert "source_last_updated" in coordinator
    assert "async_get_config_entry_diagnostics" in diagnostics
    assert '"whole_portfolio_position_count"' in diagnostics
    assert '"last_successful_refresh"' in diagnostics


def test_display_precision_preserves_full_native_value() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    assert "_attr_suggested_display_precision = 2" in sensor
    assert "return position.current_pct" in sensor
    assert "round(position.current_pct" not in sensor


def test_target_sensor_does_not_duplicate_drift_attributes() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    assert "if self._kind is AllocationKind.TARGET" in sensor
    assert "return {**identity, **base}" in sensor


def test_native_coverage_entities_are_registered() -> None:
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    assert "Platform.BINARY_SENSOR" in const
    assert "PortfolioTargetCoverageSensor" in sensor
    assert "PortfolioTargetArchitectureComplete" in binary
    assert "PortfolioTargetPositionHeld" in binary


def test_coverage_is_derived_and_source_summary_is_cross_checked() -> None:
    model = (COMPONENT / "model.py").read_text(encoding="utf-8")
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    assert "calculate_target_coverage" in model
    assert "_validate_source_coverage" in model
    assert "parse_portfolio_data" in coordinator


def test_current_runtime_versions_are_aligned() -> None:
    import json

    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    engine_init = (COMPONENT / "engine" / "__init__.py").read_text(encoding="utf-8")
    assert manifest["version"] == "1.40.1"
    assert 'VERSION: Final = "1.40.1"' in const
    assert '__version__ = "1.40.1"' in engine_init


def test_native_monthly_plan_runtime_and_policy_entities_are_registered() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    for name in (
        "PortfolioMonthlyContributionSensor",
        "PortfolioRecommendedTotalSensor",
        "PortfolioUnallocatedContributionSensor",
        "PortfolioPurchaseCountSensor",
        "PortfolioProposedBuySensor",
        "PortfolioLastSuccessfulRefreshSensor",
        "PortfolioPayloadSchemaVersionSensor",
        "PortfolioVersionSensor",
    ):
        assert name in sensor
    for name in (
        "PortfolioMonthlyPlanReady", "PortfolioMandatoryControlsCompliant",
        "PortfolioSourceHealthy", "PortfolioDataFresh",
        "PortfolioAllocationOnTarget", "PortfolioExceptionReviewOverdue",
    ):
        assert name in binary
    for name in (
        "PortfolioPolicyStatusSensor", "PortfolioPolicyChecksSensor",
        "PortfolioPolicyErrorCountSensor", "PortfolioPolicyWarningCountSensor",
        "PortfolioAcceptedExceptionCountSensor",
        "PortfolioOptimisationOpportunityCountSensor",
        "PortfolioNextExceptionReviewSensor", "PortfolioPolicyFindingSensor",
        "PortfolioValueSensor", "PortfolioAllocationCorridorSensor",
        "PortfolioAllocationStatusSensor", "PortfolioAllocationDriftSensor",
        "PortfolioAllocationValueGapSensor",
        "PortfolioAllocationOverviewSensor",
        "PortfolioOverdueExceptionReviewCountSensor",
        "PortfolioOldestOverdueExceptionReviewSensor",
        "PortfolioLastExceptionDecisionSensor",
    ):
        assert name in sensor


def test_freshness_option_is_bounded_and_reloads() -> None:
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    assert "MIN_FRESHNESS_HOURS: Final = 1" in const
    assert "MAX_FRESHNESS_HOURS: Final = 168" in const
    assert "OptionsFlowWithReload" in flow
    assert "NumberSelectorMode.BOX" in flow


def test_integration_loads_degraded_to_expose_health_entities() -> None:
    setup = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    assert "await coordinator.async_refresh()" in setup
    assert "async_config_entry_first_refresh" not in setup
    assert "if coordinator.data is None" in sensor
    assert "if coordinator.data is None" in binary


def test_v12_plan_and_schedule_contract_is_native_and_fail_closed():
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    schedule = (COMPONENT / "schedule.py").read_text(encoding="utf-8")
    assert 'CONF_PLAN_OVERRIDE_ENABLED' in const
    assert 'CONF_PLAN_INSTRUMENTS' in const
    assert 'PLAN_FREQUENCY_WEEKLY' in const
    assert 'PLAN_FREQUENCY_YEARLY' in const
    assert 'async_step_plan' in flow
    assert 'async_step_plan_instrument' in flow
    assert 'SelectSelectorConfig' in flow
    assert 'validate_schedule_config' in flow
    assert 'plan_override=plan_override' in coordinator
    assert 'source_freshness_evidence' in coordinator
    assert 'plan_review_schedule' in coordinator
    assert 'review_schedule_configured' in coordinator
    assert 'PlanScheduleConfig' in schedule
    assert '_first_execution_in_next_period' in schedule


def test_v1182_removes_invalid_statistics_state_class_from_plan_money_entities() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")

    for class_name in (
        "PortfolioMonthlyContributionSensor",
        "PortfolioRecommendedTotalSensor",
        "PortfolioUnallocatedContributionSensor",
        "PortfolioProposedBuySensor",
    ):
        start = sensor.index(f"class {class_name}")
        next_class = sensor.find("\nclass ", start + 1)
        class_source = sensor[start: next_class if next_class != -1 else None]
        assert "_attr_state_class" not in class_source

    # Monetary entities remain monetary; only the invalid statistics classification
    # is removed. The dedicated v1.19.0 metadata contract checks all subclasses.
    assert "_attr_device_class = SensorDeviceClass.MONETARY" in sensor
