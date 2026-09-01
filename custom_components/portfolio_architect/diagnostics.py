"""Diagnostics support for Portfolio Architect."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CONFIG_DIRECTORY,
    CONF_SETUP_STATE,
    DEFAULT_CONFIG_DIRECTORY,
    SETUP_STATE_CONFIGURED,
    VERSION,
)
from .coordinator import PortfolioArchitectCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return privacy-conscious diagnostics for a config entry."""
    setup_state = entry.data.get(CONF_SETUP_STATE, SETUP_STATE_CONFIGURED)
    if setup_state != SETUP_STATE_CONFIGURED or entry.runtime_data is None:
        # A deliberately incomplete first-run entry has no coordinator, entities or
        # source payload yet. Diagnostics must remain available without inventing
        # runtime state or exposing filesystem contents.
        return {
            "integration_version": VERSION,
            "setup_state": setup_state,
            "config_directory": entry.data.get(
                CONF_CONFIG_DIRECTORY, DEFAULT_CONFIG_DIRECTORY
            ),
            "source_configured": bool(entry.data.get("source_type")),
            "runtime_loaded": False,
        }

    coordinator: PortfolioArchitectCoordinator = entry.runtime_data
    source_state = (
        hass.states.get(coordinator.source_entity_id)
        if coordinator.source_entity_id is not None
        else None
    )
    data = coordinator.data
    review_schedule = coordinator.plan_review_schedule()

    return {
        "integration_version": VERSION,
        "engine_version": data.runtime.engine_version if data is not None else None,
        "payload_schema_version": (
            data.runtime.payload_schema_version if data is not None else None
        ),
        "source_type": coordinator.source_type,
        "source_provider": coordinator.source_provider,
        "source_adapter": coordinator.source_adapter_diagnostics,
        "source": coordinator.source_label,
        "source_freshness": {
            "mode": coordinator.freshness_mode,
            "threshold_hours": coordinator.freshness_hours,
            "data_fresh": coordinator.is_data_fresh(),
            "stale_source_ids": list(coordinator.stale_source_ids),
            "stale_source_summary": coordinator.stale_source_summary,
            "sources": list(coordinator.source_freshness_evidence()),
        },
        "gateway_health": (
            {
                "version": coordinator.gateway_health.gateway_version,
                "status": coordinator.gateway_health.status,
                "snapshot_available": coordinator.gateway_health.snapshot_available,
                "snapshot_generated_at": _isoformat(
                    coordinator.gateway_health.snapshot_generated_at
                ),
                "last_refresh_success": _isoformat(
                    coordinator.gateway_health.last_refresh_success
                ),
                "reauthentication_required": (
                    coordinator.gateway_health.reauthentication_required
                ),
                "last_error": coordinator.gateway_health.last_error,
                "health_schema_version": (
                    coordinator.gateway_health.health_schema_version
                ),
                "provider_id": coordinator.gateway_health.provider_id,
                "snapshot_sha256": coordinator.gateway_health.snapshot_sha256,
                "snapshot_position_count": (
                    coordinator.gateway_health.snapshot_position_count
                ),
                "poll_interval_seconds": (
                    coordinator.gateway_health.poll_interval_seconds
                ),
                "max_cached_snapshot_age_seconds": (
                    coordinator.gateway_health.max_cached_snapshot_age_seconds
                ),
                "operating_mode": coordinator.gateway_health.operating_mode,
                "last_refresh_attempt": _isoformat(
                    coordinator.gateway_health.last_refresh_attempt
                ),
                "consecutive_refresh_failures": (
                    coordinator.gateway_health.consecutive_refresh_failures
                ),
                "snapshot_age_seconds": (
                    coordinator.gateway_health.snapshot_age_seconds
                ),
                "snapshot_expires_in_seconds": (
                    coordinator.gateway_health.snapshot_expires_in_seconds
                ),
                "refresh_in_progress": (
                    coordinator.gateway_health.refresh_in_progress
                ),
                "last_refresh_duration_ms": (
                    coordinator.gateway_health.last_refresh_duration_ms
                ),
                "last_refresh_trigger": (
                    coordinator.gateway_health.last_refresh_trigger
                ),
                "next_refresh_due_at": _isoformat(
                    coordinator.gateway_health.next_refresh_due_at
                ),
                "manual_refresh_min_interval_seconds": (
                    coordinator.gateway_health.manual_refresh_min_interval_seconds
                ),
                "last_refresh_failure_at": _isoformat(
                    coordinator.gateway_health.last_refresh_failure_at
                ),
                "last_refresh_failure_class": (
                    coordinator.gateway_health.last_refresh_failure_class
                ),
                "recommended_action": (
                    coordinator.gateway_health.recommended_action
                ),
                "retry_after_seconds": (
                    coordinator.gateway_health.retry_after_seconds
                ),
                "active_acquisition_method": (
                    coordinator.gateway_health.active_acquisition_method
                ),
                "acquisition_methods": [
                    item.as_public_dict()
                    for item in coordinator.gateway_health.acquisition_methods
                ],
                "fallback_policy": coordinator.gateway_health.fallback_policy,
                "acquisition_capabilities": [
                    item.as_public_dict()
                    for item in coordinator.gateway_health.acquisition_capabilities
                ],
                "previous_acquisition_method": (
                    coordinator.gateway_health.previous_acquisition_method
                ),
                "last_acquisition_method_change_at": _isoformat(
                    coordinator.gateway_health.last_acquisition_method_change_at
                ),
                "last_acquisition_method_change_reason": (
                    coordinator.gateway_health.last_acquisition_method_change_reason
                ),
            }
            if coordinator.gateway_health is not None
            else None
        ),
        "gateway_health_error": coordinator.gateway_health_error,
        "gateway_health_observed_at": _isoformat(
            coordinator.gateway_health_observed_at
        ),
        "supplemental_gateway_health": {
            provider_id: {
                "status": health.status,
                "operating_mode": health.operating_mode,
                "snapshot_available": health.snapshot_available,
                "snapshot_generated_at": _isoformat(health.snapshot_generated_at),
                "health_schema_version": health.health_schema_version,
                "provider_id": health.provider_id,
                "active_acquisition_method": health.active_acquisition_method,
                "acquisition_methods": [
                    item.as_public_dict() for item in health.acquisition_methods
                ],
                "fallback_policy": health.fallback_policy,
                "acquisition_capabilities": [
                    item.as_public_dict() for item in health.acquisition_capabilities
                ],
                "previous_acquisition_method": health.previous_acquisition_method,
                "last_acquisition_method_change_at": _isoformat(
                    health.last_acquisition_method_change_at
                ),
                "last_acquisition_method_change_reason": (
                    health.last_acquisition_method_change_reason
                ),
            }
            for provider_id, health in sorted(
                coordinator.supplemental_gateway_health.items()
            )
        },
        "supplemental_gateway_health_errors": dict(
            sorted(coordinator.supplemental_gateway_health_errors.items())
        ),
        "unavailable_sources": {
            "count": coordinator.unavailable_source_count,
            "ids": list(coordinator.unavailable_source_ids),
            "summary": coordinator.unavailable_source_summary,
        },
        "home_assistant_last_known_good": {
            "active": coordinator.using_home_assistant_last_known_good,
            "snapshot_generated_at": _isoformat(
                coordinator.gateway_snapshot_generated_at
            ),
            "snapshot_age_seconds": coordinator.gateway_snapshot_age_seconds,
            "retention_max_age_seconds": coordinator.home_assistant_lkg_max_age_seconds,
            "accepted_sha256": coordinator.rest_snapshot_sha256,
            "accepted_position_count": coordinator.rest_snapshot_position_count,
            "consecutive_gateway_failures": (
                coordinator.gateway_consecutive_refresh_failures
            ),
            "last_gateway_failure_at": _isoformat(
                coordinator.gateway_last_refresh_failure_at
            ),
        },
        "gateway_recovery": {
            "attention_required": coordinator.gateway_attention_required,
            "attention_reason": coordinator.gateway_attention_reason,
            "recommended_action": coordinator.gateway_recommended_action,
            "refresh_overdue": coordinator.is_gateway_refresh_overdue(),
            "refresh_overdue_evidence_current": (
                coordinator.gateway_refresh_overdue_evidence_current
            ),
            "health_observed_at": _isoformat(coordinator.gateway_health_observed_at),
            "last_refresh_failure_at": _isoformat(
                coordinator.gateway_last_refresh_failure_at
            ),
            "last_refresh_failure_class": (
                coordinator.gateway_last_refresh_failure_class
            ),
        },
        "rest_snapshot_integrity": {
            "verified": coordinator.rest_snapshot_integrity_verified,
            "last_error": coordinator.rest_snapshot_integrity_error,
            "accepted_sha256": coordinator.rest_snapshot_sha256,
            "accepted_position_count": coordinator.rest_snapshot_position_count,
            "accepted_generated_at": _isoformat(
                coordinator.gateway_snapshot_generated_at
            ),
            "health_schema_version": (
                coordinator.gateway_health.health_schema_version
                if coordinator.gateway_health is not None
                else None
            ),
        },
        "configuration_directory": coordinator.configuration_label,
        "legacy_source_entity_id": coordinator.source_entity_id,
        "source_state": source_state.state if source_state else None,
        "source_last_changed": _isoformat(coordinator.source_last_changed),
        "source_last_updated": _isoformat(coordinator.source_last_updated),
        "last_update_success": coordinator.last_update_success,
        "last_successful_refresh": _isoformat(coordinator.data_timestamp),
        "data_fresh": coordinator.is_data_fresh(),
        "plan_actionable": coordinator.plan_actionable,
        "plan_actionability_reason": coordinator.plan_actionability_reason,
        "freshness_mode": coordinator.freshness_mode,
        "freshness_policy": coordinator.freshness_policy,
        "freshness_threshold_hours": coordinator.freshness_hours,
        "freshness_thresholds": coordinator.effective_freshness_thresholds,
        "fresh_through": _isoformat(coordinator.data_fresh_through),
        "review_schedule": {
            "configured": coordinator.review_schedule_configured,
            "frequency": coordinator.plan_frequency,
            "execution_days": list(coordinator.plan_execution_days),
            "execution_month": (
                coordinator.schedule_config.execution_month
                if coordinator.schedule_config else None
            ),
            "execution_month_offset": (
                coordinator.schedule_config.execution_month_offset
                if coordinator.schedule_config else None
            ),
            "review_lead_days": coordinator.review_lead_days,
            "evaluated_on": _isoformat(review_schedule.evaluated_on) if review_schedule else None,
            "planned_execution_on": _isoformat(review_schedule.planned_execution_on) if review_schedule else None,
            "next_review_on": _isoformat(review_schedule.next_review_on) if review_schedule else None,
            "review_for_execution_on": _isoformat(review_schedule.review_for_execution_on) if review_schedule else None,
            "review_due": coordinator.is_plan_review_due(),
        },
        "last_error": (
            None
            if coordinator.last_update_success
            else str(coordinator.last_exception)
        ),
        "current_plan_position_count": len(data.positions) if data is not None else 0,
        "whole_portfolio_position_count": len(data.holdings) if data is not None else 0,
        "outside_scope_position_count": (
            sum(1 for holding in data.holdings.values() if not holding.in_current_plan)
            if data is not None else 0
        ),
        "decision_trace": (
            {
                "state": coordinator.plan_delta.state,
                "previous_evaluated_at": coordinator.plan_delta.attributes.get(
                    "previous_evaluated_at"
                ),
                "current_evaluated_at": coordinator.plan_delta.attributes.get(
                    "current_evaluated_at"
                ),
                "change_categories": list(
                    coordinator.plan_delta.attributes.get("change_categories", [])
                ),
                "position_change_count": coordinator.plan_delta.attributes.get(
                    "position_change_count", 0
                ),
                "changed_fund_ids": [
                    item.get("fund_id")
                    for item in coordinator.plan_delta.attributes.get(
                        "position_changes", []
                    )
                    if isinstance(item, dict) and isinstance(item.get("fund_id"), str)
                ],
            }
            if coordinator.plan_delta is not None
            else None
        ),
        "monthly_plan": (
            {
                # Financial amounts are intentionally omitted from diagnostics.
                "ready": data.monthly_plan.ready,
                "purchase_count": data.monthly_plan.purchase_count,
                "name": data.monthly_plan.name,
                "configuration_source": data.monthly_plan.configuration_source,
                "budget_basis": data.monthly_plan.budget_basis,
                "frequency": data.monthly_plan.frequency,
                "executions_per_period": data.monthly_plan.executions_per_period,
                "has_unallocated_contribution": (
                    data.monthly_plan.unallocated_contribution_eur > 0.01
                ),
            }
            if data is not None
            else None
        ),
        "policy": (
            {
                "status": data.policy.status,
                "checks_evaluated": data.policy.checks_evaluated,
                "errors": data.policy.errors,
                "warnings": data.policy.warnings,
                "accepted_exceptions": data.policy.accepted_exceptions,
                "optimisation_opportunities": data.policy.opportunities,
                "mandatory_controls_compliant": data.policy.mandatory_controls_compliant,
                "next_exception_review_on": _isoformat(data.policy.next_exception_review_on),
                "exception_review_overdue": data.policy.review_overdue,
                "overdue_exception_reviews": data.policy.overdue_reviews,
                "oldest_overdue_exception_review_on": _isoformat(
                    data.policy.oldest_overdue_review_on
                ),
                "last_exception_decision_on": _isoformat(
                    data.policy.last_exception_decision_on
                ),
                "active_finding_keys": [
                    finding.key for finding in data.policy.non_pass_findings
                ],
            }
            if data is not None
            else None
        ),
        "allocation": (
            {
                # Financial values are intentionally omitted from diagnostics.
                "corridor_pp": data.allocation.corridor_pp,
                "underweight": data.allocation.underweight,
                "on_target": data.allocation.on_target,
                "overweight": data.allocation.overweight,
                "allocation_on_target": data.allocation.allocation_on_target,
                "whole_portfolio_position_count": data.allocation.whole_portfolio_position_count,
                "current_plan_position_count": data.allocation.current_plan_position_count,
                "outside_scope_position_count": data.allocation.outside_scope_position_count,
            }
            if data is not None
            else None
        ),
        "target_coverage": (
            {
                "held": data.coverage.held,
                "total": data.coverage.total,
                "missing": data.coverage.missing,
                "coverage_pct": data.coverage.coverage_pct,
                "missing_fund_ids": list(data.coverage.missing_fund_ids),
            }
            if data is not None
            else None
        ),
        "holdings": [
            {
                "position_id": holding.position_id,
                "instrument_type": holding.instrument_type,
                "strategy_scope": holding.strategy_scope,
                "has_value": holding.current_value_eur > 0,
            }
            for holding in data.holdings.values()
        ] if data is not None else [],
        "positions": [
            {
                "fund_id": position.fund_id,
                "is_target_position": position.is_target_position,
                "is_held": position.is_held,
                "allocation_status": position.allocation_status,
                "buy_enabled": position.buy_enabled,
                "has_proposed_buy": position.proposed_buy_eur > 0,
            }
            for position in data.positions.values()
        ] if data is not None else [],
    }


def _isoformat(value: Any) -> str | None:
    """Return an ISO timestamp when available."""
    return value.isoformat() if value is not None else None
