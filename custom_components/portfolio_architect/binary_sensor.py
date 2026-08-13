"""Portfolio Architect binary sensors."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, SOURCE_TYPE_REST_API, VERSION
from .coordinator import PortfolioArchitectCoordinator
from .model import PositionData

FRESHNESS_TICK = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Portfolio Architect binary sensors."""
    coordinator: PortfolioArchitectCoordinator = entry.runtime_data
    static_entities: list[BinarySensorEntity] = [
            PortfolioTargetArchitectureComplete(coordinator, entry),
            PortfolioMonthlyPlanReady(coordinator, entry),
            PortfolioPlanReviewDue(coordinator, entry),
            PortfolioReviewScheduleConfigured(coordinator, entry),
            PortfolioAllocationOnTarget(coordinator, entry),
            PortfolioMandatoryControlsCompliant(coordinator, entry),
            PortfolioExceptionReviewOverdue(coordinator, entry),
            PortfolioSourceHealthy(coordinator, entry),
            PortfolioDataFresh(coordinator, entry),
        ]
    if coordinator.source_type == SOURCE_TYPE_REST_API:
        static_entities.extend(
            [
                PortfolioGatewayReauthenticationRequired(coordinator, entry),
                PortfolioGatewayUsingLastKnownGoodSnapshot(coordinator, entry),
                PortfolioGatewayRefreshInProgress(coordinator, entry),
                PortfolioGatewayRefreshOverdue(coordinator, entry),
                PortfolioGatewayAttentionRequired(coordinator, entry),
                PortfolioGatewaySnapshotIntegrityVerified(coordinator, entry),
            ]
        )
    async_add_entities(static_entities)

    known: set[str] = set()

    @callback
    def _add_missing_entities() -> None:
        if coordinator.data is None:
            return
        entities: list[PortfolioTargetPositionHeld] = []
        for fund_id, position in coordinator.data.positions.items():
            if not position.is_target_position or fund_id in known:
                continue
            known.add(fund_id)
            entities.append(
                PortfolioTargetPositionHeld(
                    coordinator=coordinator,
                    entry=entry,
                    fund_id=fund_id,
                )
            )
        if entities:
            async_add_entities(entities)

    _add_missing_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_missing_entities))


class _FreshnessTickEntity:
    """Refresh a time-derived entity without polling the source."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._handle_freshness_tick,
                FRESHNESS_TICK,
            )
        )

    @callback
    def _handle_freshness_tick(self, _now: datetime) -> None:
        self.async_write_ha_state()


class PortfolioTargetArchitectureComplete(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether every positive-weight target position is held."""

    _attr_has_entity_name = True
    _attr_translation_key = "target_architecture_complete"

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="target_architecture_complete")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_target_architecture_complete"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "target_architecture_complete"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.coverage.complete if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes = _source_attributes(self.coordinator)
        if not self.available:
            return attributes
        return {**self.coordinator.data.coverage.attributes, **attributes}


class PortfolioMonthlyPlanReady(
    _FreshnessTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    BinarySensorEntity,
):
    """Whether the monthly plan is fully allocated and fresh."""

    _attr_has_entity_name = True
    _attr_translation_key = "monthly_plan_ready"

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="monthly_plan_ready")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_monthly_plan_ready"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "monthly_plan_ready"

    @property
    def is_on(self) -> bool | None:
        if not self.available:
            return None
        return (
            self.coordinator.data.monthly_plan.ready
            and self.coordinator.plan_actionable
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        plan = self.coordinator.data.monthly_plan
        attributes = {
            "contribution_per_execution_eur": plan.contribution_per_execution_eur,
            "plan_budget_amount_eur": plan.budget_amount_eur,
            "plan_budget_basis": plan.budget_basis,
            "plan_frequency": plan.frequency,
            "scheduled_executions_per_period": plan.executions_per_period,
            "data_fresh": self.coordinator.is_data_fresh(),
            "plan_actionable": self.coordinator.plan_actionable,
            "actionability_reason": self.coordinator.plan_actionability_reason,
            "freshness_mode": self.coordinator.freshness_mode,
            **base,
        }
        if self.coordinator.plan_actionable:
            attributes.update({
                "recommended_total_eur": plan.recommended_total_eur,
                "unallocated_contribution_eur": plan.unallocated_contribution_eur,
                "purchase_count": plan.purchase_count,
            })
        return attributes


class PortfolioReviewScheduleConfigured(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether a recurring execution schedule is configured."""

    _attr_has_entity_name = True
    _attr_translation_key = "review_schedule_configured"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="review_schedule_configured")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_review_schedule_configured"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "review_schedule_configured"

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.review_schedule_configured

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        schedule = self.coordinator.schedule_config
        return {
            "frequency": schedule.frequency if schedule else None,
            "execution_days": list(schedule.execution_days) if schedule else [],
            "execution_month": schedule.execution_month if schedule else None,
            "execution_month_offset": (
                schedule.execution_month_offset if schedule else None
            ),
            "executions_per_period": (
                schedule.executions_per_period if schedule else 0
            ),
            "review_lead_days": self.coordinator.review_lead_days,
        }


class PortfolioPlanReviewDue(
    _FreshnessTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    BinarySensorEntity,
):
    """Whether a fresh recurring portfolio evaluation is due."""

    _attr_has_entity_name = True
    _attr_translation_key = "plan_review_due"

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="plan_review_due")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_plan_review_due"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "plan_review_due"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.plan_review_schedule() is not None

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.is_plan_review_due() if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        schedule = self.coordinator.plan_review_schedule()
        if schedule is None:
            return base
        return {
            "evaluated_on": schedule.evaluated_on.isoformat(),
            "next_review_on": schedule.next_review_on.isoformat(),
            "review_for_execution_on": schedule.review_for_execution_on.isoformat(),
            "frequency": schedule.frequency,
            "execution_days": list(self.coordinator.plan_execution_days),
            "executions_per_period": schedule.executions_per_period,
            "review_lead_days": self.coordinator.review_lead_days,
            **base,
        }


class PortfolioAllocationOnTarget(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether every tracked position is inside its allocation corridor."""

    _attr_has_entity_name = True
    _attr_translation_key = "portfolio_allocation_on_target"

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="portfolio_allocation_on_target")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_portfolio_allocation_on_target"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "portfolio_allocation_on_target"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.allocation.allocation_on_target if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        allocation = self.coordinator.data.allocation
        return {
            "portfolio_value_eur": allocation.portfolio_value_eur,
            "allocation_corridor_pp": allocation.corridor_pp,
            "underweight_positions": allocation.underweight,
            "on_target_positions": allocation.on_target,
            "overweight_positions": allocation.overweight,
            **base,
        }


class PortfolioMandatoryControlsCompliant(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether no unresolved error- or warning-level policy finding remains."""

    _attr_has_entity_name = True
    _attr_translation_key = "mandatory_controls_compliant"

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="mandatory_controls_compliant")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_mandatory_controls_compliant"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "mandatory_controls_compliant"

    @property
    def is_on(self) -> bool | None:
        if not self.available:
            return None
        return self.coordinator.data.policy.mandatory_controls_compliant

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        policy = self.coordinator.data.policy
        return {
            "error_findings": policy.errors,
            "warning_findings": policy.warnings,
            "accepted_exceptions": policy.accepted_exceptions,
            "optimisation_opportunities": policy.opportunities,
            **base,
        }


class PortfolioExceptionReviewOverdue(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether one or more accepted exception reviews are overdue."""

    _attr_has_entity_name = True
    _attr_translation_key = "exception_review_overdue"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="exception_review_overdue")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_exception_review_overdue"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "exception_review_overdue"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.policy.review_overdue if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        policy = self.coordinator.data.policy
        return {
            "overdue_reviews": policy.overdue_reviews,
            "oldest_overdue_review_on": (
                policy.oldest_overdue_review_on.isoformat()
                if policy.oldest_overdue_review_on
                else None
            ),
            "next_exception_review_on": (
                policy.next_exception_review_on.isoformat()
                if policy.next_exception_review_on
                else None
            ),
            **base,
        }


class PortfolioSourceHealthy(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether the configured portfolio source was processed successfully."""

    _attr_has_entity_name = True
    _attr_translation_key = "source_healthy"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="source_healthy")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_source_healthy"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "source_healthy"

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        if self.coordinator.source_type == SOURCE_TYPE_REST_API:
            health = self.coordinator.gateway_health
            return (
                self.coordinator.last_update_success
                and health is not None
                and health.status == "ok"
                and not health.reauthentication_required
                and not self.coordinator.using_home_assistant_last_known_good
                and self.coordinator.rest_snapshot_integrity_error is None
                and self.coordinator.gateway_operating_mode == "live"
            )
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            **_source_attributes(self.coordinator),
            "last_error": (
                None
                if self.coordinator.last_update_success
                else str(self.coordinator.last_exception)
            ),
        }


class PortfolioGatewayReauthenticationRequired(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether the Gateway App requires another interactive PhotoTAN bootstrap."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_reauthentication_required"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_reauthentication_required")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_reauthentication_required"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_reauthentication_required"

    @property
    def available(self) -> bool:
        return self.coordinator.gateway_health is not None

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.gateway_reauthentication_required if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "gateway_status": health.status if health else None,
            "last_error": health.last_error if health else None,
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayUsingLastKnownGoodSnapshot(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether PA is using a valid Gateway or Home Assistant cached snapshot."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_using_last_known_good_snapshot"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_using_last_known_good_snapshot")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_using_last_known_good_snapshot"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_using_last_known_good_snapshot"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_using_last_known_good_snapshot is not None
        )

    @property
    def is_on(self) -> bool | None:
        return (
            self.coordinator.gateway_using_last_known_good_snapshot
            if self.available
            else None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "operating_mode": self.coordinator.gateway_operating_mode,
            "home_assistant_cache_active": (
                self.coordinator.using_home_assistant_last_known_good
            ),
            "consecutive_refresh_failures": (
                self.coordinator.gateway_consecutive_refresh_failures
            ),
            "snapshot_age_seconds": (
                self.coordinator.gateway_snapshot_age_seconds
            ),
            "snapshot_expires_in_seconds": (
                self.coordinator.gateway_snapshot_expires_in_seconds
            ),
            "last_error": (
                health.last_error if health else self.coordinator.gateway_health_error
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayRefreshInProgress(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether the Gateway currently has a live refresh in progress."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_refresh_in_progress"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_refresh_in_progress")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_refresh_in_progress"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_refresh_in_progress"

    @property
    def available(self) -> bool:
        return (
            self.coordinator.gateway_health is not None
            and self.coordinator.gateway_refresh_in_progress is not None
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.gateway_refresh_in_progress if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "last_refresh_attempt": (
                health.last_refresh_attempt.isoformat()
                if health and health.last_refresh_attempt
                else None
            ),
            "last_refresh_trigger": (
                health.last_refresh_trigger if health else None
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayRefreshOverdue(
    _FreshnessTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    BinarySensorEntity,
):
    """Whether the Gateway missed its fixed-cadence refresh deadline."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_refresh_overdue"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_refresh_overdue")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_refresh_overdue"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_refresh_overdue"

    @property
    def available(self) -> bool:
        return self.coordinator.is_gateway_refresh_overdue() is not None

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.is_gateway_refresh_overdue()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "next_refresh_due_at": (
                health.next_refresh_due_at.isoformat()
                if health and health.next_refresh_due_at
                else None
            ),
            "poll_interval_seconds": health.poll_interval_seconds if health else None,
            "refresh_in_progress": health.refresh_in_progress if health else None,
            "health_observed_at": _isoformat(
                self.coordinator.gateway_health_observed_at
            ),
            "overdue_evidence_current": (
                self.coordinator.gateway_refresh_overdue_evidence_current
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayAttentionRequired(
    _FreshnessTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    BinarySensorEntity,
):
    """Consolidated live-source attention state suitable for automations."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_attention_required"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_attention_required")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_attention_required"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_attention_required"

    @property
    def available(self) -> bool:
        return self.coordinator.gateway_attention_required is not None

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.gateway_attention_required

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "attention_reason": self.coordinator.gateway_attention_reason,
            "recommended_action": self.coordinator.gateway_recommended_action,
            "last_refresh_failure_class": (
                self.coordinator.gateway_last_refresh_failure_class
            ),
            "consecutive_refresh_failures": (
                self.coordinator.gateway_consecutive_refresh_failures
            ),
            "retry_after_seconds": health.retry_after_seconds if health else None,
            "home_assistant_cache_active": (
                self.coordinator.using_home_assistant_last_known_good
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewaySnapshotIntegrityVerified(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether Gateway transport metadata verified the accepted snapshot."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_snapshot_integrity_verified"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_snapshot_integrity_verified")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_snapshot_integrity_verified"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_snapshot_integrity_verified"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.rest_snapshot_integrity_verified is not None
        )

    @property
    def is_on(self) -> bool | None:
        return (
            self.coordinator.rest_snapshot_integrity_verified
            if self.available
            else None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "snapshot_sha256": self.coordinator.rest_snapshot_sha256,
            "position_count": self.coordinator.rest_snapshot_position_count,
            "snapshot_generated_at": (
                self.coordinator.gateway_snapshot_generated_at.isoformat()
                if self.coordinator.gateway_snapshot_generated_at
                else None
            ),
            "health_schema_version": (
                health.health_schema_version if health else None
            ),
            "last_integrity_error": (
                self.coordinator.rest_snapshot_integrity_error
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioDataFresh(
    _FreshnessTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    BinarySensorEntity,
):
    """Whether the accepted snapshot is within its configured freshness window."""

    _attr_has_entity_name = True
    _attr_translation_key = "data_fresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="data_fresh")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_data_fresh"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "data_fresh"

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.is_data_fresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        schedule = self.coordinator.plan_review_schedule()
        return {
            "freshness_mode": self.coordinator.freshness_mode,
            "freshness_threshold_hours": self.coordinator.freshness_hours,
            "fresh_through": (
                schedule.next_review_on.isoformat() if schedule else None
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioTargetPositionHeld(
    CoordinatorEntity[PortfolioArchitectCoordinator], BinarySensorEntity
):
    """Whether one positive-weight target ETF is currently held."""

    _attr_has_entity_name = True
    _attr_translation_key = "target_position_held"

    def __init__(
        self,
        coordinator: PortfolioArchitectCoordinator,
        entry: ConfigEntry,
        fund_id: str,
    ) -> None:
        super().__init__(coordinator, context=f"{fund_id}:target_position_held")
        self._fund_id = fund_id
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{fund_id}_target_position_held"
        self._attr_translation_placeholders = {"fund_name": self._position.name}
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_target_position_held"

    @property
    def _position(self) -> PositionData:
        return self.coordinator.data.positions[self._fund_id]

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._fund_id in self.coordinator.data.positions
            and self._position.is_target_position
        )

    @property
    def is_on(self) -> bool | None:
        return self._position.is_held if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        position = self._position
        return {
            "fund_id": position.fund_id,
            "wkn": position.wkn,
            "isin": position.isin,
            "fund_name": position.name,
            "current_value_eur": position.current_value_eur,
            "current_pct": position.current_pct,
            "target_pct": position.target_pct,
            **base,
        }


def _device_info(source_key: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, source_key)},
        name=NAME,
        manufacturer="Portfolio Architect",
        model="Local portfolio analysis service",
        sw_version=VERSION,
        entry_type=DeviceEntryType.SERVICE,
    )


def _source_attributes(coordinator: PortfolioArchitectCoordinator) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "source_type": coordinator.source_type,
        "source_provider": coordinator.source_provider,
        "source": coordinator.source_label,
        "source_count": coordinator.source_count,
        "source_conflict_count": coordinator.source_conflict_count,
        "configuration_directory": coordinator.configuration_label,
        "source_last_changed": _isoformat(coordinator.source_last_changed),
        "source_last_updated": _isoformat(coordinator.source_last_updated),
        "last_successful_refresh": _isoformat(coordinator.data_timestamp),
        "data_fresh": coordinator.is_data_fresh(),
        "plan_actionable": coordinator.plan_actionable,
        "plan_actionability_reason": coordinator.plan_actionability_reason,
    }
    if coordinator.source_entity_id is not None:
        attributes["source_entity_id"] = coordinator.source_entity_id
    return attributes


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
