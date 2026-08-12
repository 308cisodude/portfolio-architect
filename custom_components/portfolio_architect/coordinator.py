"""Coordinator for self-contained Portfolio Architect calculations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import (
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_HOLDINGS,
    ATTR_POLICY_FINDINGS,
    ATTR_RECOMMENDATIONS,
    ATTR_SUMMARY,
    CONF_CONFIG_DIRECTORY,
    CONF_CSV_PATH,
    CONF_FRESHNESS_HOURS,
    CONF_PLAN_BUDGET_AMOUNT,
    CONF_PLAN_BUDGET_BASIS,
    CONF_PLAN_EXECUTION_DAYS,
    CONF_PLAN_EXECUTION_MONTH,
    CONF_PLAN_EXECUTION_MONTH_OFFSET,
    CONF_PLAN_FREQUENCY,
    CONF_PLAN_INSTRUMENTS,
    CONF_PLAN_NAME,
    CONF_PLAN_OVERRIDE_ENABLED,
    CONF_PLAN_SCHEDULE_ENABLED,
    CONF_EXECUTION_COST_AWARE_ENABLED,
    CONF_EXECUTION_POLICY,
    CONF_EXECUTION_MAX_COST_RATIO_PCT,
    CONF_EXECUTION_MAX_DEFERRAL_PERIODS,
    CONF_EXECUTION_MAX_ORDERS,
    CONF_EXECUTION_RESERVE_MODE,
    CONF_MANUAL_COMMISSION_BASE_EUR,
    CONF_MANUAL_COMMISSION_PCT,
    CONF_MANUAL_COMMISSION_MIN_EUR,
    CONF_MANUAL_COMMISSION_MAX_EUR,
    CONF_MANUAL_VENUE_FEE_PCT,
    CONF_MANUAL_VENUE_FEE_MIN_EUR,
    CONF_MANUAL_SETTLEMENT_FEE_EUR,
    CONF_REVIEW_LEAD_DAYS,
    CONF_SOURCE_ENTITY_ID,
    CONF_SUPPLEMENTAL_DKB_CSV_PATHS,
    CONF_SOURCE_TYPE,
    DEFAULT_CONFIG_DIRECTORY,
    DEFAULT_CSV_PATH,
    DEFAULT_FRESHNESS_HOURS,
    DEFAULT_HOME_ASSISTANT_LKG_MAX_AGE_SECONDS,
    DEFAULT_REVIEW_LEAD_DAYS,
    DEFAULT_SOURCE_ENTITY_ID,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    MAX_SUPPLEMENTAL_SOURCES,
    DOMAIN,
    MAX_FRESHNESS_HOURS,
    MAX_REVIEW_LEAD_DAYS,
    MIN_FRESHNESS_HOURS,
    MIN_REVIEW_LEAD_DAYS,
    PLAN_BUDGET_BASIS_PERIOD,
    PLAN_FREQUENCY_MONTHLY,
    SOURCE_TYPE_LEGACY_SENSOR,
    SOURCE_TYPE_LOCAL_FILES,
    SOURCE_TYPE_REST_API,
)
from .decision_trace import (
    DecisionTraceError,
    EvaluationHistory,
    PlanDelta,
    advance_history,
    build_evaluation_snapshot,
    compare_history,
)
from .decision_trace_store import DecisionTraceStore
from .engine import calculate_portfolio_payload_from_positions
from .engine.aggregation import (
    AggregationResult,
    PortfolioSourceSnapshot,
    PROVIDER_MULTI_SOURCE,
    aggregate_sources,
)
from .engine.calculator import configuration_files
from .engine.importers import (
    CsvSourceConfig,
    PROVIDER_COMDIRECT,
    PROVIDER_DKB,
    dkb_export_timestamp,
    read_positions,
    select_latest_dkb_exports,
)
from .engine.models import Position
from .engine.rest import PROVIDER_LOCAL_REST_JSON, RestInvestmentCash
from .last_known_good import RestLastKnownGoodStore, configuration_fingerprint
from .model import PortfolioArchitectDataError, PortfolioData, parse_portfolio_data
from .resilience import (
    refresh_overdue_is_evidenced,
    snapshot_age_seconds,
    snapshot_expires_in_seconds,
    snapshot_within_retention,
)
from .rest_client import (
    PortfolioRestAuthenticationError,
    PortfolioRestError,
    PortfolioRestRateLimitError,
    GatewayHealth,
    RestSourceConfig,
    async_fetch_gateway_health,
    async_fetch_rest_snapshot,
)
from .schedule import (
    PlanReviewSchedule,
    PlanScheduleConfig,
    calculate_plan_review_schedule,
    validate_schedule_config,
)
from .source import (
    LocalConfigurationPath,
    LocalSourcePaths,
    SupplementalCsvPath,
    csv_source_config_from_data,
    resolve_configuration_directory,
    resolve_local_source_paths,
    resolve_supplemental_csv_paths,
)

_LOGGER = logging.getLogger(__name__)


class PortfolioArchitectCoordinator(TimestampDataUpdateCoordinator[PortfolioData]):
    """Calculate, validate, and publish Portfolio Architect data."""

    source_last_changed: datetime | None = None
    source_last_updated: datetime | None = None
    last_valid_source_updated: datetime | None = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.source_type = entry.data.get(CONF_SOURCE_TYPE, SOURCE_TYPE_LEGACY_SENSOR)
        update_interval = (
            timedelta(minutes=DEFAULT_UPDATE_INTERVAL_MINUTES)
            if self.source_type in {SOURCE_TYPE_LOCAL_FILES, SOURCE_TYPE_REST_API}
            else None
        )
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=update_interval,
            always_update=True,
        )

        self.source_entity_id: str | None = None
        self.local_paths: LocalSourcePaths | None = None
        self.configuration_path: LocalConfigurationPath | None = None
        self.csv_source_config: CsvSourceConfig = CsvSourceConfig(
            provider=PROVIDER_COMDIRECT
        )
        self.rest_source_config: RestSourceConfig | None = None
        self.positions: dict[str, Position] = {}
        self.primary_positions: dict[str, Position] = {}
        self.source_summaries: tuple[dict[str, Any], ...] = ()
        self.source_conflicts: tuple[dict[str, Any], ...] = ()
        self.oldest_source_generated_at: datetime | None = None
        self.newest_source_generated_at: datetime | None = None
        self.supplemental_dkb_paths: tuple[SupplementalCsvPath, ...] = resolve_supplemental_csv_paths(
            hass,
            entry.options.get(CONF_SUPPLEMENTAL_DKB_CSV_PATHS, []),
            require_exists=False,
            maximum=MAX_SUPPLEMENTAL_SOURCES,
        )
        self._rest_etag: str | None = None
        self._rest_last_modified: str | None = None
        self._rest_snapshot_generated_at: datetime | None = None
        self._rest_snapshot_sha256: str | None = None
        self._rest_snapshot_position_count: int | None = None
        self._rest_investment_reserve_eur = None
        self._rest_investment_reserve_as_of: datetime | None = None
        self._rest_investment_cash: RestInvestmentCash | None = None
        self.rest_snapshot_integrity_verified: bool | None = None
        self.rest_snapshot_integrity_error: str | None = None
        self._last_configuration_modified: datetime | None = None
        self.gateway_health: GatewayHealth | None = None
        self.gateway_health_error: str | None = None
        self._gateway_health_observed_at: datetime | None = None
        self._gateway_max_cached_snapshot_age_seconds: int | None = None
        self._last_known_good_store: RestLastKnownGoodStore | None = None
        self._last_known_good_payload: dict[str, Any] | None = None
        self._last_known_good_configuration_sha256: str | None = None
        self._using_home_assistant_last_known_good = False
        self._decision_trace_store = DecisionTraceStore(hass, entry.entry_id)
        self._decision_history = EvaluationHistory()
        self.plan_delta: PlanDelta | None = None
        self._home_assistant_cache_failure_count = 0
        self._home_assistant_cache_last_failure_at: datetime | None = None
        self._gateway_reauth_issue_id = f"gateway_reauthentication_required_{entry.entry_id}"
        self._gateway_repeated_failures_issue_id = (
            f"gateway_repeated_refresh_failures_{entry.entry_id}"
        )
        self._gateway_snapshot_unavailable_issue_id = (
            f"gateway_snapshot_unavailable_{entry.entry_id}"
        )
        self._gateway_refresh_overdue_issue_id = (
            f"gateway_refresh_overdue_{entry.entry_id}"
        )
        self._gateway_integrity_issue_id = (
            f"gateway_snapshot_integrity_failure_{entry.entry_id}"
        )

        if self.source_type == SOURCE_TYPE_LOCAL_FILES:
            self.csv_source_config = csv_source_config_from_data(dict(entry.data))
            self.local_paths = resolve_local_source_paths(
                hass,
                entry.data.get(CONF_CSV_PATH, DEFAULT_CSV_PATH),
                entry.data.get(CONF_CONFIG_DIRECTORY, DEFAULT_CONFIG_DIRECTORY),
                require_exists=False,
            )
        elif self.source_type == SOURCE_TYPE_REST_API:
            self.rest_source_config = RestSourceConfig.from_mapping(dict(entry.data))
            self._last_known_good_store = RestLastKnownGoodStore(hass, entry.entry_id)
            self.configuration_path = resolve_configuration_directory(
                hass,
                entry.data.get(CONF_CONFIG_DIRECTORY, DEFAULT_CONFIG_DIRECTORY),
                require_exists=False,
            )
        else:
            self.source_entity_id = entry.data.get(
                CONF_SOURCE_ENTITY_ID, DEFAULT_SOURCE_ENTITY_ID
            )

        self.freshness_hours = _bounded_int(
            entry.options.get(CONF_FRESHNESS_HOURS),
            default=DEFAULT_FRESHNESS_HOURS,
            minimum=MIN_FRESHNESS_HOURS,
            maximum=MAX_FRESHNESS_HOURS,
        )
        self.review_lead_days = _bounded_int(
            entry.options.get(CONF_REVIEW_LEAD_DAYS),
            default=DEFAULT_REVIEW_LEAD_DAYS,
            minimum=MIN_REVIEW_LEAD_DAYS,
            maximum=MAX_REVIEW_LEAD_DAYS,
        )
        self.plan_override = _plan_override_from_entry(entry)
        self.schedule_config = _schedule_config_from_entry(entry)

    async def async_restore_decision_trace(self) -> bool:
        """Restore the bounded two-evaluation trace before the first refresh."""
        history = await self._decision_trace_store.async_load()
        if history is None:
            return False
        self._decision_history = history
        self.plan_delta = compare_history(history)
        _LOGGER.info("Restored Portfolio Architect decision trace from private storage")
        return self.plan_delta is not None

    @property
    def using_home_assistant_last_known_good(self) -> bool:
        """Return whether HA is serving its private validated cache after live degradation."""
        return self._using_home_assistant_last_known_good

    async def async_restore_last_known_good(self) -> bool:
        """Restore one strictly validated REST calculation before the first refresh."""
        if (
            self.source_type != SOURCE_TYPE_REST_API
            or self.rest_source_config is None
            or self.configuration_path is None
            or self._last_known_good_store is None
        ):
            return False
        try:
            configuration_modified, configuration_sha256 = (
                await self.hass.async_add_executor_job(
                    _configuration_metadata,
                    self.configuration_path.config_directory,
                    self.plan_override,
                    tuple(item.relative for item in self.supplemental_dkb_paths),
                )
            )
            cached = await self._last_known_good_store.async_load(
                endpoint_url=self.rest_source_config.endpoint_url,
                configuration_sha256=configuration_sha256,
            )
            if cached is None:
                return False
            if not snapshot_within_retention(
                cached.snapshot_generated_at,
                maximum_age_seconds=self.home_assistant_lkg_max_age_seconds,
                now=dt_util.utcnow(),
            ):
                _LOGGER.info(
                    "Ignoring Portfolio Architect last-known-good cache beyond its retention window"
                )
                return False
            data = _parse_payload(cached.payload)
        except (OSError, ValueError, PortfolioArchitectDataError) as err:
            _LOGGER.warning("Ignoring invalid Portfolio Architect last-known-good cache: %s", err)
            return False

        self._last_known_good_payload = cached.payload
        self._last_known_good_configuration_sha256 = configuration_sha256
        self._last_configuration_modified = configuration_modified
        self._rest_snapshot_generated_at = cached.snapshot_generated_at
        self._rest_snapshot_sha256 = cached.snapshot_sha256
        self._rest_snapshot_position_count = cached.snapshot_position_count
        self.rest_snapshot_integrity_verified = (
            True if cached.snapshot_sha256 is not None else None
        )
        self.rest_snapshot_integrity_error = None
        self.source_last_changed = cached.snapshot_generated_at
        self.source_last_updated = cached.saved_at
        self.last_valid_source_updated = cached.snapshot_generated_at
        self.data = data
        self._restore_source_metadata_from_payload(cached.payload)
        self._using_home_assistant_last_known_good = True
        _LOGGER.info(
            "Restored Portfolio Architect last-known-good calculation from private Home Assistant storage"
        )
        return True

    @property
    def data_timestamp(self) -> datetime | None:
        """Return the portfolio snapshot timestamp with safe fallbacks."""
        if self.data is not None and self.data.runtime.generated_at is not None:
            return self.data.runtime.generated_at
        return self.last_valid_source_updated or self.last_update_success_time

    @property
    def source_label(self) -> str:
        """Return a privacy-conscious description of the effective source set."""
        if self.source_summaries:
            if len(self.source_summaries) > 1:
                return f"{len(self.source_summaries)} sources"
            label = self.source_summaries[0].get("label")
            if isinstance(label, str) and label:
                return label
        if self.supplemental_dkb_paths:
            return "Multi-source portfolio"
        if self.local_paths is not None:
            return self.local_paths.csv_relative
        if self.rest_source_config is not None:
            return _endpoint_source_label(self.rest_source_config.endpoint_url)
        return self.source_entity_id or "unconfigured"

    @property
    def source_provider(self) -> str:
        """Return the explicit provider adapter."""
        if self.supplemental_dkb_paths:
            return PROVIDER_MULTI_SOURCE
        if self.rest_source_config is not None:
            return PROVIDER_LOCAL_REST_JSON
        return self.csv_source_config.provider

    @property
    def source_adapter_diagnostics(self) -> dict[str, Any]:
        """Return bounded source-adapter diagnostics without credentials."""
        base = (
            self.rest_source_config.as_public_dict()
            if self.rest_source_config is not None
            else self.csv_source_config.as_public_dict()
        )
        effective_dkb_count = sum(
            1
            for item in self.source_summaries
            if isinstance(item, dict) and item.get("provider") == PROVIDER_DKB
        )
        return {
            **base,
            "configured_supplemental_path_count": len(self.supplemental_dkb_paths),
            "supplemental_source_count": (
                effective_dkb_count
                if self.source_summaries
                else len(self.supplemental_dkb_paths)
            ),
            "supplemental_providers": [PROVIDER_DKB] * (
                effective_dkb_count
                if self.source_summaries
                else len(self.supplemental_dkb_paths)
            ),
        }

    @property
    def source_count(self) -> int:
        """Return the number of independent portfolio sources in the aggregate."""
        return len(self.source_summaries) if self.source_summaries else 1

    @property
    def source_conflict_count(self) -> int:
        """Return the number of bounded cross-source identity warnings."""
        return len(self.source_conflicts)

    @property
    def gateway_status(self) -> str:
        """Return the effective Gateway status for the data PA is serving."""
        if self.source_type != SOURCE_TYPE_REST_API:
            return "not_configured"
        if self._using_home_assistant_last_known_good:
            return "degraded"
        if self.gateway_health is None:
            return "unavailable"
        return self.gateway_health.status

    @property
    def gateway_snapshot_generated_at(self) -> datetime | None:
        """Return the timestamp of the snapshot PA has actually accepted."""
        if self._rest_snapshot_generated_at is not None:
            return self._rest_snapshot_generated_at
        if self.gateway_health is not None:
            return self.gateway_health.snapshot_generated_at
        return None

    @property
    def gateway_health_observed_at(self) -> datetime | None:
        """Return when PA last obtained a validated Gateway health document."""
        return self._gateway_health_observed_at

    @property
    def home_assistant_lkg_max_age_seconds(self) -> int:
        """Return the bounded informational retention window for HA-private LKG."""
        advertised = self._gateway_max_cached_snapshot_age_seconds
        if advertised is not None and advertised > 0:
            return advertised
        return DEFAULT_HOME_ASSISTANT_LKG_MAX_AGE_SECONDS

    @property
    def rest_snapshot_sha256(self) -> str | None:
        """Return the accepted live snapshot fingerprint."""
        return self._rest_snapshot_sha256

    @property
    def rest_snapshot_position_count(self) -> int | None:
        """Return the accepted live snapshot position count."""
        return self._rest_snapshot_position_count

    @property
    def gateway_reauthentication_required(self) -> bool | None:
        """Return whether Comdirect needs another interactive PhotoTAN bootstrap."""
        if self.source_type != SOURCE_TYPE_REST_API or self.gateway_health is None:
            return None
        return self.gateway_health.reauthentication_required

    @property
    def gateway_operating_mode(self) -> str:
        """Return the effective live-data operating mode for PA's active data."""
        if self.source_type != SOURCE_TYPE_REST_API:
            return "not_configured"
        if self._using_home_assistant_last_known_good and self.data is not None:
            return "last_known_good"
        health = self.gateway_health
        if health is None:
            return "unavailable"
        if health.operating_mode is not None:
            return health.operating_mode
        if health.reauthentication_required:
            return "reauthentication_required"
        if health.status == "ok" and health.snapshot_available:
            return "live"
        if health.snapshot_available:
            return "last_known_good"
        return "unavailable"

    @property
    def gateway_snapshot_age_seconds(self) -> int | None:
        """Return locally derived age of the snapshot PA actually accepted."""
        return snapshot_age_seconds(
            self.gateway_snapshot_generated_at,
            now=dt_util.utcnow(),
        )

    @property
    def gateway_snapshot_expires_in_seconds(self) -> int | None:
        """Return locally derived remaining informational retention time."""
        maximum = None
        if self.gateway_health is not None:
            maximum = self.gateway_health.max_cached_snapshot_age_seconds
        if (maximum is None or maximum <= 0) and self._using_home_assistant_last_known_good:
            maximum = self.home_assistant_lkg_max_age_seconds
        return snapshot_expires_in_seconds(
            self.gateway_snapshot_generated_at,
            maximum_age_seconds=maximum,
            now=dt_util.utcnow(),
        )

    @property
    def gateway_consecutive_refresh_failures(self) -> int | None:
        """Return the current consecutive live-refresh failure count."""
        health = self.gateway_health
        if health is None:
            return (
                self._home_assistant_cache_failure_count
                if self._using_home_assistant_last_known_good
                else None
            )
        return health.consecutive_refresh_failures

    @property
    def gateway_using_last_known_good_snapshot(self) -> bool | None:
        """Return whether calculations use cached rather than newly live bank data."""
        if self.source_type != SOURCE_TYPE_REST_API:
            return None
        if self.data is None:
            return None
        if self._using_home_assistant_last_known_good:
            return True
        health = self.gateway_health
        if health is None:
            return False
        return bool(
            health.snapshot_available
            and (
                health.operating_mode == "last_known_good"
                or health.reauthentication_required
            )
        )

    @property
    def gateway_refresh_in_progress(self) -> bool | None:
        """Return whether the Gateway is currently executing one refresh."""
        health = self.gateway_health
        if health is None:
            return None
        return health.refresh_in_progress

    @property
    def gateway_last_refresh_duration_seconds(self) -> float | None:
        """Return the duration of the most recently completed refresh."""
        health = self.gateway_health
        if health is None or health.last_refresh_duration_ms is None:
            return None
        return health.last_refresh_duration_ms / 1000

    @property
    def gateway_last_refresh_trigger(self) -> str | None:
        """Return what initiated the most recent refresh attempt."""
        health = self.gateway_health
        if health is None:
            return None
        return health.last_refresh_trigger

    @property
    def gateway_next_refresh_due_at(self) -> datetime | None:
        """Return the fixed-cadence next scheduled refresh time."""
        health = self.gateway_health
        if health is None:
            return None
        return health.next_refresh_due_at

    @property
    def gateway_last_refresh_failure_at(self) -> datetime | None:
        """Return when the active consecutive refresh-failure run began or advanced."""
        health = self.gateway_health
        if health is None:
            return self._home_assistant_cache_last_failure_at
        return health.last_refresh_failure_at

    @property
    def gateway_last_refresh_failure_class(self) -> str | None:
        """Return the sanitized class of the most recent live-refresh failure."""
        health = self.gateway_health
        if health is None:
            return "transport_error" if self._using_home_assistant_last_known_good else None
        return health.last_refresh_failure_class

    @property
    def gateway_refresh_grace_seconds(self) -> int | None:
        """Return the bounded scheduling grace period used for overdue detection."""
        health = self.gateway_health
        if health is None or health.next_refresh_due_at is None:
            return None
        poll_interval = health.poll_interval_seconds or (DEFAULT_UPDATE_INTERVAL_MINUTES * 60)
        return max(60, min(poll_interval // 4, 300))

    def is_gateway_refresh_overdue(self, now: datetime | None = None) -> bool | None:
        """Return overdue only when a fresh health observation proves the miss."""
        health = self.gateway_health
        if health is None:
            return None
        return refresh_overdue_is_evidenced(
            next_refresh_due_at=health.next_refresh_due_at,
            health_observed_at=self._gateway_health_observed_at,
            refresh_in_progress=health.refresh_in_progress,
            grace_seconds=self.gateway_refresh_grace_seconds,
            now=now or dt_util.utcnow(),
        )

    @property
    def gateway_refresh_overdue_evidence_current(self) -> bool | None:
        """Return whether the latest health sample is new enough to prove overdue."""
        health = self.gateway_health
        grace_seconds = self.gateway_refresh_grace_seconds
        observed = self._gateway_health_observed_at
        if (
            health is None
            or health.next_refresh_due_at is None
            or grace_seconds is None
            or observed is None
        ):
            return None
        threshold = health.next_refresh_due_at + timedelta(seconds=grace_seconds)
        return observed >= threshold

    @property
    def gateway_attention_reason(self) -> str:
        """Return one stable, priority-ordered operational attention reason."""
        if self.source_type != SOURCE_TYPE_REST_API:
            return "not_configured"
        health = self.gateway_health
        if health is None:
            return (
                "transport_error"
                if self._using_home_assistant_last_known_good
                else "health_unavailable"
            )
        if health.reauthentication_required:
            return "reauthentication_required"
        if self.rest_snapshot_integrity_error is not None:
            return "integrity_failure"
        if self.gateway_operating_mode == "unavailable":
            return "snapshot_unavailable"
        if self.is_gateway_refresh_overdue():
            return "refresh_overdue"
        if self.gateway_operating_mode == "last_known_good":
            return health.last_refresh_failure_class or "last_known_good"
        return "none"

    @property
    def gateway_attention_required(self) -> bool | None:
        """Return whether live-source operation requires operator attention."""
        if self.source_type != SOURCE_TYPE_REST_API:
            return None
        return self.gateway_attention_reason != "none"

    @property
    def gateway_recommended_action(self) -> str:
        """Return one stable recovery action for the current attention reason."""
        health = self.gateway_health
        if health is not None and health.recommended_action not in {None, "none"}:
            return health.recommended_action
        reason = self.gateway_attention_reason
        if reason == "none":
            return "none"
        if reason == "reauthentication_required":
            return "reauthenticate"
        if reason in {"health_unavailable", "transport_error"}:
            return "check_connectivity"
        if reason in {"rate_limited", "remote_service_error", "last_known_good"}:
            return "wait"
        if reason == "configuration_error":
            return "fix_configuration"
        return "inspect_logs"

    def _sync_gateway_issues(self) -> None:
        """Create or dismiss bounded, actionable live-source repair issues."""
        issue_ids = (
            self._gateway_reauth_issue_id,
            self._gateway_repeated_failures_issue_id,
            self._gateway_snapshot_unavailable_issue_id,
            self._gateway_refresh_overdue_issue_id,
            self._gateway_integrity_issue_id,
        )
        if self.source_type != SOURCE_TYPE_REST_API:
            for issue_id in issue_ids:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return

        health = self.gateway_health
        if health is not None:
            self._set_gateway_issue(
                issue_id=self._gateway_reauth_issue_id,
                active=health.reauthentication_required,
                severity=ir.IssueSeverity.WARNING,
                translation_key="gateway_reauthentication_required",
            )
            self._set_gateway_issue(
                issue_id=self._gateway_repeated_failures_issue_id,
                active=(
                    not health.reauthentication_required
                    and self.gateway_operating_mode == "last_known_good"
                    and (health.consecutive_refresh_failures or 0) >= 3
                ),
                severity=ir.IssueSeverity.WARNING,
                translation_key="gateway_repeated_refresh_failures",
            )
            self._set_gateway_issue(
                issue_id=self._gateway_snapshot_unavailable_issue_id,
                active=(self.gateway_operating_mode == "unavailable"),
                severity=ir.IssueSeverity.ERROR,
                translation_key="gateway_snapshot_unavailable",
            )
            self._set_gateway_issue(
                issue_id=self._gateway_refresh_overdue_issue_id,
                active=(self.is_gateway_refresh_overdue() is True),
                severity=ir.IssueSeverity.WARNING,
                translation_key="gateway_refresh_overdue",
            )
        elif self._using_home_assistant_last_known_good:
            # A transport outage cannot prove that Comdirect authentication is
            # invalid. Remove any stale reauthentication issue and report the
            # currently observable connectivity condition instead.
            self._set_gateway_issue(
                issue_id=self._gateway_reauth_issue_id,
                active=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="gateway_reauthentication_required",
            )
            self._set_gateway_issue(
                issue_id=self._gateway_repeated_failures_issue_id,
                active=self._home_assistant_cache_failure_count >= 3,
                severity=ir.IssueSeverity.WARNING,
                translation_key="gateway_repeated_refresh_failures",
            )
            self._set_gateway_issue(
                issue_id=self._gateway_snapshot_unavailable_issue_id,
                active=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="gateway_snapshot_unavailable",
            )
            self._set_gateway_issue(
                issue_id=self._gateway_refresh_overdue_issue_id,
                active=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="gateway_refresh_overdue",
            )

        self._set_gateway_issue(
            issue_id=self._gateway_integrity_issue_id,
            active=(self.rest_snapshot_integrity_error is not None),
            severity=ir.IssueSeverity.ERROR,
            translation_key="gateway_snapshot_integrity_failure",
        )

    def _set_gateway_issue(
        self,
        *,
        issue_id: str,
        active: bool,
        severity: ir.IssueSeverity,
        translation_key: str,
    ) -> None:
        """Set one issue to the supplied state without duplicating registry logic."""
        if active:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                issue_domain=DOMAIN,
                severity=severity,
                translation_key=translation_key,
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    @property
    def configuration_label(self) -> str | None:
        """Return the relative local YAML configuration directory."""
        if self.local_paths is not None:
            return self.local_paths.config_relative
        if self.configuration_path is not None:
            return self.configuration_path.config_relative
        return None

    @property
    def freshness_mode(self) -> str:
        """Return the active freshness policy."""
        return "review_schedule" if self.review_schedule_configured else "age_threshold"

    def is_data_fresh(self, now: datetime | None = None) -> bool:
        """Return whether the last validated snapshot is still actionable."""
        timestamp = self.oldest_source_generated_at or self.data_timestamp
        if timestamp is None:
            return False
        current = now or dt_util.utcnow()
        age = current - timestamp
        if age < timedelta(minutes=-5):
            return False

        schedule = self.plan_review_schedule()
        if schedule is not None:
            current_date = dt_util.as_local(current).date()
            return current_date <= schedule.next_review_on
        return age <= timedelta(hours=self.freshness_hours)

    @property
    def plan_actionable(self) -> bool:
        """Return whether current source evidence may drive a new investment action."""
        if self.data is None or not self.is_data_fresh():
            return False
        if self.source_type != SOURCE_TYPE_REST_API:
            return True
        if self._using_home_assistant_last_known_good:
            return False
        if self.rest_snapshot_integrity_error is not None:
            return False
        health = self.gateway_health
        if health is None or health.reauthentication_required:
            return False
        return self.gateway_operating_mode == "live"

    @property
    def plan_actionability_reason(self) -> str:
        """Return one bounded reason for the current plan-actionability decision."""
        if self.data is None:
            return "data_unavailable"
        if not self.is_data_fresh():
            return "data_stale"
        if self.source_type != SOURCE_TYPE_REST_API:
            return "actionable"
        if self.rest_snapshot_integrity_error is not None:
            return "integrity_failure"
        if self._using_home_assistant_last_known_good:
            return "last_known_good"
        health = self.gateway_health
        if health is None:
            return "health_unavailable"
        if health.reauthentication_required:
            return "reauthentication_required"
        if self.gateway_operating_mode != "live":
            return "source_degraded"
        return "actionable"

    @property
    def review_schedule_configured(self) -> bool:
        """Return whether a recurring execution schedule has been configured."""
        return self.schedule_config is not None

    @property
    def plan_frequency(self) -> str:
        """Return the configured or calculated plan frequency."""
        if self.schedule_config is not None:
            return self.schedule_config.frequency
        if self.data is not None:
            return self.data.monthly_plan.frequency
        return PLAN_FREQUENCY_MONTHLY

    @property
    def plan_execution_days(self) -> tuple[int, ...]:
        """Return configured execution day tokens."""
        return self.schedule_config.execution_days if self.schedule_config else ()

    @property
    def plan_execution_day(self) -> int | None:
        """Return the single legacy monthly execution day, when applicable."""
        if (
            self.schedule_config is not None
            and self.schedule_config.frequency == PLAN_FREQUENCY_MONTHLY
            and len(self.schedule_config.execution_days) == 1
        ):
            return self.schedule_config.execution_days[0]
        return None

    def plan_review_schedule(self) -> PlanReviewSchedule | None:
        """Return the review cycle derived from the last valid evaluation."""
        timestamp = self.oldest_source_generated_at or self.data_timestamp
        if timestamp is None or self.schedule_config is None:
            return None
        evaluated_on = dt_util.as_local(timestamp).date()
        return calculate_plan_review_schedule(
            evaluated_on,
            self.schedule_config,
            self.review_lead_days,
        )

    def is_plan_review_due(self, now: datetime | None = None) -> bool:
        """Return whether a new portfolio evaluation is due."""
        schedule = self.plan_review_schedule()
        if schedule is None:
            return False
        current = dt_util.as_local(now or dt_util.utcnow()).date()
        return schedule.is_due(current)

    async def _async_update_data(self) -> PortfolioData:
        """Calculate or read the configured source and validate its payload."""
        if self.source_type == SOURCE_TYPE_LOCAL_FILES:
            data = await self._async_update_local_files()
        elif self.source_type == SOURCE_TYPE_REST_API:
            data = await self._async_update_rest_api()
        else:
            data = self._update_legacy_sensor()

        # A degraded REST refresh deliberately republishes the already stored
        # last-known-good calculation. It must never advance the decision trace
        # or masquerade as a new portfolio evaluation.
        if not self._using_home_assistant_last_known_good:
            await self._async_record_decision_trace(data)
        return data

    async def _async_record_decision_trace(self, data: PortfolioData) -> None:
        """Advance and persist the two-evaluation trace after a fresh validation."""
        evaluated_at = (
            data.runtime.generated_at
            or self.last_valid_source_updated
            or self.source_last_updated
            or dt_util.utcnow()
        )
        try:
            snapshot = build_evaluation_snapshot(
                data,
                evaluated_at=evaluated_at,
                source_provider=self.source_provider,
                source_count=self.source_count,
                source_conflict_count=self.source_conflict_count,
            )
            history, changed = advance_history(self._decision_history, snapshot)
            if not changed:
                return
            self._decision_history = history
            self.plan_delta = compare_history(history)
            await self._decision_trace_store.async_save(history)
        except DecisionTraceError as err:
            _LOGGER.warning("Could not derive Portfolio Architect decision trace: %s", err)
        except Exception as err:  # Trace persistence is non-authoritative.
            _LOGGER.warning(
                "Could not update Portfolio Architect decision-trace storage: %s",
                type(err).__name__,
            )

    async def _async_update_local_files(self) -> PortfolioData:
        """Calculate one portfolio snapshot from confined local files."""
        if self.local_paths is None:
            raise UpdateFailed("Local portfolio source paths are not configured")
        try:
            (
                payload,
                csv_modified,
                latest_input_modified,
                primary_positions,
                aggregation,
            ) = await self.hass.async_add_executor_job(
                _calculate_local_payload,
                self.local_paths.csv_path,
                self.local_paths.config_directory,
                self.plan_override,
                self.csv_source_config,
                self.supplemental_dkb_paths,
            )
            data = _parse_payload(payload)
        except (OSError, ValueError, PortfolioArchitectDataError) as err:
            raise UpdateFailed(str(err)) from err

        self.primary_positions = dict(primary_positions)
        self._apply_aggregation(aggregation)
        self.source_last_changed = csv_modified
        self.source_last_updated = latest_input_modified
        self.last_valid_source_updated = csv_modified
        self.gateway_health = None
        self.gateway_health_error = None
        self._gateway_health_observed_at = None
        self._rest_snapshot_sha256 = None
        self._rest_snapshot_position_count = None
        self.rest_snapshot_integrity_verified = None
        self.rest_snapshot_integrity_error = None
        self._sync_gateway_issues()
        return data

    async def _async_update_rest_api(self) -> PortfolioData:
        """Fetch REST data and retain HA-private validated data on live-source degradation."""
        if self.rest_source_config is None or self.configuration_path is None:
            raise UpdateFailed("Local REST portfolio source is not configured")

        try:
            configuration_modified, configuration_sha256 = (
                await self.hass.async_add_executor_job(
                    _configuration_metadata,
                    self.configuration_path.config_directory,
                    self.plan_override,
                    tuple(item.relative for item in self.supplemental_dkb_paths),
                )
            )
        except (OSError, ValueError) as err:
            raise UpdateFailed(str(err)) from err

        try:
            try:
                self.gateway_health = await async_fetch_gateway_health(
                    self.hass, self.rest_source_config
                )
                self._gateway_health_observed_at = dt_util.utcnow()
                if self.gateway_health.max_cached_snapshot_age_seconds is not None:
                    self._gateway_max_cached_snapshot_age_seconds = (
                        self.gateway_health.max_cached_snapshot_age_seconds
                    )
                self.gateway_health_error = None
                self._sync_gateway_issues()
            except PortfolioRestAuthenticationError:
                raise
            except PortfolioRestError as health_err:
                self.gateway_health = None
                self._gateway_health_observed_at = None
                self.gateway_health_error = str(health_err)
            result = await async_fetch_rest_snapshot(
                self.hass,
                self.rest_source_config,
                etag=self._rest_etag,
                last_modified=self._rest_last_modified,
            )
        except PortfolioRestAuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PortfolioRestRateLimitError as err:
            return self._use_home_assistant_last_known_good(
                str(err),
                configuration_sha256=configuration_sha256,
                retry_after=float(
                    err.retry_after or DEFAULT_UPDATE_INTERVAL_MINUTES * 60
                ),
            )
        except (OSError, ValueError, PortfolioRestError) as err:
            return self._use_home_assistant_last_known_good(
                str(err), configuration_sha256=configuration_sha256
            )

        snapshot = result.snapshot
        reuse_existing_data = False
        if snapshot is None:
            if (
                self.data is None
                or not self.positions
                or self._rest_snapshot_generated_at is None
            ):
                return self._use_home_assistant_last_known_good(
                    "Local REST source returned not modified before a live snapshot existed",
                    configuration_sha256=configuration_sha256,
                )
            reuse_existing_data = (
                self._last_configuration_modified is not None
                and configuration_modified <= self._last_configuration_modified
                and not self.supplemental_dkb_paths
            )
            positions = self.primary_positions
            generated_at = self._rest_snapshot_generated_at
        else:
            positions = snapshot.positions
            generated_at = snapshot.generated_at
            self._rest_investment_reserve_eur = snapshot.investment_reserve_eur
            self._rest_investment_reserve_as_of = snapshot.investment_reserve_as_of
            self._rest_investment_cash = snapshot.investment_cash
            if (
                self._rest_snapshot_generated_at is not None
                and generated_at < self._rest_snapshot_generated_at
            ):
                message = (
                    "Local REST source attempted to replace the accepted snapshot "
                    "with an older snapshot"
                )
                self.rest_snapshot_integrity_error = message
                self._sync_gateway_issues()
                return self._use_home_assistant_last_known_good(
                    message,
                    configuration_sha256=configuration_sha256,
                    integrity_failure=True,
                )

        try:
            integrity_verified = self._validate_rest_snapshot_integrity(
                result=result,
                generated_at=generated_at,
                position_count=len(positions),
            )
        except PortfolioRestError as err:
            self.rest_snapshot_integrity_error = str(err)
            self._sync_gateway_issues()
            return self._use_home_assistant_last_known_good(
                str(err),
                configuration_sha256=configuration_sha256,
                integrity_failure=True,
            )

        if reuse_existing_data:
            if result.snapshot_sha256 is not None:
                self._rest_snapshot_sha256 = result.snapshot_sha256
            if result.position_count is not None:
                self._rest_snapshot_position_count = result.position_count
            self.rest_snapshot_integrity_verified = integrity_verified
            self.rest_snapshot_integrity_error = None
            self._rest_etag = result.etag or self._rest_etag
            self._rest_last_modified = result.last_modified or self._rest_last_modified
            self.source_last_updated = dt_util.utcnow()
            self._using_home_assistant_last_known_good = False
            self._home_assistant_cache_failure_count = 0
            self._home_assistant_cache_last_failure_at = None
            self._sync_gateway_issues()
            return self.data

        try:
            payload, aggregation = await self.hass.async_add_executor_job(
                _calculate_rest_payload,
                positions,
                self.configuration_path.config_directory,
                self.plan_override,
                generated_at,
                self.rest_source_config.endpoint_url,
                self.supplemental_dkb_paths,
                self._rest_investment_reserve_eur,
                self._rest_investment_reserve_as_of,
                self._rest_investment_cash,
            )
            data = _parse_payload(payload)
        except SupplementalPortfolioSourceError as err:
            return self._use_home_assistant_last_known_good(
                f"Supplemental portfolio source failed: {err}",
                configuration_sha256=configuration_sha256,
            )
        except (OSError, ValueError, PortfolioArchitectDataError) as err:
            return self._use_home_assistant_last_known_good(
                f"Portfolio calculation failed: {err}",
                configuration_sha256=configuration_sha256,
            )

        self.primary_positions = dict(positions)
        self._apply_aggregation(aggregation)
        self._rest_snapshot_generated_at = generated_at
        if result.snapshot_sha256 is not None:
            self._rest_snapshot_sha256 = result.snapshot_sha256
        if result.position_count is not None:
            self._rest_snapshot_position_count = result.position_count
        self.rest_snapshot_integrity_verified = integrity_verified
        self.rest_snapshot_integrity_error = None
        self._rest_etag = result.etag or self._rest_etag
        self._rest_last_modified = result.last_modified or self._rest_last_modified
        self._last_configuration_modified = configuration_modified
        self.source_last_changed = generated_at
        self.source_last_updated = max(generated_at, configuration_modified)
        self.last_valid_source_updated = generated_at
        self._using_home_assistant_last_known_good = False
        self._home_assistant_cache_failure_count = 0
        self._home_assistant_cache_last_failure_at = None
        self._last_known_good_payload = payload
        self._last_known_good_configuration_sha256 = configuration_sha256
        if self._last_known_good_store is not None:
            try:
                await self._last_known_good_store.async_save(
                    payload=payload,
                    endpoint_url=self.rest_source_config.endpoint_url,
                    configuration_sha256=configuration_sha256,
                    snapshot_generated_at=generated_at,
                    snapshot_sha256=self._rest_snapshot_sha256,
                    snapshot_position_count=self._rest_snapshot_position_count,
                )
            except Exception as err:  # Cache persistence is non-authoritative.
                _LOGGER.warning(
                    "Could not update Portfolio Architect last-known-good cache: %s",
                    type(err).__name__,
                )
        self._sync_gateway_issues()
        return data

    def _use_home_assistant_last_known_good(
        self,
        message: str,
        *,
        configuration_sha256: str,
        retry_after: float | None = None,
        integrity_failure: bool = False,
    ) -> PortfolioData:
        """Publish the private HA cache as a successful degraded coordinator update."""
        # Integrity errors describe evidence from the current refresh attempt.
        # Do not carry an older mismatch into an unrelated transport, bank-auth,
        # or calculation failure. The fingerprint of the last accepted snapshot
        # remains preserved separately and is still checked on the next live read.
        if not integrity_failure:
            self.rest_snapshot_integrity_error = None
        if (
            self._last_known_good_payload is None
            or self._last_known_good_configuration_sha256 != configuration_sha256
            or self._rest_snapshot_generated_at is None
        ):
            if retry_after is not None:
                raise UpdateFailed(message, retry_after=retry_after)
            raise UpdateFailed(message)
        if not snapshot_within_retention(
            self._rest_snapshot_generated_at,
            maximum_age_seconds=self.home_assistant_lkg_max_age_seconds,
            now=dt_util.utcnow(),
        ):
            expired = "Stored last-known-good portfolio snapshot exceeded its retention window"
            if retry_after is not None:
                raise UpdateFailed(expired, retry_after=retry_after)
            raise UpdateFailed(expired)
        try:
            data = _parse_payload(self._last_known_good_payload)
        except PortfolioArchitectDataError as err:
            raise UpdateFailed("Stored last-known-good portfolio payload is invalid") from err
        if self.gateway_health is None:
            self.gateway_health_error = message
        self._using_home_assistant_last_known_good = True
        self._home_assistant_cache_failure_count += 1
        self._home_assistant_cache_last_failure_at = dt_util.utcnow()
        self.source_last_changed = self._rest_snapshot_generated_at
        self.source_last_updated = self._rest_snapshot_generated_at
        self.last_valid_source_updated = self._rest_snapshot_generated_at
        self._sync_gateway_issues()
        _LOGGER.warning(
            "Live source degraded; retaining the validated Home Assistant last-known-good calculation"
        )
        return data

    def _apply_aggregation(self, aggregation: AggregationResult) -> None:
        """Apply one validated aggregation result to coordinator diagnostics."""
        self.positions = dict(aggregation.positions)
        self.source_summaries = tuple(item.to_dict() for item in aggregation.sources)
        self.source_conflicts = tuple(item.to_dict() for item in aggregation.conflicts)
        self.oldest_source_generated_at = aggregation.oldest_generated_at
        self.newest_source_generated_at = aggregation.newest_generated_at

    def _restore_source_metadata_from_payload(self, payload: dict[str, Any]) -> None:
        """Restore bounded multi-source timestamps from a validated cached payload."""
        summary = payload.get("summary")
        if not isinstance(summary, dict):
            return
        self.source_summaries = tuple(
            item for item in summary.get("source_summaries", []) if isinstance(item, dict)
        )
        self.source_conflicts = tuple(
            item for item in summary.get("source_conflicts", []) if isinstance(item, dict)
        )
        for key, attribute in (
            ("oldest_source_generated_at", "oldest_source_generated_at"),
            ("newest_source_generated_at", "newest_source_generated_at"),
        ):
            value = summary.get(key)
            if not isinstance(value, str):
                continue
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
            if parsed.tzinfo is not None:
                setattr(self, attribute, parsed.astimezone(timezone.utc))

    def _validate_rest_snapshot_integrity(
        self,
        *,
        result: Any,
        generated_at: datetime,
        position_count: int,
    ) -> bool | None:
        """Validate transport and health metadata for one accepted snapshot."""
        digest = result.snapshot_sha256
        declared_count = result.position_count

        if digest is None and declared_count is None:
            verified = (
                self.rest_snapshot_integrity_verified
                if result.snapshot is None
                else None
            )
        else:
            if digest is None or declared_count is None:
                raise PortfolioRestError(
                    "Local REST snapshot integrity metadata is incomplete"
                )
            if declared_count != position_count:
                raise PortfolioRestError(
                    "Local REST snapshot position count changed during validation"
                )
            if result.snapshot is None:
                if (
                    self._rest_snapshot_sha256 is not None
                    and digest != self._rest_snapshot_sha256
                ):
                    raise PortfolioRestError(
                        "Not-modified REST response changed the snapshot fingerprint"
                    )
                if (
                    self._rest_snapshot_position_count is not None
                    and declared_count != self._rest_snapshot_position_count
                ):
                    raise PortfolioRestError(
                        "Not-modified REST response changed the position count"
                    )
            verified = result.transport_integrity_verified is True

        health = self.gateway_health
        if (
            health is not None
            and health.health_schema_version >= 2
            and health.snapshot_generated_at == generated_at
        ):
            if health.snapshot_sha256 != (digest or self._rest_snapshot_sha256):
                raise PortfolioRestError(
                    "Gateway health fingerprint does not match the accepted snapshot"
                )
            if health.snapshot_position_count != position_count:
                raise PortfolioRestError(
                    "Gateway health position count does not match the accepted snapshot"
                )
            verified = True

        return verified

    def _update_legacy_sensor(self) -> PortfolioData:
        """Read the deprecated v1.0 command-line source sensor."""
        if self.source_entity_id is None:
            raise UpdateFailed("Legacy source entity is not configured")
        state = self.hass.states.get(self.source_entity_id)
        if state is None:
            raise UpdateFailed(f"Source entity {self.source_entity_id} does not exist")

        self.source_last_changed = state.last_changed
        self.source_last_updated = state.last_updated
        if state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            raise UpdateFailed(f"Source entity {self.source_entity_id} is {state.state}")

        try:
            data = parse_portfolio_data(
                state.attributes.get(ATTR_RECOMMENDATIONS),
                state.attributes.get(ATTR_SUMMARY),
                state.attributes.get(ATTR_POLICY_FINDINGS),
                holdings=state.attributes.get(ATTR_HOLDINGS),
            )
        except PortfolioArchitectDataError as err:
            raise UpdateFailed(str(err)) from err

        self.last_valid_source_updated = state.last_updated
        return data


class SupplementalPortfolioSourceError(ValueError):
    """Raised when a configured supplemental source cannot be read or aggregated."""


def _parse_payload(payload: dict[str, Any]) -> PortfolioData:
    return parse_portfolio_data(
        payload.get(ATTR_RECOMMENDATIONS),
        payload.get(ATTR_SUMMARY),
        payload.get(ATTR_POLICY_FINDINGS),
        holdings=payload.get(ATTR_HOLDINGS),
    )


def _supplemental_snapshots(
    supplemental_paths: tuple[SupplementalCsvPath, ...],
) -> tuple[PortfolioSourceSnapshot, ...]:
    selected_paths = select_latest_dkb_exports(
        tuple(item.path for item in supplemental_paths)
    )
    snapshots: list[PortfolioSourceSnapshot] = []
    multiple = len(selected_paths) > 1
    for index, path in enumerate(selected_paths, start=1):
        positions = read_positions(path, CsvSourceConfig(provider=PROVIDER_DKB))
        snapshots.append(
            PortfolioSourceSnapshot(
                source_id=f"dkb_{index}",
                provider=PROVIDER_DKB,
                label=(f"DKB CSV {index}" if multiple else "DKB CSV"),
                generated_at=dkb_export_timestamp(path),
                positions=positions,
            )
        )
    return tuple(snapshots)


def _aggregation_metadata(aggregation: AggregationResult) -> dict[str, Any]:
    return {
        "source_count": len(aggregation.sources),
        "source_providers": [item.provider for item in aggregation.sources],
        "source_summaries": [item.to_dict() for item in aggregation.sources],
        "source_conflict_count": len(aggregation.conflicts),
        "source_conflicts": [item.to_dict() for item in aggregation.conflicts],
        "oldest_source_generated_at": aggregation.oldest_generated_at.isoformat(),
        "newest_source_generated_at": aggregation.newest_generated_at.isoformat(),
    }


def _calculate_local_payload(
    csv_path: Path,
    config_directory: Path,
    plan_override: dict[str, Any] | None,
    source_config: CsvSourceConfig,
    supplemental_paths: tuple[SupplementalCsvPath, ...],
) -> tuple[dict[str, Any], datetime, datetime, dict[str, Position], AggregationResult]:
    """Run blocking local-file I/O, aggregation, and calculation."""
    csv_modified = _mtime(csv_path)
    primary_generated_at = (
        dkb_export_timestamp(csv_path)
        if source_config.provider == PROVIDER_DKB
        else csv_modified
    )
    primary_positions = read_positions(csv_path, source_config)
    sources = (
        PortfolioSourceSnapshot(
            source_id="primary",
            provider=source_config.provider,
            label=csv_path.name,
            generated_at=primary_generated_at,
            positions=primary_positions,
        ),
        *_supplemental_snapshots(supplemental_paths),
    )
    aggregation = aggregate_sources(sources)
    provider = PROVIDER_MULTI_SOURCE if supplemental_paths else source_config.provider
    payload = calculate_portfolio_payload_from_positions(
        aggregation.positions,
        config_directory,
        evaluated_at=max(item.generated_at for item in sources),
        plan_override=plan_override,
        source_provider=provider,
        source_label=(f"{len(sources)} sources" if supplemental_paths else csv_path.name),
        source_metadata=_aggregation_metadata(aggregation),
    )
    input_times = [csv_modified, *(_mtime(item.path) for item in supplemental_paths)]
    for path in configuration_files(config_directory):
        if path.exists():
            input_times.append(_mtime(path))
    return payload, primary_generated_at, max(input_times), primary_positions, aggregation


def _calculate_rest_payload(
    positions: dict[str, Position],
    config_directory: Path,
    plan_override: dict[str, Any] | None,
    generated_at: datetime,
    endpoint_url: str,
    supplemental_paths: tuple[SupplementalCsvPath, ...],
    investment_reserve_eur,
    investment_reserve_as_of: datetime | None,
    investment_cash: RestInvestmentCash | None,
) -> tuple[dict[str, Any], AggregationResult]:
    primary = PortfolioSourceSnapshot(
        source_id="comdirect",
        provider=PROVIDER_LOCAL_REST_JSON,
        label=_endpoint_source_label(endpoint_url),
        generated_at=generated_at,
        positions=positions,
    )
    try:
        supplements = _supplemental_snapshots(supplemental_paths)
        sources = (primary, *supplements)
        aggregation = aggregate_sources(sources)
    except (OSError, ValueError) as err:
        if supplemental_paths:
            raise SupplementalPortfolioSourceError(str(err)) from err
        raise
    provider = PROVIDER_MULTI_SOURCE if supplemental_paths else PROVIDER_LOCAL_REST_JSON
    payload = calculate_portfolio_payload_from_positions(
        aggregation.positions,
        config_directory,
        evaluated_at=max(item.generated_at for item in sources),
        plan_override=plan_override,
        source_provider=provider,
        source_label=(f"{len(sources)} sources" if supplemental_paths else _endpoint_source_label(endpoint_url)),
        source_metadata={
            **_aggregation_metadata(aggregation),
            **(
                {
                    "investment_reserve_eur": investment_reserve_eur,
                    "investment_reserve_as_of": investment_reserve_as_of.isoformat(),
                }
                if investment_reserve_eur is not None and investment_reserve_as_of is not None
                else {}
            ),
            **(
                {
                    "investment_account_balance_eur": investment_cash.account_balance_eur,
                    "eligible_investment_cash_eur": investment_cash.eligible_eur,
                    "authorized_investment_cash_eur": investment_cash.authorized_eur,
                    "investment_cash_authorization_policy": investment_cash.policy,
                    "investment_cash_authorization_cap_eur": investment_cash.cap_eur,
                }
                if investment_cash is not None
                else {}
            ),
        },
    )
    return payload, aggregation


def _endpoint_source_label(endpoint_url: str) -> str:
    """Return a friendly bounded label without leaking endpoint internals."""
    from urllib.parse import urlsplit

    parsed = urlsplit(endpoint_url)
    hostname = (parsed.hostname or "").lower()
    if "portfolio-architect-gateway" in hostname:
        return "Comdirect REST"
    return "Local REST"


def _latest_configuration_modified(config_directory: Path) -> datetime:
    modified, _fingerprint = _configuration_metadata(config_directory, None)
    return modified


def _configuration_metadata(
    config_directory: Path,
    plan_override: dict[str, Any] | None,
    supplemental_paths: tuple[str, ...] = (),
) -> tuple[datetime, str]:
    paths = tuple(configuration_files(config_directory))
    if not paths or any(not path.is_file() for path in paths):
        raise ValueError("Portfolio configuration files are unavailable")
    modified = max(_mtime(path) for path in paths)
    fingerprint = configuration_fingerprint(config_directory, paths, plan_override)
    if supplemental_paths:
        import hashlib
        import json

        digest = hashlib.sha256()
        digest.update(fingerprint.encode("ascii"))
        digest.update(
            json.dumps(
                list(supplemental_paths),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        fingerprint = digest.hexdigest()
    return modified, fingerprint


def _plan_override_from_entry(entry: ConfigEntry) -> dict[str, Any] | None:
    options = entry.options
    execution = {
        "enabled": bool(options.get(CONF_EXECUTION_COST_AWARE_ENABLED, False)),
        "policy": options.get(CONF_EXECUTION_POLICY, "balanced"),
        "max_cost_ratio_pct": options.get(CONF_EXECUTION_MAX_COST_RATIO_PCT, 1.5),
        "max_deferral_periods": options.get(CONF_EXECUTION_MAX_DEFERRAL_PERIODS, 3),
        "max_orders_per_execution": options.get(CONF_EXECUTION_MAX_ORDERS, 1),
        "reserve_mode": options.get(CONF_EXECUTION_RESERVE_MODE, "gateway_balance"),
        "manual_commission_base_eur": options.get(CONF_MANUAL_COMMISSION_BASE_EUR, 4.90),
        "manual_commission_pct": options.get(CONF_MANUAL_COMMISSION_PCT, 0.25),
        "manual_commission_min_eur": options.get(CONF_MANUAL_COMMISSION_MIN_EUR, 9.90),
        "manual_commission_max_eur": options.get(CONF_MANUAL_COMMISSION_MAX_EUR, 59.90),
        "manual_venue_fee_pct": options.get(CONF_MANUAL_VENUE_FEE_PCT, 0.0025),
        "manual_venue_fee_min_eur": options.get(CONF_MANUAL_VENUE_FEE_MIN_EUR, 2.50),
        "manual_settlement_fee_eur": options.get(CONF_MANUAL_SETTLEMENT_FEE_EUR, 2.90),
    }
    if not options.get(CONF_PLAN_OVERRIDE_ENABLED):
        return {"enabled": False, "execution": execution} if execution["enabled"] else None
    instruments = options.get(CONF_PLAN_INSTRUMENTS)
    if not isinstance(instruments, list):
        return None
    execution_days = _normalised_int_list(options.get(CONF_PLAN_EXECUTION_DAYS))
    executions_per_period = max(1, len(execution_days))
    return {
        "enabled": True,
        "name": options.get(CONF_PLAN_NAME, "Investment plan"),
        "budget_amount_eur": options.get(CONF_PLAN_BUDGET_AMOUNT),
        "budget_basis": options.get(CONF_PLAN_BUDGET_BASIS, PLAN_BUDGET_BASIS_PERIOD),
        "frequency": options.get(CONF_PLAN_FREQUENCY, PLAN_FREQUENCY_MONTHLY),
        "executions_per_period": executions_per_period,
        "instruments": instruments,
        "execution": execution,
    }


def _schedule_config_from_entry(entry: ConfigEntry) -> PlanScheduleConfig | None:
    options = entry.options
    if not options.get(CONF_PLAN_SCHEDULE_ENABLED):
        return None
    try:
        return validate_schedule_config(
            options.get(CONF_PLAN_FREQUENCY, PLAN_FREQUENCY_MONTHLY),
            _normalised_int_list(options.get(CONF_PLAN_EXECUTION_DAYS)),
            execution_month=options.get(CONF_PLAN_EXECUTION_MONTH),
            execution_month_offset=options.get(CONF_PLAN_EXECUTION_MONTH_OFFSET),
        )
    except ValueError:
        _LOGGER.error("Stored Portfolio Architect plan schedule is invalid")
        return None


def _normalised_int_list(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for raw in value:
        if isinstance(raw, bool):
            continue
        try:
            result.append(int(raw))
        except (TypeError, ValueError):
            continue
    return sorted(set(result))


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    """Return one bounded integer, falling back to a safe default."""
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, parsed))
