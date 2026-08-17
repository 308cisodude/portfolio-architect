"""Portfolio Architect numeric and runtime sensors."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL, PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    NAME,
    PLAN_BUDGET_BASES,
    PLAN_FREQUENCIES,
    SOURCE_TYPE_REST_API,
    VERSION,
)
from .allocation_overview import allocation_overview_state, build_allocation_overview
from .decision_trace import PLAN_CHANGE_STATES
from .coordinator import PortfolioArchitectCoordinator
from .engine.aggregation import PROVIDER_MULTI_SOURCE
from .engine.importers import PROVIDER_COMDIRECT, PROVIDER_DKB, PROVIDER_GENERIC_CSV
from .engine.rest import PROVIDER_LOCAL_REST_JSON
from .execution_semantics import PLAN_ACTIONABILITY_STATES, derive_plan_actionability
from .model import HoldingData, PolicyFindingData, PositionData
from .presentation import (
    display_count_de,
    display_datetime_de,
    display_eur_de,
    display_state_de,
)

CURRENCY_EUR = "EUR"
REFRESH_SCHEDULE_TICK = timedelta(minutes=1)


class AllocationKind(StrEnum):
    """Allocation sensor variants."""

    CURRENT = "current"
    TARGET = "target"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Portfolio Architect sensors."""
    coordinator: PortfolioArchitectCoordinator = entry.runtime_data
    static_entities: list[SensorEntity] = [
            PortfolioTargetCoverageSensor(coordinator, entry),
            PortfolioValueSensor(coordinator, entry),
            PortfolioCurrentPlanValueSensor(coordinator, entry),
            PortfolioOutsideScopeValueSensor(coordinator, entry),
            PortfolioCurrentPlanShareSensor(coordinator, entry),
            PortfolioOutsideScopeShareSensor(coordinator, entry),
            PortfolioWholePositionCountSensor(coordinator, entry),
            PortfolioOutsideScopePositionCountSensor(coordinator, entry),
            PortfolioAllocationCorridorSensor(coordinator, entry),
            PortfolioUnderweightCountSensor(coordinator, entry),
            PortfolioOnTargetCountSensor(coordinator, entry),
            PortfolioOverweightCountSensor(coordinator, entry),
            PortfolioAllocationOverviewSensor(coordinator, entry),
            PortfolioPlanChangeSensor(coordinator, entry),
            PortfolioPlanBudgetSensor(coordinator, entry),
            PortfolioPlanFrequencySensor(coordinator, entry),
            PortfolioPlanBudgetBasisSensor(coordinator, entry),
            PortfolioExecutionsPerPeriodSensor(coordinator, entry),
            PortfolioMonthlyContributionSensor(coordinator, entry),
            PortfolioRecommendedTotalSensor(coordinator, entry),
            PortfolioUnallocatedContributionSensor(coordinator, entry),
            PortfolioAvailableInvestmentReserveSensor(coordinator, entry),
            PortfolioRemainingInvestmentReserveSensor(coordinator, entry),
            PortfolioDeferredContributionSensor(coordinator, entry),
            PortfolioEstimatedTransactionFeesSensor(coordinator, entry),
            PortfolioEstimatedCashOutlaySensor(coordinator, entry),
            PortfolioExecutionPolicySensor(coordinator, entry),
            PortfolioExecutionStateSensor(coordinator, entry),
            PortfolioPlanActionabilitySensor(coordinator, entry),
            PortfolioAdditionalInvestmentCashRequiredSensor(coordinator, entry),
            PortfolioInvestmentReserveSourceSensor(coordinator, entry),
            PortfolioDeferredPurchaseCountSensor(coordinator, entry),
            PortfolioPurchaseCountSensor(coordinator, entry),
            PortfolioPlannedExecutionSensor(coordinator, entry),
            PortfolioPolicyStatusSensor(coordinator, entry),
            PortfolioPolicyChecksSensor(coordinator, entry),
            PortfolioPolicyErrorCountSensor(coordinator, entry),
            PortfolioPolicyWarningCountSensor(coordinator, entry),
            PortfolioAcceptedExceptionCountSensor(coordinator, entry),
            PortfolioExceptionReviewRequiredCountSensor(coordinator, entry),
            PortfolioOptimisationOpportunityCountSensor(coordinator, entry),
            PortfolioNextExceptionReviewSensor(coordinator, entry),
            PortfolioOverdueExceptionReviewCountSensor(coordinator, entry),
            PortfolioOldestOverdueExceptionReviewSensor(coordinator, entry),
            PortfolioLastExceptionDecisionSensor(coordinator, entry),
            PortfolioLastSuccessfulRefreshSensor(coordinator, entry),
            PortfolioNextPlanReviewSensor(coordinator, entry),
            PortfolioPayloadSchemaVersionSensor(coordinator, entry),
            PortfolioSourceProviderSensor(coordinator, entry),
            PortfolioSourceCountSensor(coordinator, entry),
            PortfolioSourceConflictCountSensor(coordinator, entry),
            PortfolioVersionSensor(coordinator, entry),
        ]
    if coordinator.source_type == SOURCE_TYPE_REST_API:
        static_entities.extend(
            [
                PortfolioGatewayStatusSensor(coordinator, entry),
                PortfolioGatewayOperatingModeSensor(coordinator, entry),
                PortfolioGatewayLastRefreshSensor(coordinator, entry),
                PortfolioGatewayNextRefreshSensor(coordinator, entry),
                PortfolioGatewayRefreshScheduleSensor(coordinator, entry),
                PortfolioGatewayLastRefreshDurationSensor(coordinator, entry),
                PortfolioGatewayLastRefreshTriggerSensor(coordinator, entry),
                PortfolioGatewayAttentionReasonSensor(coordinator, entry),
                PortfolioGatewayRecommendedActionSensor(coordinator, entry),
                PortfolioGatewayLastRefreshFailureSensor(coordinator, entry),
                PortfolioGatewaySnapshotGeneratedSensor(coordinator, entry),
                PortfolioGatewaySnapshotAgeSensor(coordinator, entry),
                PortfolioGatewaySnapshotExpiresInSensor(coordinator, entry),
                PortfolioGatewayConsecutiveRefreshFailuresSensor(coordinator, entry),
                PortfolioGatewayLastErrorSensor(coordinator, entry),
            ]
        )
    async_add_entities(static_entities)

    known_allocations: set[tuple[str, AllocationKind]] = set()
    known_holdings: set[str] = set()
    known_position_details: set[str] = set()
    known_explanation_details: set[str] = set()
    known_purchases: set[str] = set()
    known_identifiers: set[str] = set()
    known_policy_findings: set[str] = set()
    known_policy_exception_details: set[str] = set()
    known_policy_decision_details: set[str] = set()

    @callback
    def _add_missing_entities() -> None:
        if coordinator.data is None:
            return
        entities: list[SensorEntity] = []
        for fund_id, position in coordinator.data.positions.items():
            for kind in AllocationKind:
                key = (fund_id, kind)
                if key not in known_allocations:
                    known_allocations.add(key)
                    entities.append(
                        PortfolioAllocationSensor(
                            coordinator=coordinator,
                            entry=entry,
                            fund_id=fund_id,
                            kind=kind,
                        )
                    )
            if fund_id not in known_position_details:
                known_position_details.add(fund_id)
                entities.extend(
                    [
                        PortfolioAllocationStatusSensor(
                            coordinator=coordinator, entry=entry, fund_id=fund_id
                        ),
                        PortfolioAllocationDriftSensor(
                            coordinator=coordinator, entry=entry, fund_id=fund_id
                        ),
                        PortfolioAllocationValueGapSensor(
                            coordinator=coordinator, entry=entry, fund_id=fund_id
                        ),
                        PortfolioPositionSourcesSensor(
                            coordinator=coordinator, entry=entry, fund_id=fund_id
                        ),
                        PortfolioAllocationExplanationSensor(
                            coordinator=coordinator, entry=entry, fund_id=fund_id
                        ),
                        PortfolioPurchaseExplanationSensor(
                            coordinator=coordinator, entry=entry, fund_id=fund_id
                        ),
                    ]
                )
            if position.is_target_position and fund_id not in known_purchases:
                known_purchases.add(fund_id)
                entities.append(
                    PortfolioProposedBuySensor(
                        coordinator=coordinator,
                        entry=entry,
                        fund_id=fund_id,
                    )
                )
            if position.is_target_position and fund_id not in known_identifiers:
                known_identifiers.add(fund_id)
                entities.append(
                    PortfolioInstrumentIsinSensor(
                        coordinator=coordinator,
                        entry=entry,
                        fund_id=fund_id,
                    )
                )
        for position_id in coordinator.data.holdings:
            if position_id in known_holdings:
                continue
            known_holdings.add(position_id)
            entities.extend(
                [
                    PortfolioHoldingWholeAllocationSensor(
                        coordinator=coordinator, entry=entry, position_id=position_id
                    ),
                    PortfolioHoldingValueSensor(
                        coordinator=coordinator, entry=entry, position_id=position_id
                    ),
                    PortfolioHoldingQuantitySensor(
                        coordinator=coordinator, entry=entry, position_id=position_id
                    ),
                    PortfolioHoldingScopeSensor(
                        coordinator=coordinator, entry=entry, position_id=position_id
                    ),
                ]
            )
        for finding in coordinator.data.policy.non_pass_findings:
            if finding.key not in known_policy_findings:
                known_policy_findings.add(finding.key)
                entities.append(
                    PortfolioPolicyFindingSensor(
                        coordinator=coordinator,
                        entry=entry,
                        fund_id=finding.fund_id,
                        rule=finding.rule,
                    )
                )
            if finding.key not in known_policy_decision_details:
                known_policy_decision_details.add(finding.key)
                entities.append(
                    PortfolioPolicyDecisionDetailSensor(
                        coordinator=coordinator,
                        entry=entry,
                        fund_id=finding.fund_id,
                        rule=finding.rule,
                    )
                )
            if (
                finding.status in {"accepted_exception", "review_required"}
                and finding.key not in known_policy_exception_details
            ):
                known_policy_exception_details.add(finding.key)
                entities.append(
                    PortfolioPolicyExceptionDetailSensor(
                        coordinator=coordinator,
                        entry=entry,
                        fund_id=finding.fund_id,
                        rule=finding.rule,
                    )
                )
        if entities:
            async_add_entities(entities)

    _add_missing_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_missing_entities))


class PortfolioTargetCoverageSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Percentage of positive-weight target positions currently held."""

    _attr_has_entity_name = True
    _attr_translation_key = "target_position_coverage"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 2
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="target_position_coverage")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_target_position_coverage"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "target_position_coverage"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.coverage.coverage_pct if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes = _source_attributes(self.coordinator)
        if not self.available:
            return attributes
        return {**self.coordinator.data.coverage.attributes, **attributes}


class PortfolioValueSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Current total value of the tracked portfolio."""

    _attr_has_entity_name = True
    _attr_translation_key = "portfolio_value"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_EUR
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="portfolio_value")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_portfolio_value"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "portfolio_value"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.allocation.portfolio_value_eur if self.available else None



class _PortfolioScopeSummarySensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    field: str
    object_id: str

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context=self.object_id)
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{self.object_id}"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return self.object_id

    @property
    def native_value(self):
        if not self.available:
            return None
        return getattr(self.coordinator.data.allocation, self.field)


class PortfolioCurrentPlanValueSensor(_PortfolioScopeSummarySensor):
    _attr_translation_key = "current_plan_value"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_EUR
    _attr_suggested_display_precision = 2
    field = "current_plan_value_eur"
    object_id = "current_plan_value"


class PortfolioOutsideScopeValueSensor(_PortfolioScopeSummarySensor):
    _attr_translation_key = "outside_scope_value"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_EUR
    _attr_suggested_display_precision = 2
    field = "outside_scope_value_eur"
    object_id = "outside_scope_value"


class PortfolioCurrentPlanShareSensor(_PortfolioScopeSummarySensor):
    _attr_translation_key = "current_plan_share"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 2
    _attr_state_class = SensorStateClass.MEASUREMENT
    field = "current_plan_whole_portfolio_pct"
    object_id = "current_plan_share"


class PortfolioOutsideScopeShareSensor(_PortfolioScopeSummarySensor):
    _attr_translation_key = "outside_scope_share"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 2
    _attr_state_class = SensorStateClass.MEASUREMENT
    field = "outside_scope_whole_portfolio_pct"
    object_id = "outside_scope_share"


class PortfolioWholePositionCountSensor(_PortfolioScopeSummarySensor):
    _attr_translation_key = "whole_position_count"
    field = "whole_portfolio_position_count"
    object_id = "whole_position_count"


class PortfolioOutsideScopePositionCountSensor(_PortfolioScopeSummarySensor):
    _attr_translation_key = "outside_scope_position_count"
    field = "outside_scope_position_count"
    object_id = "outside_scope_position_count"


class PortfolioAllocationCorridorSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Configured allocation corridor in percentage points."""

    _attr_has_entity_name = True
    _attr_translation_key = "allocation_corridor"
    _attr_native_unit_of_measurement = "pp"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="allocation_corridor")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_allocation_corridor"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "allocation_corridor"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.allocation.corridor_pp if self.available else None


class _PortfolioAllocationCountSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Base class for allocation-state position counts."""

    _attr_has_entity_name = True
    value_attribute: str
    object_id: str

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context=self.object_id)
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{self.object_id}"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return self.object_id

    @property
    def native_value(self) -> int | None:
        if not self.available:
            return None
        return int(getattr(self.coordinator.data.allocation, self.value_attribute))


class PortfolioUnderweightCountSensor(_PortfolioAllocationCountSensor):
    _attr_translation_key = "underweight_position_count"
    value_attribute = "underweight"
    object_id = "underweight_position_count"


class PortfolioOnTargetCountSensor(_PortfolioAllocationCountSensor):
    _attr_translation_key = "on_target_position_count"
    value_attribute = "on_target"
    object_id = "on_target_position_count"


class PortfolioOverweightCountSensor(_PortfolioAllocationCountSensor):
    _attr_translation_key = "overweight_position_count"
    value_attribute = "overweight"
    object_id = "overweight_position_count"


class PortfolioAllocationOverviewSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Presentation-ready aggregate allocation and drift contract."""

    _attr_has_entity_name = True
    _attr_translation_key = "allocation_overview"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["on_target", "drift_detected"]

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="allocation_overview")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_allocation_overview"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "allocation_overview"

    @property
    def native_value(self) -> str | None:
        if not self.available or self.coordinator.data is None:
            return None
        return allocation_overview_state(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available or self.coordinator.data is None:
            return base
        return {
            **build_allocation_overview(
                self.coordinator.data,
                include_actionable=self.coordinator.plan_actionable,
            ),
            **base,
        }


class PortfolioPlanChangeSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Changes between the two most recent validated portfolio evaluations."""

    _attr_has_entity_name = True
    _attr_translation_key = "plan_change"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(PLAN_CHANGE_STATES)
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="plan_change")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_plan_change"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "plan_change"

    @property
    def native_value(self) -> str | None:
        if not self.available or self.coordinator.plan_delta is None:
            return None
        return self.coordinator.plan_delta.state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available or self.coordinator.plan_delta is None:
            return {
                "display_state_de": display_state_de(
                    "plan_change", None, available=False
                ),
                **base,
            }
        return {
            **self.coordinator.plan_delta.attributes,
            "display_state_de": display_state_de(
                "plan_change", self.coordinator.plan_delta.state
            ),
            **base,
        }


class _PortfolioMonthlyMoneySensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Base class for monthly monetary values."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_EUR
    _attr_suggested_display_precision = 2

    value_attribute: str
    object_id: str
    requires_actionable_source: bool = False

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context=self.object_id)
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{self.object_id}"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return self.object_id

    @property
    def available(self) -> bool:
        return super().available and (
            not self.requires_actionable_source or self.coordinator.plan_actionable
        )

    @property
    def native_value(self) -> float | None:
        if not self.available:
            return None
        return float(getattr(self.coordinator.data.monthly_plan, self.value_attribute))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "display_state_de": display_eur_de(
                self.native_value, available=self.available
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioPlanBudgetSensor(_PortfolioMonthlyMoneySensor):
    """Configured budget amount per period or per execution."""

    _attr_translation_key = "plan_budget"
    value_attribute = "budget_amount_eur"
    object_id = "plan_budget"


class PortfolioMonthlyContributionSensor(_PortfolioMonthlyMoneySensor):
    """Contribution allocated to the next individual execution."""

    _attr_translation_key = "contribution_per_execution"
    value_attribute = "contribution_per_execution_eur"
    object_id = "monthly_contribution"


class PortfolioRecommendedTotalSensor(_PortfolioMonthlyMoneySensor):
    requires_actionable_source = True
    _attr_translation_key = "recommended_total"
    value_attribute = "recommended_total_eur"
    object_id = "recommended_total"


class PortfolioUnallocatedContributionSensor(_PortfolioMonthlyMoneySensor):
    requires_actionable_source = True
    _attr_translation_key = "unallocated_contribution"
    value_attribute = "unallocated_contribution_eur"
    object_id = "unallocated_contribution"


class PortfolioAvailableInvestmentReserveSensor(_PortfolioMonthlyMoneySensor):
    """Cash Portfolio Architect is currently authorized to allocate."""

    requires_actionable_source = True

    _attr_translation_key = "available_investment_reserve"
    value_attribute = "available_reserve_eur"
    object_id = "available_investment_reserve"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = super().extra_state_attributes
        if not self.available:
            return base
        plan = self.coordinator.data.monthly_plan
        return {
            "reserve_source": plan.reserve_source,
            "reserve_as_of": plan.reserve_as_of.isoformat() if plan.reserve_as_of else None,
            "investment_account_balance_eur": plan.investment_account_balance_eur,
            "eligible_investment_cash_eur": plan.eligible_investment_cash_eur,
            "authorization_policy": plan.investment_cash_authorization_policy,
            "authorization_cap_eur": plan.investment_cash_authorization_cap_eur,
            **base,
        }


class PortfolioRemainingInvestmentReserveSensor(_PortfolioMonthlyMoneySensor):
    requires_actionable_source = True
    _attr_translation_key = "remaining_investment_reserve"
    value_attribute = "remaining_reserve_eur"
    object_id = "remaining_investment_reserve"


class PortfolioDeferredContributionSensor(_PortfolioMonthlyMoneySensor):
    requires_actionable_source = True
    _attr_translation_key = "deferred_contribution"
    value_attribute = "deferred_contribution_eur"
    object_id = "deferred_contribution"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = super().extra_state_attributes
        if not self.available:
            return base
        deferred = [
            {
                "fund_id": item.fund_id,
                "fund_name": item.name,
                "execution_route": item.execution_route,
                "execution_provider": item.execution_provider,
                "execution_provider_name": item.execution_provider_name,
                "estimated_fee_eur": item.estimated_fee_eur,
                "estimated_cash_outlay_eur": item.estimated_cash_outlay_eur,
                "estimated_cost_ratio_pct": item.estimated_cost_ratio_pct,
                "additional_reserve_required_eur": item.additional_reserve_required_eur,
                "reason_code": item.recommendation_reason,
            }
            for item in self.coordinator.data.positions.values()
            if item.deferred
        ]
        return {"deferred_purchases": deferred, **base}


class PortfolioEstimatedTransactionFeesSensor(_PortfolioMonthlyMoneySensor):
    requires_actionable_source = True
    _attr_translation_key = "estimated_transaction_fees"
    value_attribute = "estimated_transaction_fees_eur"
    object_id = "estimated_transaction_fees"


class PortfolioEstimatedCashOutlaySensor(_PortfolioMonthlyMoneySensor):
    requires_actionable_source = True
    _attr_translation_key = "estimated_cash_outlay"
    value_attribute = "estimated_cash_outlay_eur"
    object_id = "estimated_cash_outlay"


class PortfolioDeferredPurchaseCountSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    _attr_translation_key = "deferred_purchase_count"

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="deferred_purchase_count")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_deferred_purchase_count"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "deferred_purchase_count"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.plan_actionable

    @property
    def native_value(self) -> int | None:
        return (
            self.coordinator.data.monthly_plan.deferred_purchase_count
            if self.available
            else None
        )


class PortfolioPurchaseCountSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Number of non-zero purchases in the monthly plan."""

    _attr_has_entity_name = True
    _attr_translation_key = "purchase_count"

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="purchase_count")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_purchase_count"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "purchase_count"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.plan_actionable

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.monthly_plan.purchase_count if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "display_state_de": display_count_de(
                self.native_value, available=self.available
            ),
            **_source_attributes(self.coordinator),
        }


class _PortfolioPlanEnumSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Base class for translated plan configuration enum sensors."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    value_attribute: str
    object_id: str
    requires_actionable_source: bool = False

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context=self.object_id)
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{self.object_id}"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return self.object_id

    @property
    def available(self) -> bool:
        return super().available and (
            not self.requires_actionable_source or self.coordinator.plan_actionable
        )

    @property
    def native_value(self) -> str | None:
        if not self.available:
            return None
        return str(getattr(self.coordinator.data.monthly_plan, self.value_attribute))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "display_state_de": display_state_de(
                self.object_id, self.native_value, available=self.available
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioPlanFrequencySensor(_PortfolioPlanEnumSensor):
    """Configured recurring plan frequency."""

    _attr_translation_key = "plan_frequency"
    _attr_options = list(PLAN_FREQUENCIES)
    value_attribute = "frequency"
    object_id = "plan_frequency"


class PortfolioPlanBudgetBasisSensor(_PortfolioPlanEnumSensor):
    """Whether the configured budget applies per period or execution."""

    _attr_translation_key = "plan_budget_basis"
    _attr_options = list(PLAN_BUDGET_BASES)
    value_attribute = "budget_basis"
    object_id = "plan_budget_basis"


class PortfolioExecutionPolicySensor(_PortfolioPlanEnumSensor):
    _attr_translation_key = "execution_policy"
    _attr_options = [
        "legacy_distribution",
        "monthly_continuity",
        "balanced",
        "efficiency_first",
    ]
    value_attribute = "execution_policy"
    object_id = "execution_policy"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = super().extra_state_attributes
        if not self.available:
            return base
        plan = self.coordinator.data.monthly_plan
        return {
            "max_cost_ratio_pct": plan.max_cost_ratio_pct,
            "max_orders_per_execution": plan.max_orders_per_execution,
            "max_deferral_periods": plan.max_deferral_periods,
            **base,
        }


class PortfolioExecutionStateSensor(_PortfolioPlanEnumSensor):
    """Operational state of the next investment-plan execution."""

    requires_actionable_source = True

    _attr_translation_key = "execution_state"
    _attr_options = [
        "ready",
        "waiting_for_reserve",
        "deferred_for_cost_efficiency",
        "no_eligible_purchase",
        "reserve_unavailable",
    ]
    value_attribute = "execution_state"
    object_id = "execution_state"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        plan = self.coordinator.data.monthly_plan
        return {
            "execution_policy": plan.execution_policy,
            "purchase_count": plan.purchase_count,
            "deferred_purchase_count": plan.deferred_purchase_count,
            "available_investment_cash_eur": plan.available_reserve_eur,
            "cash_after_recommended_purchases_eur": plan.remaining_reserve_eur,
            "additional_investment_cash_required_eur": (
                plan.additional_investment_cash_required_eur
            ),
            "reserve_source": plan.reserve_source,
            **base,
        }


class PortfolioAdditionalInvestmentCashRequiredSensor(_PortfolioMonthlyMoneySensor):
    """Additional cash required before the next eligible execution."""

    requires_actionable_source = True

    _attr_translation_key = "additional_investment_cash_required"
    value_attribute = "additional_investment_cash_required_eur"
    object_id = "additional_investment_cash_required"


class PortfolioInvestmentReserveSourceSensor(_PortfolioPlanEnumSensor):
    requires_actionable_source = True
    _attr_translation_key = "investment_reserve_source"
    _attr_options = ["contribution", "gateway_balance", "unavailable"]
    value_attribute = "reserve_source"
    object_id = "investment_reserve_source"


class PortfolioExecutionsPerPeriodSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Number of scheduled executions inside one plan period."""

    _attr_has_entity_name = True
    _attr_translation_key = "executions_per_period"

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="executions_per_period")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_executions_per_period"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "executions_per_period"

    @property
    def native_value(self) -> int | None:
        if not self.available:
            return None
        return self.coordinator.data.monthly_plan.executions_per_period

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.available:
            return _source_attributes(self.coordinator)
        plan = self.coordinator.data.monthly_plan
        return {
            "plan_name": plan.name,
            "configuration_source": plan.configuration_source,
            **_source_attributes(self.coordinator),
        }


class PortfolioPolicyStatusSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Overall policy state derived from validated policy findings."""

    _attr_has_entity_name = True
    _attr_translation_key = "policy_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["compliant", "attention", "non_compliant"]

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="policy_status")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_policy_status"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "policy_status"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.policy.status if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        policy = self.coordinator.data.policy
        return {
            "checks_evaluated": policy.checks_evaluated,
            "error_findings": policy.errors,
            "warning_findings": policy.warnings,
            "accepted_exceptions": policy.accepted_exceptions,
            "exception_reviews_required": policy.exception_reviews_required,
            "optimisation_opportunities": policy.opportunities,
            "mandatory_controls_compliant": policy.mandatory_controls_compliant,
            **base,
        }


class _PortfolioPolicyCountSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Base class for bounded policy summary counts."""

    _attr_has_entity_name = True
    value_attribute: str
    object_id: str

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context=self.object_id)
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{self.object_id}"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return self.object_id

    @property
    def native_value(self) -> int | None:
        if not self.available:
            return None
        return int(getattr(self.coordinator.data.policy, self.value_attribute))


class PortfolioPolicyChecksSensor(_PortfolioPolicyCountSensor):
    _attr_translation_key = "policy_checks_evaluated"
    value_attribute = "checks_evaluated"
    object_id = "policy_checks_evaluated"


class PortfolioPolicyErrorCountSensor(_PortfolioPolicyCountSensor):
    _attr_translation_key = "policy_error_findings"
    value_attribute = "errors"
    object_id = "policy_error_findings"


class PortfolioPolicyWarningCountSensor(_PortfolioPolicyCountSensor):
    _attr_translation_key = "policy_warning_findings"
    value_attribute = "warnings"
    object_id = "policy_warning_findings"


class PortfolioAcceptedExceptionCountSensor(_PortfolioPolicyCountSensor):
    _attr_translation_key = "accepted_exception_count"
    value_attribute = "accepted_exceptions"
    object_id = "accepted_exception_count"


class PortfolioExceptionReviewRequiredCountSensor(_PortfolioPolicyCountSensor):
    _attr_translation_key = "exception_review_required_count"
    value_attribute = "exception_reviews_required"
    object_id = "exception_review_required_count"


class PortfolioOptimisationOpportunityCountSensor(_PortfolioPolicyCountSensor):
    _attr_translation_key = "optimisation_opportunity_count"
    value_attribute = "opportunities"
    object_id = "optimisation_opportunity_count"


class PortfolioNextExceptionReviewSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Earliest scheduled review date among accepted policy exceptions."""

    _attr_has_entity_name = True
    _attr_translation_key = "next_exception_review"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="next_exception_review")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_next_exception_review"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "next_exception_review"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.policy.next_exception_review_on is not None

    @property
    def native_value(self) -> date | None:
        return self.coordinator.data.policy.next_exception_review_on if self.available else None


class PortfolioOverdueExceptionReviewCountSensor(_PortfolioPolicyCountSensor):
    _attr_translation_key = "overdue_exception_review_count"
    value_attribute = "overdue_reviews"
    object_id = "overdue_exception_review_count"


class _PortfolioPolicyDateSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Base class for optional policy-governance dates."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATE
    value_attribute: str
    object_id: str

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context=self.object_id)
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{self.object_id}"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return self.object_id

    @property
    def available(self) -> bool:
        return (
            super().available
            and getattr(self.coordinator.data.policy, self.value_attribute) is not None
        )

    @property
    def native_value(self) -> date | None:
        return getattr(self.coordinator.data.policy, self.value_attribute) if self.available else None


class PortfolioOldestOverdueExceptionReviewSensor(_PortfolioPolicyDateSensor):
    _attr_translation_key = "oldest_overdue_exception_review"
    value_attribute = "oldest_overdue_review_on"
    object_id = "oldest_overdue_exception_review"


class PortfolioLastExceptionDecisionSensor(_PortfolioPolicyDateSensor):
    _attr_translation_key = "last_exception_decision"
    value_attribute = "last_exception_decision_on"
    object_id = "last_exception_decision"


class PortfolioPolicyFindingSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """One active non-pass policy finding as a native enum sensor."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["error", "warning", "accepted_exception", "review_required", "opportunity"]

    def __init__(
        self,
        coordinator: PortfolioArchitectCoordinator,
        entry: ConfigEntry,
        fund_id: str,
        rule: str,
    ) -> None:
        super().__init__(coordinator, context=f"{fund_id}:{rule}:policy_finding")
        self._fund_id = fund_id
        self._rule = rule
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{fund_id}_{rule}_policy_finding"
        self._attr_translation_key = f"policy_finding_{rule}"
        self._attr_translation_placeholders = {"fund_name": self._finding.fund_name}
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_{self._rule}_policy_finding"

    @property
    def _key(self) -> str:
        return f"{self._fund_id}:{self._rule}"

    @property
    def _finding(self) -> PolicyFindingData:
        return self.coordinator.data.policy.findings[self._key]

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._key in self.coordinator.data.policy.findings
            and self._finding.non_pass
        )

    @property
    def native_value(self) -> str | None:
        return self._finding.entity_state if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        return {**self._finding.attributes, **base}


class PortfolioPolicyDecisionDetailSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Bounded native explanation for one active policy decision."""

    _attr_has_entity_name = True
    _attr_translation_key = "policy_decision_detail"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["error", "warning", "opportunity", "accepted_exception", "review_required"]

    def __init__(self, coordinator, entry, fund_id, rule):
        super().__init__(coordinator, context=f"{fund_id}:{rule}:policy_decision")
        self._fund_id = fund_id
        self._rule = rule
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{fund_id}_{rule}_policy_decision"
        self._attr_translation_placeholders = {"fund_name": self._finding.fund_name}
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_{self._rule}_policy_decision"

    @property
    def _key(self) -> str:
        return f"{self._fund_id}:{self._rule}"

    @property
    def _finding(self) -> PolicyFindingData:
        return self.coordinator.data.policy.findings[self._key]

    @property
    def available(self) -> bool:
        return super().available and self._key in self.coordinator.data.policy.findings and self._finding.non_pass

    @property
    def native_value(self) -> str | None:
        return self._finding.entity_state if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        f = self._finding
        attrs = {
            "fund_name": f.fund_name,
            "rule": f.rule,
            "severity": f.severity,
            "observed": f.attributes.get("observed"),
            "expected": f.attributes.get("expected"),
            "reason_code": f"policy_{f.entity_state}",
        }
        if f.status in {"accepted_exception", "review_required"}:
            attrs.update(f.exception_detail_attributes)
        return {**attrs, **base}


class PortfolioPolicyExceptionDetailSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Bounded native detail view for one accepted policy exception."""

    _attr_has_entity_name = True
    _attr_translation_key = "policy_exception_detail"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["accepted_exception", "review_required"]

    def __init__(
        self,
        coordinator: PortfolioArchitectCoordinator,
        entry: ConfigEntry,
        fund_id: str,
        rule: str,
    ) -> None:
        super().__init__(coordinator, context=f"{fund_id}:{rule}:policy_exception")
        self._fund_id = fund_id
        self._rule = rule
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{fund_id}_{rule}_policy_exception"
        self._attr_translation_placeholders = {"fund_name": self._finding.fund_name}
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_{self._rule}_policy_exception"

    @property
    def _key(self) -> str:
        return f"{self._fund_id}:{self._rule}"

    @property
    def _finding(self) -> PolicyFindingData:
        return self.coordinator.data.policy.findings[self._key]

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._key in self.coordinator.data.policy.findings
            and self._finding.status in {"accepted_exception", "review_required"}
        )

    @property
    def native_value(self) -> str | None:
        return self._finding.status if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        return {**self._finding.exception_detail_attributes, **base}


class _PortfolioPositionDetailSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Base class for native per-position allocation details."""

    def __init__(
        self,
        coordinator: PortfolioArchitectCoordinator,
        entry: ConfigEntry,
        fund_id: str,
        suffix: str,
    ) -> None:
        super().__init__(coordinator, context=f"{fund_id}:{suffix}")
        self._fund_id = fund_id
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{fund_id}_{suffix}"
        self._attr_translation_placeholders = {"fund_name": self._position.name}
        self._attr_device_info = _device_info(source_key)

    @property
    def _position(self) -> PositionData:
        return self.coordinator.data.positions[self._fund_id]

    @property
    def available(self) -> bool:
        return super().available and self._fund_id in self.coordinator.data.positions

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        return {**_position_attributes(self.coordinator, self._position), **base}


class PortfolioAllocationExplanationSensor(_PortfolioPositionDetailSensor):
    """Bounded native explanation for one position's allocation state."""

    _attr_has_entity_name = True
    _attr_translation_key = "allocation_explanation"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["underweight", "on_target", "overweight"]

    def __init__(self, coordinator, entry, fund_id):
        super().__init__(coordinator, entry, fund_id, "allocation_explanation")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_allocation_explanation"

    @property
    def native_value(self) -> str | None:
        return self._position.allocation_status if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        p = self._position
        corridor = self.coordinator.data.allocation.corridor_pp
        return {
            "fund_name": p.name,
            "current_pct": p.current_pct,
            "target_pct": p.target_pct,
            "corridor_lower_pct": p.target_pct - corridor,
            "corridor_upper_pct": p.target_pct + corridor,
            "deviation_pp": p.deviation_pp,
            "current_value_eur": p.current_value_eur,
            "target_value_eur": p.target_value_eur,
            "deviation_eur": p.deviation_eur,
            "reason_code": f"allocation_{p.allocation_status}",
            **base,
        }


class PortfolioPurchaseExplanationSensor(_PortfolioPositionDetailSensor):
    """Bounded native explanation for one proposed purchase."""

    _attr_has_entity_name = True
    _attr_translation_key = "purchase_explanation"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["recommended", "deferred", "not_recommended", "disabled"]

    def __init__(self, coordinator, entry, fund_id):
        super().__init__(coordinator, entry, fund_id, "purchase_explanation")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_purchase_explanation"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.plan_actionable

    @property
    def native_value(self) -> str | None:
        if not self.available:
            return None
        if not self._position.buy_enabled:
            return "disabled"
        if self._position.deferred:
            return "deferred"
        return "recommended" if self._position.proposed_buy_eur > 0 else "not_recommended"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        p = self._position
        return {
            "fund_name": p.name,
            "allocation_status": p.allocation_status,
            "current_pct": p.current_pct,
            "target_pct": p.target_pct,
            "deviation_pp": p.deviation_pp,
            "deviation_eur": p.deviation_eur,
            "buy_enabled": p.buy_enabled,
            "proposed_buy_eur": p.proposed_buy_eur,
            "execution_route": p.execution_route,
            "execution_provider": p.execution_provider,
            "execution_provider_name": p.execution_provider_name,
            "execution_fee_data_as_of": (
                p.execution_fee_data_as_of.isoformat()
                if p.execution_fee_data_as_of is not None
                else None
            ),
            "estimated_fee_eur": p.estimated_fee_eur,
            "estimated_cash_outlay_eur": p.estimated_cash_outlay_eur,
            "estimated_cost_ratio_pct": p.estimated_cost_ratio_pct,
            "additional_reserve_required_eur": p.additional_reserve_required_eur,
            "deferred": p.deferred,
            "reason_code": p.recommendation_reason,
            **base,
        }


class PortfolioAllocationStatusSensor(_PortfolioPositionDetailSensor):
    """Translated allocation state for one ETF."""

    _attr_has_entity_name = True
    _attr_translation_key = "allocation_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["underweight", "on_target", "overweight"]

    def __init__(self, coordinator, entry, fund_id):
        super().__init__(coordinator, entry, fund_id, "allocation_status")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_allocation_status"

    @property
    def native_value(self) -> str | None:
        return self._position.allocation_status if self.available else None


class PortfolioAllocationDriftSensor(_PortfolioPositionDetailSensor):
    """Allocation deviation in percentage points for one ETF."""

    _attr_has_entity_name = True
    _attr_translation_key = "allocation_drift"
    _attr_native_unit_of_measurement = "pp"
    _attr_suggested_display_precision = 2
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, fund_id):
        super().__init__(coordinator, entry, fund_id, "allocation_drift")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_allocation_drift"

    @property
    def native_value(self) -> float | None:
        return self._position.deviation_pp if self.available else None


class PortfolioAllocationValueGapSensor(_PortfolioPositionDetailSensor):
    """Monetary allocation gap or excess for one ETF."""

    _attr_has_entity_name = True
    _attr_translation_key = "allocation_value_gap"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_EUR
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry, fund_id):
        super().__init__(coordinator, entry, fund_id, "allocation_value_gap")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_allocation_value_gap"

    @property
    def native_value(self) -> float | None:
        return self._position.deviation_eur if self.available else None


class PortfolioPositionSourcesSensor(_PortfolioPositionDetailSensor):
    """Readable source provenance for one consolidated target position."""

    _attr_has_entity_name = True
    _attr_translation_key = "position_sources"

    def __init__(self, coordinator, entry, fund_id):
        super().__init__(coordinator, entry, fund_id, "position_sources")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_position_sources"

    @property
    def native_value(self) -> int | None:
        return len(self._position.source_ids) if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        position = self._position
        contributions = _position_source_contributions(self.coordinator, position)
        return {
            "fund_id": position.fund_id,
            "fund_name": position.name,
            "isin": position.isin,
            "wkn": position.wkn,
            "source_count": len(position.source_ids),
            "source_summary": _compact_source_summary(contributions),
            "source_contributions": contributions,
            "source_ids": list(position.source_ids),
            "source_values_eur": dict(position.source_values_eur),
            "consolidated_value_eur": position.current_value_eur,
            **base,
        }


class PortfolioProposedBuySensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Proposed monthly purchase for one target ETF."""

    _attr_has_entity_name = True
    _attr_translation_key = "proposed_buy"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_EUR
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: PortfolioArchitectCoordinator,
        entry: ConfigEntry,
        fund_id: str,
    ) -> None:
        super().__init__(coordinator, context=f"{fund_id}:proposed_buy")
        self._fund_id = fund_id
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{fund_id}_proposed_buy"
        self._attr_translation_placeholders = {"fund_name": self._position.name}
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_proposed_buy"

    @property
    def _position(self) -> PositionData:
        return self.coordinator.data.positions[self._fund_id]

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.plan_actionable
            and self._fund_id in self.coordinator.data.positions
            and self._position.is_target_position
        )

    @property
    def native_value(self) -> float | None:
        return self._position.proposed_buy_eur if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        position = self._position
        return {
            "fund_name": position.name,
            "isin": position.isin,
            "wkn": position.wkn,
            "fund_id": position.fund_id,
            "allocation_status": position.allocation_status,
            "deviation_pp": position.deviation_pp,
            "execution_route": position.execution_route,
            "execution_provider": position.execution_provider,
            "execution_provider_name": position.execution_provider_name,
            "execution_fee_data_as_of": (
                position.execution_fee_data_as_of.isoformat()
                if position.execution_fee_data_as_of is not None
                else None
            ),
            "estimated_fee_eur": position.estimated_fee_eur,
            "estimated_cost_ratio_pct": position.estimated_cost_ratio_pct,
            "recommendation_reason": position.recommendation_reason,
            "deferred": position.deferred,
            **base,
        }


class PortfolioInstrumentIsinSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Copy-friendly ISIN identity sensor for one target instrument."""

    _attr_has_entity_name = True
    _attr_translation_key = "instrument_isin"

    def __init__(
        self,
        coordinator: PortfolioArchitectCoordinator,
        entry: ConfigEntry,
        fund_id: str,
    ) -> None:
        super().__init__(coordinator, context=f"{fund_id}:isin")
        self._fund_id = fund_id
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{fund_id}_isin"
        self._attr_translation_placeholders = {"fund_name": self._position.name}
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_isin"

    @property
    def _position(self) -> PositionData:
        return self.coordinator.data.positions[self._fund_id]

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._fund_id in self.coordinator.data.positions
            and self._position.is_target_position
            and bool(self._position.isin)
        )

    @property
    def native_value(self) -> str | None:
        return self._position.isin if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        position = self._position
        attributes = {
            "fund_name": position.name,
            "wkn": position.wkn,
            "fund_id": position.fund_id,
            **base,
        }
        if self.coordinator.plan_actionable:
            attributes["proposed_buy_eur"] = position.proposed_buy_eur
        return attributes


class PortfolioPlanActionabilitySensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Current actionability of the latest recommendation, separate from its schedule."""

    _attr_has_entity_name = True
    _attr_translation_key = "plan_actionability"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(PLAN_ACTIONABILITY_STATES)

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="plan_actionability")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_plan_actionability"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "plan_actionability"

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    def _semantics(self):
        if self.coordinator.data is None:
            return None
        schedule = self.coordinator.plan_review_schedule()
        planned_execution_on = schedule.planned_execution_on if schedule else None
        current_date = dt_util.as_local(dt_util.utcnow()).date()
        return derive_plan_actionability(
            source_actionable=self.coordinator.plan_actionable,
            execution_state=self.coordinator.data.monthly_plan.execution_state,
            planned_execution_on=planned_execution_on,
            current_date=current_date,
        )

    @property
    def native_value(self) -> str | None:
        semantics = self._semantics()
        return semantics.state if semantics is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        data = self.coordinator.data
        semantics = self._semantics()
        if data is None or semantics is None:
            return base
        schedule = self.coordinator.plan_review_schedule()
        return {
            "source_actionable": self.coordinator.plan_actionable,
            "actionability_reason": self.coordinator.plan_actionability_reason,
            "execution_state": data.monthly_plan.execution_state,
            "plan_ready": data.monthly_plan.ready,
            "recommended_total_display_de": display_eur_de(
                data.monthly_plan.recommended_total_eur,
                available=self.coordinator.plan_actionable,
            ),
            "purchase_count_display_de": display_count_de(
                data.monthly_plan.purchase_count,
                available=self.coordinator.plan_actionable,
            ),
            "evaluated_at": _isoformat(_runtime_timestamp(self.coordinator)),
            "scheduled_execution_on": (
                schedule.planned_execution_on.isoformat() if schedule else None
            ),
            "schedule_relation": semantics.schedule_relation,
            "days_until_scheduled_execution": semantics.days_until_scheduled_execution,
            "display_state_de": display_state_de(
                "plan_actionability", semantics.state
            ),
            **base,
        }


class _PortfolioPlanScheduleDateSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Base class for dates derived from the recurring plan cycle."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATE
    schedule_attribute: str
    object_id: str

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context=self.object_id)
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{self.object_id}"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return self.object_id

    @property
    def _schedule(self):
        return self.coordinator.plan_review_schedule()

    @property
    def available(self) -> bool:
        return super().available and self._schedule is not None

    @property
    def native_value(self) -> date | None:
        schedule = self._schedule
        return getattr(schedule, self.schedule_attribute) if schedule is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        schedule = self._schedule
        if schedule is None:
            return {
                "review_schedule_configured": self.coordinator.review_schedule_configured,
                **base,
            }
        return {
            "evaluated_on": schedule.evaluated_on.isoformat(),
            "planned_execution_on": schedule.planned_execution_on.isoformat(),
            "next_review_on": schedule.next_review_on.isoformat(),
            "review_for_execution_on": schedule.review_for_execution_on.isoformat(),
            "frequency": schedule.frequency,
            "execution_days": list(self.coordinator.plan_execution_days),
            "executions_per_period": schedule.executions_per_period,
            "review_lead_days": self.coordinator.review_lead_days,
            **base,
        }


class PortfolioPlannedExecutionSensor(_PortfolioPlanScheduleDateSensor):
    """Scheduled execution date associated with the latest successful evaluation."""

    _attr_translation_key = "planned_execution"
    schedule_attribute = "planned_execution_on"
    object_id = "planned_execution"


class PortfolioNextPlanReviewSensor(_PortfolioPlanScheduleDateSensor):
    """Next recurring portfolio review date."""

    _attr_translation_key = "next_plan_review"
    schedule_attribute = "next_review_on"
    object_id = "next_plan_review"


class PortfolioLastSuccessfulRefreshSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Timestamp of the last successfully generated portfolio payload."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_successful_refresh"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="last_successful_refresh")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_last_successful_refresh"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "last_successful_refresh"

    @property
    def available(self) -> bool:
        return _runtime_timestamp(self.coordinator) is not None

    @property
    def native_value(self) -> datetime | None:
        return _runtime_timestamp(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        schedule = self.coordinator.plan_review_schedule()
        return {
            "integration_version": VERSION,
            "engine_version": data.runtime.engine_version if data is not None else None,
            "payload_schema_version": (
                data.runtime.payload_schema_version if data is not None else None
            ),
            "planned_execution_on": (
                schedule.planned_execution_on.isoformat() if schedule else None
            ),
            "next_plan_review_on": (
                schedule.next_review_on.isoformat() if schedule else None
            ),
            "plan_frequency": (
                data.monthly_plan.frequency if data is not None else None
            ),
            "freshness_mode": self.coordinator.freshness_mode,
            "display_state_de": display_datetime_de(dt_util.as_local(self.native_value) if self.native_value else None),
        }


class PortfolioPayloadSchemaVersionSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Last successfully parsed source payload schema version."""

    _attr_has_entity_name = True
    _attr_translation_key = "payload_schema_version"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="payload_schema_version")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_payload_schema_version"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "payload_schema_version"

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.runtime.payload_schema_version


class PortfolioSourceProviderSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Explicit provider adapter used for the portfolio source."""

    _attr_has_entity_name = True
    _attr_translation_key = "source_provider"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        PROVIDER_COMDIRECT,
        PROVIDER_DKB,
        PROVIDER_GENERIC_CSV,
        PROVIDER_LOCAL_REST_JSON,
        PROVIDER_MULTI_SOURCE,
    ]

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="source_provider")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_source_provider"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "source_provider"

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return self.coordinator.source_provider

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return _source_attributes(self.coordinator)


class PortfolioSourceCountSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Number of independent sources contributing to the consolidated portfolio."""

    _attr_has_entity_name = True
    _attr_translation_key = "source_count"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="source_count")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_source_count"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "source_count"

    @property
    def native_value(self) -> int:
        return self.coordinator.source_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "sources": list(self.coordinator.source_summaries),
            "conflict_count": self.coordinator.source_conflict_count,
            **_source_attributes(self.coordinator),
        }


class PortfolioSourceConflictCountSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Count of cross-source identity inconsistencies requiring review."""

    _attr_has_entity_name = True
    _attr_translation_key = "source_conflict_count"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="source_conflict_count")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_source_conflict_count"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "source_conflict_count"

    @property
    def native_value(self) -> int:
        return self.coordinator.source_conflict_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "conflicts": list(self.coordinator.source_conflicts),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayStatusSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Validated health status reported by the local Gateway App."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["ok", "degraded", "unavailable"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_status")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_status"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_status"

    @property
    def native_value(self) -> str:
        return self.coordinator.gateway_status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "gateway_version": health.gateway_version if health else None,
            "snapshot_available": health.snapshot_available if health else None,
            "snapshot_generated_at": (
                health.snapshot_generated_at.isoformat()
                if health and health.snapshot_generated_at else None
            ),
            "health_schema_version": (
                health.health_schema_version if health else None
            ),
            "provider_id": health.provider_id if health else None,
            "snapshot_sha256": health.snapshot_sha256 if health else None,
            "snapshot_position_count": (
                health.snapshot_position_count if health else None
            ),
            "poll_interval_seconds": (
                health.poll_interval_seconds if health else None
            ),
            "max_cached_snapshot_age_seconds": (
                health.max_cached_snapshot_age_seconds if health else None
            ),
            "operating_mode": health.operating_mode if health else None,
            "last_refresh_attempt": (
                health.last_refresh_attempt.isoformat()
                if health and health.last_refresh_attempt
                else None
            ),
            "consecutive_refresh_failures": (
                health.consecutive_refresh_failures if health else None
            ),
            "snapshot_age_seconds": self.coordinator.gateway_snapshot_age_seconds,
            "snapshot_expires_in_seconds": (
                self.coordinator.gateway_snapshot_expires_in_seconds
            ),
            "refresh_in_progress": (
                health.refresh_in_progress if health else None
            ),
            "last_refresh_duration_ms": (
                health.last_refresh_duration_ms if health else None
            ),
            "last_refresh_trigger": (
                health.last_refresh_trigger if health else None
            ),
            "next_refresh_due_at": (
                health.next_refresh_due_at.isoformat()
                if health and health.next_refresh_due_at
                else None
            ),
            "manual_refresh_min_interval_seconds": (
                health.manual_refresh_min_interval_seconds if health else None
            ),
            "last_refresh_failure_at": (
                health.last_refresh_failure_at.isoformat()
                if health and health.last_refresh_failure_at
                else None
            ),
            "last_refresh_failure_class": (
                health.last_refresh_failure_class if health else None
            ),
            "recommended_action": (
                health.recommended_action if health else None
            ),
            "retry_after_seconds": (
                health.retry_after_seconds if health else None
            ),
            "attention_reason": self.coordinator.gateway_attention_reason,
            "refresh_overdue": self.coordinator.is_gateway_refresh_overdue(),
            "transport_integrity_verified": (
                self.coordinator.rest_snapshot_integrity_verified
            ),
            "health_error": self.coordinator.gateway_health_error,
            "display_state_de": display_state_de(
                "gateway_status", self.native_value
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayOperatingModeSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Whether live data is current, cached, or unavailable."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_operating_mode"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "live",
        "last_known_good",
        "reauthentication_required",
        "unavailable",
    ]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_operating_mode")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_operating_mode"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_operating_mode"

    @property
    def native_value(self) -> str:
        return self.coordinator.gateway_operating_mode

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "last_refresh_attempt": (
                health.last_refresh_attempt.isoformat()
                if health and health.last_refresh_attempt
                else None
            ),
            "last_refresh_success": (
                health.last_refresh_success.isoformat()
                if health and health.last_refresh_success
                else None
            ),
            "consecutive_refresh_failures": (
                health.consecutive_refresh_failures if health else None
            ),
            "snapshot_age_seconds": self.coordinator.gateway_snapshot_age_seconds,
            "snapshot_expires_in_seconds": (
                self.coordinator.gateway_snapshot_expires_in_seconds
            ),
            "display_state_de": display_state_de(
                "gateway_operating_mode", self.native_value
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayLastRefreshSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Last successful Comdirect refresh reported by the Gateway App."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_last_refresh"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_last_refresh")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_last_refresh"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_last_refresh"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_health is not None
            and self.coordinator.gateway_health.last_refresh_success is not None
        )

    @property
    def native_value(self) -> datetime | None:
        health = self.coordinator.gateway_health
        return health.last_refresh_success if self.available and health else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "display_state_de": display_datetime_de(dt_util.as_local(self.native_value) if self.native_value else None),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayNextRefreshSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Next fixed-cadence refresh planned by the Gateway App."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_next_refresh"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_next_refresh")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_next_refresh"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_next_refresh"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_next_refresh_due_at is not None
        )

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.gateway_next_refresh_due_at if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "display_state_de": display_datetime_de(
                dt_util.as_local(self.native_value) if self.native_value else None
            ),
            **_source_attributes(self.coordinator),
        }


class _MinuteTickEntity:
    """Refresh a time-derived schedule entity without polling the Gateway."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._handle_minute_tick,
                REFRESH_SCHEDULE_TICK,
            )
        )

    @callback
    def _handle_minute_tick(self, _now: datetime) -> None:
        self.async_write_ha_state()


class PortfolioGatewayRefreshScheduleSensor(
    _MinuteTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    SensorEntity,
):
    """Human-readable state of the Gateway's fixed-cadence refresh schedule."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_refresh_schedule"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["scheduled", "due_now", "overdue", "refreshing"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_refresh_schedule")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_refresh_schedule"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_refresh_schedule"

    @property
    def available(self) -> bool:
        return self.coordinator.gateway_next_refresh_due_at is not None

    @property
    def native_value(self) -> str | None:
        due_at = self.coordinator.gateway_next_refresh_due_at
        if due_at is None:
            return None
        health = self.coordinator.gateway_health
        if health is not None and health.refresh_in_progress:
            return "refreshing"
        now = dt_util.utcnow()
        if now <= due_at:
            return "scheduled"
        if self.coordinator.is_gateway_refresh_overdue(now) is True:
            return "overdue"
        return "due_now"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        due_at = self.coordinator.gateway_next_refresh_due_at
        health = self.coordinator.gateway_health
        now = dt_util.utcnow()
        seconds_until_due = (
            int((due_at - now).total_seconds()) if due_at is not None else None
        )
        return {
            "scheduled_refresh_time": due_at.isoformat() if due_at else None,
            "seconds_until_due": seconds_until_due,
            "overdue_seconds": (
                max(0, -seconds_until_due) if seconds_until_due is not None else None
            ),
            "grace_seconds": self.coordinator.gateway_refresh_grace_seconds,
            "poll_interval_seconds": health.poll_interval_seconds if health else None,
            "refresh_in_progress": health.refresh_in_progress if health else None,
            "health_observed_at": _isoformat(
                self.coordinator.gateway_health_observed_at
            ),
            "overdue_evidence_current": (
                self.coordinator.gateway_refresh_overdue_evidence_current
            ),
            "display_state_de": display_state_de(
                "gateway_refresh_schedule", self.native_value
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayLastRefreshDurationSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Duration of the most recently completed Gateway refresh."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_last_refresh_duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_last_refresh_duration")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_last_refresh_duration"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_last_refresh_duration"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_last_refresh_duration_seconds is not None
        )

    @property
    def native_value(self) -> float | None:
        return (
            self.coordinator.gateway_last_refresh_duration_seconds
            if self.available
            else None
        )

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


class PortfolioGatewayLastRefreshTriggerSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Trigger that initiated the most recent Gateway refresh attempt."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_last_refresh_trigger"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["startup", "scheduled", "manual", "bootstrap"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_last_refresh_trigger")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_last_refresh_trigger"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_last_refresh_trigger"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_last_refresh_trigger is not None
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.gateway_last_refresh_trigger if self.available else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "display_state_de": display_state_de(
                "gateway_last_refresh_trigger",
                self.native_value,
                available=self.available,
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayAttentionReasonSensor(
    _MinuteTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    SensorEntity,
):
    """Priority-ordered reason why live-source operation needs attention."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_attention_reason"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "none",
        "health_unavailable",
        "reauthentication_required",
        "integrity_failure",
        "supplemental_source_unavailable",
        "snapshot_unavailable",
        "refresh_overdue",
        "last_known_good",
        "authentication_error",
        "rate_limited",
        "remote_service_error",
        "remote_api_error",
        "transport_error",
        "invalid_response",
        "configuration_error",
        "gateway_error",
        "internal_error",
    ]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_attention_reason")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_attention_reason"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_attention_reason"

    @property
    def native_value(self) -> str:
        return self.coordinator.gateway_attention_reason

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "recommended_action": self.coordinator.gateway_recommended_action,
            "consecutive_refresh_failures": (
                health.consecutive_refresh_failures if health else None
            ),
            "last_refresh_failure_at": (
                health.last_refresh_failure_at.isoformat()
                if health and health.last_refresh_failure_at
                else None
            ),
            "retry_after_seconds": health.retry_after_seconds if health else None,
            "refresh_overdue": self.coordinator.is_gateway_refresh_overdue(),
            "display_state_de": display_state_de(
                "gateway_attention_reason", self.native_value
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayRecommendedActionSensor(
    _MinuteTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    SensorEntity,
):
    """Recommended operator response for the current live-source state."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_recommended_action"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "none",
        "reauthenticate",
        "wait",
        "check_connectivity",
        "inspect_logs",
        "fix_configuration",
    ]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_recommended_action")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_recommended_action"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_recommended_action"

    @property
    def native_value(self) -> str:
        return self.coordinator.gateway_recommended_action

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "display_state_de": display_state_de(
                "gateway_recommended_action", self.native_value
            ),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewayLastRefreshFailureSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Timestamp of the most recent unresolved live-refresh failure."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_last_refresh_failure"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_last_refresh_failure")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_last_refresh_failure"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_last_refresh_failure"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_last_refresh_failure_at is not None
        )

    @property
    def native_value(self) -> datetime | None:
        return (
            self.coordinator.gateway_last_refresh_failure_at
            if self.available
            else None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self.coordinator.gateway_health
        return {
            "failure_class": self.coordinator.gateway_last_refresh_failure_class,
            "recommended_action": self.coordinator.gateway_recommended_action,
            "retry_after_seconds": health.retry_after_seconds if health else None,
            "display_state_de": display_datetime_de(dt_util.as_local(self.native_value) if self.native_value else None),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewaySnapshotGeneratedSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Timestamp embedded in the accepted live portfolio snapshot."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_snapshot_generated"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_snapshot_generated")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_snapshot_generated"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_snapshot_generated"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_snapshot_generated_at is not None
        )

    @property
    def native_value(self) -> datetime | None:
        return (
            self.coordinator.gateway_snapshot_generated_at
            if self.available
            else None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "snapshot_sha256": self.coordinator.rest_snapshot_sha256,
            "position_count": self.coordinator.rest_snapshot_position_count,
            "integrity_verified": (
                self.coordinator.rest_snapshot_integrity_verified
            ),
            "display_state_de": display_datetime_de(dt_util.as_local(self.native_value) if self.native_value else None),
            **_source_attributes(self.coordinator),
        }


class PortfolioGatewaySnapshotAgeSensor(
    _MinuteTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    SensorEntity,
):
    """Age of the active Gateway snapshot."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_snapshot_age"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_snapshot_age")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_snapshot_age"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_snapshot_age"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_snapshot_age_seconds is not None
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.gateway_snapshot_age_seconds if self.available else None


class PortfolioGatewaySnapshotExpiresInSensor(
    _MinuteTickEntity,
    CoordinatorEntity[PortfolioArchitectCoordinator],
    SensorEntity,
):
    """Remaining service window for the cached Gateway snapshot."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_snapshot_expires_in"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_snapshot_expires_in")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_snapshot_expires_in"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_snapshot_expires_in"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_snapshot_expires_in_seconds is not None
        )

    @property
    def native_value(self) -> int | None:
        return (
            self.coordinator.gateway_snapshot_expires_in_seconds
            if self.available
            else None
        )


class PortfolioGatewayConsecutiveRefreshFailuresSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Consecutive failed Comdirect refresh attempts."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_consecutive_refresh_failures"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_consecutive_refresh_failures")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_consecutive_refresh_failures"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_consecutive_refresh_failures"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.gateway_consecutive_refresh_failures is not None
        )

    @property
    def native_value(self) -> int | None:
        return (
            self.coordinator.gateway_consecutive_refresh_failures
            if self.available
            else None
        )


class PortfolioGatewayLastErrorSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Sanitized Gateway App error code."""

    _attr_has_entity_name = True
    _attr_translation_key = "gateway_last_error"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="gateway_last_error")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_gateway_last_error"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "gateway_last_error"

    @property
    def native_value(self) -> str:
        health = self.coordinator.gateway_health
        if health is not None:
            return health.last_error or "none"
        return self.coordinator.gateway_health_error or "health_unavailable"


class PortfolioVersionSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Installed Portfolio Architect version and engine compatibility."""

    _attr_has_entity_name = True
    _attr_translation_key = "version"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PortfolioArchitectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, context="version")
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_version"
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return "version"

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return VERSION

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        engine_version = (
            self.coordinator.data.runtime.engine_version
            if self.coordinator.data is not None
            else None
        )
        return {
            "integration_version": VERSION,
            "engine_version": engine_version,
            "versions_match": engine_version in {None, VERSION},
        }



class _PortfolioHoldingSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, position_id: str, suffix: str) -> None:
        super().__init__(coordinator, context=f"holding:{position_id}:{suffix}")
        self._position_id = position_id
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{position_id}_{suffix}"
        self._attr_translation_placeholders = {"holding_name": self._holding.name}
        self._attr_device_info = _device_info(source_key)

    @property
    def _holding(self) -> HoldingData:
        return self.coordinator.data.holdings[self._position_id]

    @property
    def available(self) -> bool:
        return super().available and self._position_id in self.coordinator.data.holdings

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        if not self.available:
            return base
        return {**self._holding.attributes, **base}


class PortfolioHoldingWholeAllocationSensor(_PortfolioHoldingSensor):
    _attr_translation_key = "whole_portfolio_allocation"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 2
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, position_id: str) -> None:
        super().__init__(coordinator, entry, position_id, "whole_portfolio_allocation")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._position_id}_whole_portfolio_allocation"

    @property
    def native_value(self) -> float | None:
        return self._holding.whole_portfolio_pct if self.available else None


class PortfolioHoldingValueSensor(_PortfolioHoldingSensor):
    _attr_translation_key = "holding_value"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_EUR
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry, position_id: str) -> None:
        super().__init__(coordinator, entry, position_id, "holding_value")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._position_id}_holding_value"

    @property
    def native_value(self) -> float | None:
        return self._holding.current_value_eur if self.available else None


class PortfolioHoldingQuantitySensor(_PortfolioHoldingSensor):
    _attr_translation_key = "holding_quantity"
    _attr_suggested_display_precision = 8
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, position_id: str) -> None:
        super().__init__(coordinator, entry, position_id, "holding_quantity")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._position_id}_holding_quantity"

    @property
    def available(self) -> bool:
        return super().available and self._holding.quantity is not None

    @property
    def native_value(self) -> float | None:
        return self._holding.quantity if self.available else None


class PortfolioHoldingScopeSensor(_PortfolioHoldingSensor):
    _attr_translation_key = "strategy_scope"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["current_plan", "outside_scope"]

    def __init__(self, coordinator, entry, position_id: str) -> None:
        super().__init__(coordinator, entry, position_id, "strategy_scope")

    @property
    def suggested_object_id(self) -> str:
        return f"{self._position_id}_strategy_scope"

    @property
    def native_value(self) -> str | None:
        return self._holding.strategy_scope if self.available else None


class PortfolioAllocationSensor(
    CoordinatorEntity[PortfolioArchitectCoordinator], SensorEntity
):
    """Current or target allocation for one ETF position."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: PortfolioArchitectCoordinator,
        entry: ConfigEntry,
        fund_id: str,
        kind: AllocationKind,
    ) -> None:
        super().__init__(coordinator, context=f"{fund_id}:{kind}")
        self._fund_id = fund_id
        self._kind = kind
        source_key = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{source_key}_{fund_id}_{kind}_allocation"
        self._attr_translation_key = f"{kind}_allocation"
        if kind is AllocationKind.CURRENT:
            self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_translation_placeholders = {"fund_name": self._position.name}
        self._attr_device_info = _device_info(source_key)

    @property
    def suggested_object_id(self) -> str:
        return f"{self._fund_id}_{self._kind}_allocation"

    @property
    def _position(self) -> PositionData:
        return self.coordinator.data.positions[self._fund_id]

    @property
    def available(self) -> bool:
        return super().available and self._fund_id in self.coordinator.data.positions

    @property
    def native_value(self) -> float | None:
        if not self.available:
            return None
        position = self._position
        return position.current_pct if self._kind is AllocationKind.CURRENT else position.target_pct

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = _source_attributes(self.coordinator)
        base["allocation_kind"] = self._kind
        if not self.available:
            return base

        position = self._position
        identity = {
            "fund_id": position.fund_id,
            "wkn": position.wkn,
            "isin": position.isin,
            "fund_name": position.name,
        }
        if self._kind is AllocationKind.TARGET:
            return {**identity, **base}
        return {**_position_attributes(self.coordinator, position), **base}


_ACTIONABLE_POSITION_ATTRIBUTE_KEYS = frozenset({
    "buy_enabled",
    "proposed_buy_eur",
    "execution_route",
    "estimated_fee_eur",
    "estimated_cash_outlay_eur",
    "estimated_cost_ratio_pct",
    "recommendation_reason",
    "additional_reserve_required_eur",
    "deferred",
})


def _position_attributes(
    coordinator: PortfolioArchitectCoordinator,
    position: PositionData,
) -> dict[str, Any]:
    """Return position attributes without stale action guidance in degraded mode."""
    attributes = dict(position.attributes)
    if coordinator.plan_actionable:
        return attributes
    for key in _ACTIONABLE_POSITION_ATTRIBUTE_KEYS:
        attributes.pop(key, None)
    return attributes


def _position_source_contributions(
    coordinator: PortfolioArchitectCoordinator,
    position: PositionData,
) -> list[dict[str, Any]]:
    """Return ordered, privacy-safe contribution rows for one position."""
    ordered_summaries = [
        item
        for item in coordinator.source_summaries
        if isinstance(item, dict) and item.get("source_id")
    ]
    summaries = {str(item.get("source_id")): item for item in ordered_summaries}
    dkb_ids = [
        str(item.get("source_id"))
        for item in ordered_summaries
        if item.get("provider") == PROVIDER_DKB
    ]
    dkb_ordinals = {source_id: index for index, source_id in enumerate(dkb_ids, start=1)}
    rows: list[dict[str, Any]] = []
    for source_id, value_eur in position.source_values_eur:
        summary = summaries.get(source_id, {})
        provider = summary.get("provider")
        label = str(summary.get("label") or source_id)
        if provider == PROVIDER_LOCAL_REST_JSON:
            display_name = "Comdirect" if label == "Comdirect REST" else "Local REST"
        elif provider == PROVIDER_DKB:
            display_name = (
                "DKB"
                if len(dkb_ids) == 1
                else f"DKB {dkb_ordinals.get(source_id, 1)}"
            )
        else:
            display_name = label.replace(" REST", "").replace(" CSV", "")
        rows.append(
            {
                "source_id": source_id,
                "provider": provider,
                "label": label,
                "display_name": display_name,
                "value_eur": value_eur,
            }
        )
    return rows


def _compact_source_summary(
    contributions: list[dict[str, Any]], *, maximum: int = 120
) -> str:
    """Return a bounded tile summary while retaining exact details in attributes."""
    parts = [
        f"{item['display_name']} {item['value_eur']:.2f} EUR"
        for item in contributions
    ]
    summary = " · ".join(parts)
    if len(summary) <= maximum:
        return summary
    kept: list[str] = []
    for part in parts:
        candidate = " · ".join([*kept, part])
        if len(candidate) + 4 > maximum:
            break
        kept.append(part)
    return (" · ".join(kept) + " · …") if kept else summary[: maximum - 1] + "…"


def _device_info(source_key: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, source_key)},
        name=NAME,
        manufacturer="Portfolio Architect",
        model="Local portfolio analysis service",
        sw_version=VERSION,
        entry_type=DeviceEntryType.SERVICE,
    )


def _runtime_timestamp(coordinator: PortfolioArchitectCoordinator) -> datetime | None:
    """Return the source generation timestamp with safe legacy fallbacks."""
    if coordinator.data is not None and coordinator.data.runtime.generated_at is not None:
        return coordinator.data.runtime.generated_at
    return coordinator.source_last_updated or coordinator.last_update_success_time


def _source_attributes(coordinator: PortfolioArchitectCoordinator) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "source_type": coordinator.source_type,
        "source_provider": coordinator.source_provider,
        "source": coordinator.source_label,
        "source_count": coordinator.source_count,
        "provider_count": coordinator.provider_count,
        "provider_ids": list(coordinator.provider_ids),
        "provider_summary": coordinator.provider_summary,
        "provider_summary_de": coordinator.provider_summary_de,
        "unavailable_source_count": coordinator.unavailable_source_count,
        "unavailable_source_ids": list(coordinator.unavailable_source_ids),
        "unavailable_source_summary": coordinator.unavailable_source_summary,
        "unavailable_source_summary_de": coordinator.unavailable_source_summary_de,
        "source_conflict_count": coordinator.source_conflict_count,
        "configuration_directory": coordinator.configuration_label,
        "source_last_changed": _isoformat(coordinator.source_last_changed),
        "source_last_updated": _isoformat(coordinator.source_last_updated),
        "last_successful_refresh": _isoformat(_runtime_timestamp(coordinator)),
        "data_fresh": coordinator.is_data_fresh(),
        "plan_actionable": coordinator.plan_actionable,
        "plan_actionability_reason": coordinator.plan_actionability_reason,
    }
    if coordinator.source_entity_id is not None:
        attributes["source_entity_id"] = coordinator.source_entity_id
    return attributes


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
