"""Config, reconfigure, source-adapter, and native plan flows."""

from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR
from urllib.parse import urlsplit
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.service_info.hassio import HassioServiceInfo
from homeassistant.util import dt as dt_util
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    DateSelector,
    DateSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_CONFIG_DIRECTORY,
    CONF_CSV_COLUMN_CURRENCY,
    CONF_CSV_COLUMN_IDENTIFIER,
    CONF_CSV_COLUMN_ISIN,
    CONF_CSV_COLUMN_NAME,
    CONF_CSV_COLUMN_TYPE,
    CONF_CSV_COLUMN_VALUE,
    CONF_CSV_DECIMAL_FORMAT,
    CONF_CSV_DELIMITER,
    CONF_CSV_ENCODING,
    CONF_CSV_HEADER_ROW,
    CONF_CSV_PATH,
    CONF_REST_API_TOKEN,
    CONF_REST_ENDPOINT_URL,
    CONF_REST_TLS_CA_CERTIFICATE,
    CONF_FRESHNESS_HOURS,
    CONF_FRESHNESS_LIVE_API_HOURS,
    CONF_FRESHNESS_STATEMENT_HOURS,
    CONF_FRESHNESS_CSV_HOURS,
    CONF_FRESHNESS_OTHER_HOURS,
    CONF_PLAN_BUDGET_AMOUNT,
    CONF_PLAN_BUDGET_BASIS,
    CONF_PLAN_EXECUTION_DAY,
    CONF_PLAN_EXECUTION_DAYS,
    CONF_PLAN_EXECUTION_MONTH,
    CONF_PLAN_EXECUTION_MONTH_OFFSET,
    CONF_PLAN_FREQUENCY,
    CONF_PLAN_INSTRUMENTS,
    CONF_PLAN_NAME,
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
    CONF_PLAN_OVERRIDE_ENABLED,
    CONF_PLAN_SCHEDULE_ENABLED,
    CONF_REVIEW_LEAD_DAYS,
    CONF_SOURCE_PROVIDER,
    CONF_SUPPLEMENTAL_REST_SOURCES,
    CONF_SOURCE_TYPE,
    DEFAULT_CONFIG_DIRECTORY,
    DEFAULT_CSV_PATH,
    DEFAULT_REST_ENDPOINT_URL,
    DEFAULT_FRESHNESS_HOURS,
    DEFAULT_PLAN_BUDGET_BASIS,
    DEFAULT_PLAN_FREQUENCY,
    DEFAULT_REVIEW_LEAD_DAYS,
    DEFAULT_SOURCE_PROVIDER,
    DOMAIN,
    INSTANCE_UNIQUE_ID,
    MAX_EXECUTION_MONTH,
    MAX_EXECUTION_MONTH_OFFSET,
    MAX_FRESHNESS_HOURS,
    MAX_DOCUMENT_FRESHNESS_HOURS,
    MAX_PLAN_BUDGET_EUR,
    MAX_PLAN_INSTRUMENTS,
    MAX_REVIEW_LEAD_DAYS,
    EXECUTION_POLICIES,
    EXECUTION_RESERVE_MODES,
    MAX_SUPPLEMENTAL_REST_SOURCES,
    MIN_EXECUTION_MONTH,
    MIN_EXECUTION_MONTH_OFFSET,
    MIN_FRESHNESS_HOURS,
    MIN_PLAN_BUDGET_EUR,
    MIN_REVIEW_LEAD_DAYS,
    NAME,
    PLAN_BUDGET_BASES,
    PLAN_FREQUENCIES,
    PLAN_FREQUENCY_MONTHLY,
    PLAN_FREQUENCY_QUARTERLY,
    PLAN_FREQUENCY_WEEKLY,
    PLAN_FREQUENCY_YEARLY,
    SOURCE_TYPE_LOCAL_FILES,
    SOURCE_TYPE_REST_API,
)
from .broker_editor import (
    TIE_BREAK_FALLBACK,
    TIE_BREAK_NEUTRAL,
    TIE_BREAK_PREFERRED,
    add_funding_transfer,
    edit_funding_transfer,
    load_broker_editor_context,
    remove_funding_transfer,
    remove_provider,
    remove_savings_plan,
    set_general_settings,
    tie_break_mode,
    upsert_provider,
    upsert_savings_plan,
    write_broker_document_atomic,
)
from .engine import calculate_portfolio_payload, calculate_portfolio_payload_from_positions
from .gateway_provider_ids import GATEWAY_PROVIDER_COMDIRECT
from .freshness import default_freshness_thresholds
CONF_MANUAL_VENUE_FEE_BPS = "manual_venue_fee_bps"

# Native broker editor fields intentionally remain local to the options flow. The
# authoritative runtime format remains broker.yaml schema 2/3.
CONF_BROKER_FEE_DATA_MAX_AGE_DAYS = "broker_fee_data_max_age_days"
CONF_BROKER_PROVIDER_ID = "broker_provider_id"
CONF_BROKER_PROVIDER_NAME = "broker_provider_name"
CONF_BROKER_PROVIDER_SOURCE = "broker_provider_source"
CONF_BROKER_PROVIDER_AS_OF = "broker_provider_as_of"
CONF_BROKER_TIE_BREAK = "broker_tie_break_preference"
CONF_BROKER_SAVINGS_ROUTE = "broker_savings_route"
CONF_BROKER_ISIN = "broker_isin"
CONF_BROKER_AVAILABLE = "broker_available"
CONF_BROKER_FEE_PCT = "broker_fee_pct"
CONF_BROKER_PROMOTIONAL = "broker_promotional"
CONF_BROKER_STATUS = "broker_status"
CONF_BROKER_ROUTE_SOURCE = "broker_route_source"
CONF_BROKER_ROUTE_AS_OF = "broker_route_as_of"
CONF_BROKER_FUNDING_EDGE = "broker_funding_edge"
CONF_BROKER_FROM_PROVIDER = "broker_from_provider"
CONF_BROKER_TO_PROVIDER = "broker_to_provider"
CONF_BROKER_TRANSFER_FEE_EUR = "broker_transfer_fee_eur"
CONF_BROKER_SETTLEMENT_DAYS = "broker_settlement_business_days"
CONF_BROKER_TRANSFER_SOURCE = "broker_transfer_source"
CONF_BROKER_TRANSFER_AS_OF = "broker_transfer_as_of"


from .engine.execution import ExecutionConfig
from .engine.importers import (
    CSV_DELIMITERS,
    CSV_ENCODINGS,
    DECIMAL_FORMATS,
    DEFAULT_GENERIC_DECIMAL_FORMAT,
    DEFAULT_GENERIC_DELIMITER,
    DEFAULT_GENERIC_ENCODING,
    DEFAULT_GENERIC_HEADER_ROW,
    MAX_GENERIC_HEADER_ROW,
    PROVIDER_GENERIC_CSV,
    CsvSourceConfig,
    inspect_csv_headers,
    read_positions,
)
from .engine.rest import PROVIDER_LOCAL_REST_JSON
from .engine.targets import generate_target_id
from .model import PortfolioArchitectDataError, parse_portfolio_data
from .plan_editor import (
    PlanCandidate,
    PlanEditorContext,
    load_plan_editor_context,
    load_plan_editor_context_from_positions,
)
from .rest_client import (
    GatewayTlsDiscovery,
    PortfolioRestAuthenticationError,
    PortfolioRestError,
    PortfolioRestTlsError,
    RestSourceConfig,
    SupplementalRestSourceConfig,
    async_fetch_gateway_health,
    async_fetch_rest_snapshot,
)
from .schedule import validate_schedule_config
from .source import (
    PortfolioSourcePathError,
    resolve_configuration_directory,
    resolve_local_source_paths,
)


_PLAN_OVERRIDE_OPTION_KEYS = (
    CONF_PLAN_OVERRIDE_ENABLED,
    CONF_PLAN_NAME,
    CONF_PLAN_BUDGET_AMOUNT,
    CONF_PLAN_BUDGET_BASIS,
    CONF_PLAN_INSTRUMENTS,
)

_GENERIC_KEYS = (
    CONF_CSV_ENCODING,
    CONF_CSV_DELIMITER,
    CONF_CSV_HEADER_ROW,
    CONF_CSV_DECIMAL_FORMAT,
    CONF_CSV_COLUMN_IDENTIFIER,
    CONF_CSV_COLUMN_NAME,
    CONF_CSV_COLUMN_VALUE,
    CONF_CSV_COLUMN_ISIN,
    CONF_CSV_COLUMN_TYPE,
    CONF_CSV_COLUMN_CURRENCY,
)


_SUPPORTED_SOURCE_PROVIDERS = (
    PROVIDER_GENERIC_CSV,
    PROVIDER_LOCAL_REST_JSON,
)
_NEW_SOURCE_PROVIDERS = (
    PROVIDER_GENERIC_CSV,
    PROVIDER_LOCAL_REST_JSON,
)



class PortfolioArchitectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure one explicit local CSV or local REST source adapter."""

    VERSION = 11
    _source_draft: dict[str, Any]
    _existing_source_data: dict[str, Any]
    _generic_headers: tuple[str, ...]
    _reconfigure_mode: bool = False
    _hassio_discovery: GatewayTlsDiscovery | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PortfolioArchitectOptionsFlow:
        return PortfolioArchitectOptionsFlow()

    async def async_step_hassio(
        self, discovery_info: HassioServiceInfo
    ) -> ConfigFlowResult:
        """Migrate one known Gateway to verified HTTPS using Supervisor trust discovery."""
        try:
            discovery = GatewayTlsDiscovery.from_mapping(dict(discovery_info.config))
        except PortfolioRestError:
            return self.async_abort(reason="invalid_tls_discovery")

        entries = self.hass.config_entries.async_entries(DOMAIN)
        if not entries:
            if discovery.provider_id != GATEWAY_PROVIDER_COMDIRECT:
                return self.async_abort(reason="tls_discovery_not_primary")
            self._hassio_discovery = discovery
            await self.async_set_unique_id(INSTANCE_UNIQUE_ID)
            return await self.async_step_hassio_confirm()
        if len(entries) != 1:
            return self.async_abort(reason="tls_discovery_not_applicable")

        entry = entries[0]
        if entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_REST_API:
            endpoint = entry.data.get(CONF_REST_ENDPOINT_URL)
            if isinstance(endpoint, str) and discovery.matches_legacy_endpoint(endpoint):
                if urlsplit(endpoint).scheme == "https":
                    try:
                        stored = RestSourceConfig.from_mapping(dict(entry.data))
                    except PortfolioRestError:
                        return self.async_abort(reason="tls_discovery_not_applicable")
                    if stored.tls_ca_sha256 == discovery.ca_sha256:
                        return self.async_abort(reason="tls_already_configured")
                    # HTTPS is already a secured trust boundary. Discovery may
                    # migrate legacy HTTP, but must never silently replace an
                    # existing private CA or system-PKI trust decision.
                    return self.async_abort(reason="tls_trust_changed")
                return await self._async_migrate_primary_tls(entry, discovery)

        raw_sources = entry.options.get(CONF_SUPPLEMENTAL_REST_SOURCES, [])
        if isinstance(raw_sources, list):
            for index, raw in enumerate(raw_sources):
                if not isinstance(raw, dict):
                    continue
                try:
                    source = SupplementalRestSourceConfig.from_mapping(raw)
                except PortfolioRestError:
                    continue
                if source.provider_id != discovery.provider_id:
                    continue
                if not discovery.matches_legacy_endpoint(source.endpoint_url):
                    return self.async_abort(reason="tls_discovery_not_applicable")
                if urlsplit(source.endpoint_url).scheme == "https":
                    if source.rest_config.tls_ca_sha256 == discovery.ca_sha256:
                        return self.async_abort(reason="tls_already_configured")
                    return self.async_abort(reason="tls_trust_changed")
                return await self._async_migrate_supplemental_tls(
                    entry, discovery, index, raw_sources
                )

        # A newly installed supplemental provider has no legacy HTTP source to
        # migrate. Discovery supplies network identity and public CA trust; adding
        # a provider still requires explicit user consent and the App-private bearer
        # token. Provider-specific CSV acquisition is owned by its Gateway.
        if (
            entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_REST_API
            and discovery.provider_id != GATEWAY_PROVIDER_COMDIRECT
        ):
            self._hassio_discovery = discovery
            return await self.async_step_hassio_add_supplemental_confirm()

        return self.async_abort(reason="tls_discovery_not_applicable")

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a new primary Comdirect REST entry from verified Supervisor discovery."""
        discovery = self._hassio_discovery
        if discovery is None or discovery.provider_id != GATEWAY_PROVIDER_COMDIRECT:
            return self.async_abort(reason="invalid_tls_discovery")
        errors: dict[str, str] = {}
        suggested = {
            CONF_CONFIG_DIRECTORY: DEFAULT_CONFIG_DIRECTORY,
            CONF_REST_API_TOKEN: "",
        }
        if user_input is not None:
            suggested.update(user_input)
            candidate = {
                CONF_SOURCE_TYPE: SOURCE_TYPE_REST_API,
                CONF_SOURCE_PROVIDER: PROVIDER_LOCAL_REST_JSON,
                CONF_CONFIG_DIRECTORY: user_input[CONF_CONFIG_DIRECTORY],
                CONF_REST_ENDPOINT_URL: discovery.endpoint_url,
                CONF_REST_API_TOKEN: user_input[CONF_REST_API_TOKEN],
                CONF_REST_TLS_CA_CERTIFICATE: discovery.ca_certificate,
            }
            try:
                cleaned = await self._async_validate_rest_source_data(candidate)
                health = await async_fetch_gateway_health(
                    self.hass, RestSourceConfig.from_mapping(cleaned)
                )
                if health.health_schema_version < 6 or health.provider_id != discovery.provider_id:
                    raise PortfolioRestTlsError("Discovered Gateway provider identity did not validate")
            except PortfolioRestAuthenticationError:
                errors["base"] = "invalid_auth"
            except PortfolioSourcePathError:
                errors["base"] = "invalid_path"
            except (OSError, ValueError, PortfolioRestError, PortfolioArchitectDataError):
                errors["base"] = "invalid_rest_source"
            else:
                return self.async_create_entry(title=NAME, data=cleaned)
        return self.async_show_form(
            step_id="hassio_confirm",
            data_schema=self.add_suggested_values_to_schema(
                _hassio_rest_source_schema(), suggested
            ),
            errors=errors,
            description_placeholders={"gateway": discovery.hostname},
        )

    async def async_step_hassio_add_supplemental_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Explicitly add one newly discovered verified-HTTPS supplemental Gateway."""
        discovery = self._hassio_discovery
        if discovery is None or discovery.provider_id == GATEWAY_PROVIDER_COMDIRECT:
            return self.async_abort(reason="invalid_tls_discovery")
        entries = self.hass.config_entries.async_entries(DOMAIN)
        if len(entries) != 1:
            return self.async_abort(reason="tls_discovery_not_applicable")
        entry = entries[0]
        if entry.data.get(CONF_SOURCE_TYPE) != SOURCE_TYPE_REST_API:
            return self.async_abort(reason="rest_gateways_require_rest_primary")

        errors: dict[str, str] = {}
        suggested = {CONF_REST_API_TOKEN: ""}
        if user_input is not None:
            suggested.update(user_input)
            options = dict(entry.options)
            raw_sources = options.get(CONF_SUPPLEMENTAL_REST_SOURCES, [])
            stored = raw_sources if isinstance(raw_sources, list) else []
            if len(stored) >= MAX_SUPPLEMENTAL_REST_SOURCES:
                errors["base"] = "too_many_rest_gateways"
            else:
                try:
                    candidate = RestSourceConfig.from_mapping(
                        {
                            CONF_REST_ENDPOINT_URL: discovery.endpoint_url,
                            CONF_REST_API_TOKEN: user_input[CONF_REST_API_TOKEN],
                            CONF_REST_TLS_CA_CERTIFICATE: discovery.ca_certificate,
                        }
                    )
                    existing = tuple(
                        SupplementalRestSourceConfig.from_mapping(item)
                        for item in stored
                        if isinstance(item, dict)
                    )
                    if any(item.provider_id == discovery.provider_id for item in existing):
                        raise ValueError("duplicate provider")
                    if any(item.endpoint_url == candidate.endpoint_url for item in existing):
                        raise ValueError("duplicate endpoint")

                    primary = RestSourceConfig.from_mapping(dict(entry.data))
                    primary_health = await async_fetch_gateway_health(self.hass, primary)
                    if (
                        primary_health.health_schema_version < 6
                        or primary_health.provider_id is None
                        or primary_health.status != "ok"
                        or primary_health.reauthentication_required
                        or not primary_health.snapshot_available
                    ):
                        raise PortfolioRestError(
                            "Primary Gateway is not ready for multi-Gateway configuration"
                        )
                    if primary_health.provider_id == discovery.provider_id:
                        raise ValueError("duplicate provider")

                    health = await async_fetch_gateway_health(self.hass, candidate)
                    if (
                        health.health_schema_version < 6
                        or health.provider_id != discovery.provider_id
                        or health.status != "ok"
                        or health.reauthentication_required
                        or not health.snapshot_available
                    ):
                        raise PortfolioRestError("Discovered Gateway is not ready for live use")
                    result = await async_fetch_rest_snapshot(self.hass, candidate)
                    snapshot = result.snapshot
                    if snapshot is None or result.snapshot_sha256 is None or result.position_count is None:
                        raise PortfolioRestError("Discovered Gateway returned no verified live snapshot")
                    if (
                        result.position_count != len(snapshot.positions)
                        or health.snapshot_generated_at is None
                        or health.snapshot_generated_at != snapshot.generated_at
                        or health.snapshot_position_count != len(snapshot.positions)
                        or health.snapshot_sha256 != result.snapshot_sha256
                    ):
                        raise PortfolioRestError(
                            "Discovered Gateway health does not match its live snapshot"
                        )
                except PortfolioRestAuthenticationError:
                    errors["base"] = "invalid_auth"
                except (OSError, ValueError, PortfolioRestError):
                    errors["base"] = "invalid_rest_gateway"
                else:
                    configured = SupplementalRestSourceConfig(
                        provider_id=discovery.provider_id,
                        endpoint_url=candidate.endpoint_url,
                        api_token=candidate.api_token,
                        tls_ca_certificate=discovery.ca_certificate,
                    )
                    options[CONF_SUPPLEMENTAL_REST_SOURCES] = [
                        *stored, configured.as_storage_dict()
                    ]
                    self.hass.config_entries.async_update_entry(entry, options=options)
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="tls_supplemental_added")

        return self.async_show_form(
            step_id="hassio_add_supplemental_confirm",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_REST_API_TOKEN): str}), suggested
            ),
            errors=errors,
            description_placeholders={
                "provider": discovery.provider_id.replace("_", " ").title(),
                "gateway": discovery.hostname,
            },
        )

    async def _async_migrate_primary_tls(
        self, entry: ConfigEntry, discovery: GatewayTlsDiscovery
    ) -> ConfigFlowResult:
        token = entry.data.get(CONF_REST_API_TOKEN)
        candidate = RestSourceConfig.from_mapping(
            {
                CONF_REST_ENDPOINT_URL: discovery.endpoint_url,
                CONF_REST_API_TOKEN: token,
                CONF_REST_TLS_CA_CERTIFICATE: discovery.ca_certificate,
            }
        )
        try:
            health = await async_fetch_gateway_health(self.hass, candidate)
        except PortfolioRestError:
            return self.async_abort(reason="tls_validation_failed")
        if (
            health.health_schema_version < 6
            or health.provider_id != discovery.provider_id
            or not health.snapshot_available
        ):
            return self.async_abort(reason="tls_validation_failed")
        data = dict(entry.data)
        data[CONF_REST_ENDPOINT_URL] = discovery.endpoint_url
        data[CONF_REST_TLS_CA_CERTIFICATE] = discovery.ca_certificate
        self.hass.config_entries.async_update_entry(entry, data=data)
        await self.hass.config_entries.async_reload(entry.entry_id)
        return self.async_abort(reason="tls_migrated")

    async def _async_migrate_supplemental_tls(
        self,
        entry: ConfigEntry,
        discovery: GatewayTlsDiscovery,
        index: int,
        raw_sources: list[Any],
    ) -> ConfigFlowResult:
        raw = raw_sources[index]
        assert isinstance(raw, dict)
        token = raw.get(CONF_REST_API_TOKEN)
        candidate = RestSourceConfig.from_mapping(
            {
                CONF_REST_ENDPOINT_URL: discovery.endpoint_url,
                CONF_REST_API_TOKEN: token,
                CONF_REST_TLS_CA_CERTIFICATE: discovery.ca_certificate,
            }
        )
        try:
            health = await async_fetch_gateway_health(self.hass, candidate)
        except PortfolioRestError:
            return self.async_abort(reason="tls_validation_failed")
        if (
            health.health_schema_version < 6
            or health.provider_id != discovery.provider_id
            or not health.snapshot_available
        ):
            return self.async_abort(reason="tls_validation_failed")
        configured = SupplementalRestSourceConfig(
            provider_id=discovery.provider_id,
            endpoint_url=discovery.endpoint_url,
            api_token=candidate.api_token,
            tls_ca_certificate=discovery.ca_certificate,
        )
        updated_sources = list(raw_sources)
        updated_sources[index] = configured.as_storage_dict()
        options = dict(entry.options)
        options[CONF_SUPPLEMENTAL_REST_SOURCES] = updated_sources
        self.hass.config_entries.async_update_entry(entry, options=options)
        await self.hass.config_entries.async_reload(entry.entry_id)
        return self.async_abort(reason="tls_migrated")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        # Do not use manifest single_config_entry here: Supervisor discovery must be
        # allowed to start a hassio flow so it can migrate the one existing entry
        # from legacy HTTP to verified HTTPS. Manual setup remains strictly
        # single-instance, including legacy entries that may not have a unique ID.
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_configured")
        await self.async_set_unique_id(INSTANCE_UNIQUE_ID)
        self._abort_if_unique_id_configured()
        self._reconfigure_mode = False
        return await self._async_provider_step("user", user_input, None)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        await self.async_set_unique_id(INSTANCE_UNIQUE_ID)
        self._abort_if_unique_id_mismatch()
        self._reconfigure_mode = True
        return await self._async_provider_step("reconfigure", user_input, entry)

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start bearer-token reauthentication for a REST source."""
        del entry_data
        entry = self._get_reauth_entry()
        await self.async_set_unique_id(entry.unique_id)
        self._abort_if_unique_id_mismatch()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate and replace only the local gateway bearer token."""
        entry = self._get_reauth_entry()
        if entry.data.get(CONF_SOURCE_TYPE) != SOURCE_TYPE_REST_API:
            return self.async_abort(reason="reauth_not_supported")
        errors: dict[str, str] = {}
        suggested = {
            CONF_REST_API_TOKEN: entry.data.get(CONF_REST_API_TOKEN, ""),
        }
        if user_input is not None:
            suggested.update(user_input)
            candidate = dict(entry.data)
            candidate[CONF_REST_API_TOKEN] = user_input[CONF_REST_API_TOKEN]
            try:
                cleaned = await self._async_validate_rest_source_data(
                    candidate, require_https=False
                )
            except PortfolioRestAuthenticationError:
                errors["base"] = "invalid_auth"
            except PortfolioSourcePathError:
                errors["base"] = "invalid_path"
            except (OSError, ValueError, PortfolioRestError, PortfolioArchitectDataError):
                errors["base"] = "invalid_rest_source"
            else:
                return self.async_update_reload_and_abort(entry, data=cleaned)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                _reauth_schema(), suggested
            ),
            errors=errors,
        )

    async def _async_provider_step(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
        entry: ConfigEntry | None,
    ) -> ConfigFlowResult:
        existing = dict(entry.data) if entry is not None else {}
        self._existing_source_data = existing
        suggested = {
            CONF_SOURCE_PROVIDER: existing.get(
                CONF_SOURCE_PROVIDER, DEFAULT_SOURCE_PROVIDER
            ),
            CONF_CONFIG_DIRECTORY: existing.get(
                CONF_CONFIG_DIRECTORY, DEFAULT_CONFIG_DIRECTORY
            ),
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            provider = str(user_input[CONF_SOURCE_PROVIDER])
            if provider not in _SUPPORTED_SOURCE_PROVIDERS:
                errors[CONF_SOURCE_PROVIDER] = "invalid_provider"
            else:
                try:
                    config_path = resolve_configuration_directory(
                        self.hass,
                        user_input[CONF_CONFIG_DIRECTORY],
                        require_exists=True,
                    )
                except PortfolioSourcePathError:
                    errors["base"] = "invalid_path"
                else:
                    self._source_draft = {
                        CONF_SOURCE_PROVIDER: provider,
                        CONF_CONFIG_DIRECTORY: config_path.config_relative,
                    }
                    if provider == PROVIDER_LOCAL_REST_JSON:
                        return await self.async_step_rest_source()
                    return await self.async_step_csv_source()
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                _provider_schema(
                    _SUPPORTED_SOURCE_PROVIDERS if entry is not None else _NEW_SOURCE_PROVIDERS
                ), suggested
            ),
            errors=errors,
        )

    async def async_step_csv_source(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        suggested = {
            CONF_CSV_PATH: self._existing_source_data.get(
                CONF_CSV_PATH, DEFAULT_CSV_PATH
            )
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            self._source_draft.update(
                {
                    CONF_SOURCE_TYPE: SOURCE_TYPE_LOCAL_FILES,
                    CONF_CSV_PATH: user_input[CONF_CSV_PATH],
                }
            )
            if self._source_draft[CONF_SOURCE_PROVIDER] == PROVIDER_GENERIC_CSV:
                for key in _GENERIC_KEYS:
                    if key in self._existing_source_data:
                        self._source_draft[key] = self._existing_source_data[key]
                return await self.async_step_generic_format()
            try:
                cleaned = await self._async_validate_csv_source_data(
                    self._source_draft
                )
            except PortfolioSourcePathError:
                errors["base"] = "invalid_path"
            except FileNotFoundError:
                errors["base"] = "source_unavailable"
            except (OSError, ValueError, PortfolioArchitectDataError):
                errors["base"] = "invalid_source"
            else:
                return self._finish_source(cleaned)
        return self.async_show_form(
            step_id="csv_source",
            data_schema=self.add_suggested_values_to_schema(
                _csv_source_schema(), suggested
            ),
            errors=errors,
        )

    async def async_step_rest_source(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        suggested = {
            CONF_REST_ENDPOINT_URL: self._existing_source_data.get(
                CONF_REST_ENDPOINT_URL, DEFAULT_REST_ENDPOINT_URL
            ),
            CONF_REST_API_TOKEN: self._existing_source_data.get(
                CONF_REST_API_TOKEN, ""
            ),
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            candidate = {
                **self._source_draft,
                CONF_SOURCE_TYPE: SOURCE_TYPE_REST_API,
                CONF_SOURCE_PROVIDER: PROVIDER_LOCAL_REST_JSON,
                CONF_REST_ENDPOINT_URL: user_input[CONF_REST_ENDPOINT_URL],
                CONF_REST_API_TOKEN: user_input[CONF_REST_API_TOKEN],
            }
            try:
                cleaned = await self._async_validate_rest_source_data(candidate)
            except PortfolioRestAuthenticationError:
                errors["base"] = "invalid_auth"
            except PortfolioSourcePathError:
                errors["base"] = "invalid_path"
            except (OSError, ValueError, PortfolioRestError, PortfolioArchitectDataError):
                errors["base"] = "invalid_rest_source"
            else:
                return self._finish_source(cleaned)
        return self.async_show_form(
            step_id="rest_source",
            data_schema=self.add_suggested_values_to_schema(
                _rest_source_schema(), suggested
            ),
            errors=errors,
        )

    async def async_step_generic_format(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        suggested = {
            CONF_CSV_ENCODING: self._source_draft.get(
                CONF_CSV_ENCODING, DEFAULT_GENERIC_ENCODING
            ),
            CONF_CSV_DELIMITER: self._source_draft.get(
                CONF_CSV_DELIMITER, DEFAULT_GENERIC_DELIMITER
            ),
            CONF_CSV_HEADER_ROW: self._source_draft.get(
                CONF_CSV_HEADER_ROW, DEFAULT_GENERIC_HEADER_ROW
            ),
            CONF_CSV_DECIMAL_FORMAT: self._source_draft.get(
                CONF_CSV_DECIMAL_FORMAT, DEFAULT_GENERIC_DECIMAL_FORMAT
            ),
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            self._source_draft.update(user_input)
            try:
                paths = resolve_local_source_paths(
                    self.hass,
                    self._source_draft[CONF_CSV_PATH],
                    self._source_draft[CONF_CONFIG_DIRECTORY],
                    require_exists=False,
                )
                partial = CsvSourceConfig(
                    provider=PROVIDER_GENERIC_CSV,
                    encoding=str(self._source_draft[CONF_CSV_ENCODING]),
                    delimiter=str(self._source_draft[CONF_CSV_DELIMITER]),
                    header_row=int(self._source_draft[CONF_CSV_HEADER_ROW]),
                    decimal_format=str(
                        self._source_draft[CONF_CSV_DECIMAL_FORMAT]
                    ),
                )
                self._generic_headers = await self.hass.async_add_executor_job(
                    inspect_csv_headers, paths.csv_path, partial
                )
            except PortfolioSourcePathError:
                errors["base"] = "invalid_path"
            except (OSError, ValueError):
                errors["base"] = "invalid_csv_format"
            else:
                return await self.async_step_generic_mapping()
        return self.async_show_form(
            step_id="generic_format",
            data_schema=self.add_suggested_values_to_schema(
                _generic_format_schema(), suggested
            ),
            errors=errors,
        )

    async def async_step_generic_mapping(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        suggested = _mapping_suggestions(self._source_draft, self._generic_headers)
        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            self._source_draft.update(user_input)
            try:
                cleaned = await self._async_validate_csv_source_data(
                    self._source_draft
                )
            except PortfolioSourcePathError:
                errors["base"] = "invalid_path"
            except FileNotFoundError:
                errors["base"] = "source_unavailable"
            except (OSError, ValueError, PortfolioArchitectDataError):
                errors["base"] = "invalid_source"
            else:
                return self._finish_source(cleaned)
        return self.async_show_form(
            step_id="generic_mapping",
            data_schema=self.add_suggested_values_to_schema(
                _generic_mapping_schema(self._generic_headers), suggested
            ),
            errors=errors,
            description_placeholders={
                "column_count": str(len(self._generic_headers)),
                "header_row": str(self._source_draft[CONF_CSV_HEADER_ROW]),
            },
        )

    async def _async_validate_csv_source_data(
        self, data: dict[str, Any]
    ) -> dict[str, Any]:
        paths = resolve_local_source_paths(
            self.hass,
            data[CONF_CSV_PATH],
            data[CONF_CONFIG_DIRECTORY],
            require_exists=False,
        )
        cleaned = dict(data)
        cleaned[CONF_CSV_PATH] = paths.csv_relative
        cleaned[CONF_CONFIG_DIRECTORY] = paths.config_relative
        adapter = CsvSourceConfig.from_mapping(cleaned)
        payload = await self.hass.async_add_executor_job(
            _calculate_source_payload,
            paths.csv_path,
            paths.config_directory,
            adapter,
        )
        _validate_calculated_payload(payload)
        cleaned.pop(CONF_REST_ENDPOINT_URL, None)
        cleaned.pop(CONF_REST_API_TOKEN, None)
        cleaned.pop(CONF_REST_TLS_CA_CERTIFICATE, None)
        return cleaned

    async def _async_validate_rest_source_data(
        self, data: dict[str, Any], *, require_https: bool = True
    ) -> dict[str, Any]:
        configuration = resolve_configuration_directory(
            self.hass,
            data[CONF_CONFIG_DIRECTORY],
            require_exists=True,
        )
        rest_config = RestSourceConfig.from_mapping(data)
        if require_https and urlsplit(rest_config.endpoint_url).scheme != "https":
            raise PortfolioRestTlsError("New and reconfigured REST sources must use verified HTTPS")
        result = await async_fetch_rest_snapshot(self.hass, rest_config)
        health = await async_fetch_gateway_health(self.hass, rest_config)
        if health.status != "ok" or health.reauthentication_required:
            raise PortfolioRestError("Local gateway is not ready for live portfolio use")
        if result.snapshot is None:
            raise PortfolioRestError(
                "Local REST source returned not modified during validation"
            )
        payload = await self.hass.async_add_executor_job(
            _calculate_rest_source_payload,
            result.snapshot.positions,
            configuration.config_directory,
            result.snapshot.generated_at,
            rest_config.endpoint_url,
        )
        _validate_calculated_payload(payload)
        cleaned = {
            CONF_SOURCE_TYPE: SOURCE_TYPE_REST_API,
            CONF_SOURCE_PROVIDER: PROVIDER_LOCAL_REST_JSON,
            CONF_CONFIG_DIRECTORY: configuration.config_relative,
            CONF_REST_ENDPOINT_URL: rest_config.endpoint_url,
            CONF_REST_API_TOKEN: rest_config.api_token,
        }
        if rest_config.tls_ca_certificate is not None:
            cleaned[CONF_REST_TLS_CA_CERTIFICATE] = rest_config.tls_ca_certificate
        return cleaned

    def _finish_source(self, cleaned: dict[str, Any]) -> ConfigFlowResult:
        if self._reconfigure_mode:
            entry = self._get_reconfigure_entry()
            return self.async_update_reload_and_abort(entry, data=cleaned)
        return self.async_create_entry(title=NAME, data=cleaned)


class PortfolioArchitectOptionsFlow(OptionsFlowWithReload):
    """Manage native plan configuration and runtime behaviour."""

    _context: PlanEditorContext | None = None
    _selected_isins: list[str]
    _selected_target_ids: dict[str, str]
    _draft: dict[str, Any]
    _draft_instruments: list[dict[str, Any]]
    _instrument_index: int
    _execution_draft: dict[str, Any] | None = None
    _schedule_settings_draft: dict[str, Any] | None = None
    _broker_provider_id: str | None = None
    _broker_route_token: str | None = None
    _broker_funding_token: str | None = None
    _rest_gateway_provider_id: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Present native configuration areas."""
        del user_input
        menu_options = ["plan", "plan_schedule", "execution", "execution_providers", "runtime"]
        if self.config_entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_REST_API:
            menu_options.insert(4, "sources")
        if self.config_entry.options.get(CONF_PLAN_OVERRIDE_ENABLED):
            menu_options.append("reset_plan")
        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options,
        )

    async def async_step_sources(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Model the one primary REST source separately from supplemental Gateways."""
        del user_input
        if self.config_entry.data.get(CONF_SOURCE_TYPE) != SOURCE_TYPE_REST_API:
            return self.async_abort(reason="rest_gateways_require_rest_primary")
        return self.async_show_menu(
            step_id="sources",
            menu_options=["primary_rest_gateway", "rest_gateways"],
        )

    def _supplemental_rest_sources(self) -> list[SupplementalRestSourceConfig]:
        """Return the currently configured supplemental REST Gateways."""
        raw_sources = self.config_entry.options.get(CONF_SUPPLEMENTAL_REST_SOURCES, [])
        if not isinstance(raw_sources, list):
            return []
        return [
            SupplementalRestSourceConfig.from_mapping(item)
            for item in raw_sources
            if isinstance(item, dict)
        ]

    @staticmethod
    def _rest_edit_candidate(
        user_input: dict[str, Any],
        existing: RestSourceConfig,
    ) -> RestSourceConfig:
        """Build an edited REST source while retaining trust for an unchanged endpoint."""
        first = RestSourceConfig.from_mapping(user_input)
        mapping = dict(user_input)
        if (
            first.endpoint_url == existing.endpoint_url
            and existing.tls_ca_certificate is not None
        ):
            mapping[CONF_REST_TLS_CA_CERTIFICATE] = existing.tls_ca_certificate
        return RestSourceConfig.from_mapping(mapping)

    async def async_step_primary_rest_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the single primary REST Gateway without changing its provider identity."""
        if self.config_entry.data.get(CONF_SOURCE_TYPE) != SOURCE_TYPE_REST_API:
            return self.async_abort(reason="rest_gateways_require_rest_primary")
        existing = RestSourceConfig.from_mapping(dict(self.config_entry.data))
        supplemental = self._supplemental_rest_sources()
        current_provider_id: str | None = None
        try:
            current_health = await async_fetch_gateway_health(self.hass, existing)
        except PortfolioRestError:
            current_health = None
        if current_health is not None:
            current_provider_id = current_health.provider_id
        errors: dict[str, str] = {}
        suggested = {
            CONF_REST_ENDPOINT_URL: existing.endpoint_url,
            CONF_REST_API_TOKEN: existing.api_token,
        }
        if user_input is not None:
            suggested.update(user_input)
            try:
                candidate = self._rest_edit_candidate(user_input, existing)
                if urlsplit(candidate.endpoint_url).scheme != "https":
                    raise PortfolioRestTlsError("Primary Gateway must use verified HTTPS")
                if any(item.endpoint_url == candidate.endpoint_url for item in supplemental):
                    raise ValueError("duplicate endpoint")
                health = await async_fetch_gateway_health(self.hass, candidate)
                if (
                    health.health_schema_version < 6
                    or health.provider_id is None
                    or health.status != "ok"
                    or health.reauthentication_required
                    or not health.snapshot_available
                ):
                    raise PortfolioRestError("Primary Gateway is not ready for live use")
                if any(item.provider_id == health.provider_id for item in supplemental):
                    raise ValueError("duplicate provider")
                if candidate.endpoint_url != existing.endpoint_url:
                    if current_provider_id is None or health.provider_id != current_provider_id:
                        raise ValueError("primary provider identity changed")
                elif current_provider_id is not None and health.provider_id != current_provider_id:
                    raise ValueError("primary provider identity changed")
                result = await async_fetch_rest_snapshot(self.hass, candidate)
                snapshot = result.snapshot
                if (
                    snapshot is None
                    or result.snapshot_sha256 is None
                    or result.position_count is None
                    or result.position_count != len(snapshot.positions)
                    or health.snapshot_generated_at is None
                    or health.snapshot_generated_at != snapshot.generated_at
                    or health.snapshot_position_count != len(snapshot.positions)
                    or health.snapshot_sha256 != result.snapshot_sha256
                ):
                    raise PortfolioRestError("Primary Gateway health does not match its live snapshot")
            except PortfolioRestAuthenticationError:
                errors["base"] = "invalid_auth"
            except (OSError, ValueError, PortfolioRestError):
                errors["base"] = "invalid_rest_gateway"
            else:
                data = dict(self.config_entry.data)
                data[CONF_REST_ENDPOINT_URL] = candidate.endpoint_url
                data[CONF_REST_API_TOKEN] = candidate.api_token
                if candidate.tls_ca_certificate is None:
                    data.pop(CONF_REST_TLS_CA_CERTIFICATE, None)
                else:
                    data[CONF_REST_TLS_CA_CERTIFICATE] = candidate.tls_ca_certificate
                self.hass.config_entries.async_update_entry(self.config_entry, data=data)
                return self.async_create_entry(data=dict(self.config_entry.options))
        provider_label = (current_provider_id or "unknown").replace("_", " ").title()
        return self.async_show_form(
            step_id="primary_rest_gateway",
            data_schema=self.add_suggested_values_to_schema(
                _rest_source_schema(), suggested
            ),
            errors=errors,
            description_placeholders={
                "provider": provider_label,
                "endpoint": existing.endpoint_url,
            },
        )

    async def async_step_rest_gateways(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage additional authenticated local REST Gateways."""
        del user_input
        if self.config_entry.data.get(CONF_SOURCE_TYPE) != SOURCE_TYPE_REST_API:
            return self.async_abort(reason="rest_gateways_require_rest_primary")
        stored = self._supplemental_rest_sources()
        menu = ["add_rest_gateway"]
        if stored:
            menu.extend(["edit_rest_gateway", "remove_rest_gateway"])
        return self.async_show_menu(step_id="rest_gateways", menu_options=menu)

    async def async_step_edit_rest_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select one supplemental Gateway for editing."""
        stored = self._supplemental_rest_sources()
        if not stored:
            return self.async_abort(reason="no_rest_gateways")
        provider_ids = [item.provider_id for item in stored]
        if user_input is not None:
            selected = str(user_input["provider_id"])
            if selected not in provider_ids:
                return self.async_abort(reason="no_rest_gateways")
            self._rest_gateway_provider_id = selected
            return await self.async_step_edit_rest_gateway_details()
        return self.async_show_form(
            step_id="edit_rest_gateway",
            data_schema=vol.Schema(
                {
                    vol.Required("provider_id"): SelectSelector(
                        SelectSelectorConfig(
                            options=provider_ids,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_edit_rest_gateway_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit transport/authentication for one immutable supplemental provider."""
        selected = self._rest_gateway_provider_id
        stored = self._supplemental_rest_sources()
        existing = next((item for item in stored if item.provider_id == selected), None)
        if existing is None:
            return self.async_abort(reason="no_rest_gateways")
        existing_transport = existing.rest_config
        suggested = {
            CONF_REST_ENDPOINT_URL: existing.endpoint_url,
            CONF_REST_API_TOKEN: existing.api_token,
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            try:
                candidate = self._rest_edit_candidate(user_input, existing_transport)
                if urlsplit(candidate.endpoint_url).scheme != "https":
                    raise PortfolioRestTlsError("Additional Gateways must use verified HTTPS")
                primary = RestSourceConfig.from_mapping(dict(self.config_entry.data))
                if candidate.endpoint_url == primary.endpoint_url or any(
                    item.provider_id != existing.provider_id
                    and item.endpoint_url == candidate.endpoint_url
                    for item in stored
                ):
                    raise ValueError("duplicate endpoint")
                health = await async_fetch_gateway_health(self.hass, candidate)
                if (
                    health.health_schema_version < 6
                    or health.provider_id != existing.provider_id
                    or health.status != "ok"
                    or health.reauthentication_required
                    or not health.snapshot_available
                ):
                    raise PortfolioRestError("Edited Gateway is not ready for live use")
                primary_health = await async_fetch_gateway_health(self.hass, primary)
                if (
                    primary_health.health_schema_version < 6
                    or primary_health.provider_id is None
                    or primary_health.status != "ok"
                    or primary_health.reauthentication_required
                    or not primary_health.snapshot_available
                    or primary_health.provider_id == health.provider_id
                ):
                    raise PortfolioRestError("Primary Gateway is not ready for multi-Gateway configuration")
                result = await async_fetch_rest_snapshot(self.hass, candidate)
                snapshot = result.snapshot
                if (
                    snapshot is None
                    or result.snapshot_sha256 is None
                    or result.position_count is None
                    or result.position_count != len(snapshot.positions)
                    or health.snapshot_generated_at is None
                    or health.snapshot_generated_at != snapshot.generated_at
                    or health.snapshot_position_count != len(snapshot.positions)
                    or health.snapshot_sha256 != result.snapshot_sha256
                ):
                    raise PortfolioRestError("Edited Gateway health does not match its live snapshot")
            except PortfolioRestAuthenticationError:
                errors["base"] = "invalid_auth"
            except (OSError, ValueError, PortfolioRestError):
                errors["base"] = "invalid_rest_gateway"
            else:
                configured = SupplementalRestSourceConfig(
                    provider_id=existing.provider_id,
                    endpoint_url=candidate.endpoint_url,
                    api_token=candidate.api_token,
                    tls_ca_certificate=candidate.tls_ca_certificate,
                )
                options = dict(self.config_entry.options)
                options[CONF_SUPPLEMENTAL_REST_SOURCES] = [
                    configured.as_storage_dict()
                    if item.provider_id == existing.provider_id
                    else item.as_storage_dict()
                    for item in stored
                ]
                return self.async_create_entry(data=options)
        return self.async_show_form(
            step_id="edit_rest_gateway_details",
            data_schema=self.add_suggested_values_to_schema(
                _rest_source_schema(), suggested
            ),
            errors=errors,
            description_placeholders={
                "provider": existing.provider_id.replace("_", " ").title(),
                "provider_id": existing.provider_id,
                "endpoint": existing.endpoint_url,
            },
        )

    async def async_step_add_rest_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate and append one provider-identified local REST Gateway."""
        options = dict(self.config_entry.options)
        raw_sources = options.get(CONF_SUPPLEMENTAL_REST_SOURCES, [])
        stored = raw_sources if isinstance(raw_sources, list) else []
        errors: dict[str, str] = {}
        suggested = {
            CONF_REST_ENDPOINT_URL: "",
            CONF_REST_API_TOKEN: "",
        }
        if user_input is not None:
            suggested.update(user_input)
            if len(stored) >= MAX_SUPPLEMENTAL_REST_SOURCES:
                errors["base"] = "too_many_rest_gateways"
            else:
                try:
                    candidate_transport = RestSourceConfig.from_mapping(user_input)
                    if urlsplit(candidate_transport.endpoint_url).scheme != "https":
                        raise PortfolioRestTlsError("Additional Gateways must use verified HTTPS")
                    existing = tuple(
                        SupplementalRestSourceConfig.from_mapping(item)
                        for item in stored
                        if isinstance(item, dict)
                    )
                    endpoints = {item.endpoint_url for item in existing}
                    primary_endpoint = self.config_entry.data.get(CONF_REST_ENDPOINT_URL)
                    if candidate_transport.endpoint_url in endpoints or (
                        isinstance(primary_endpoint, str)
                        and candidate_transport.endpoint_url == RestSourceConfig.from_mapping(
                            self.config_entry.data
                        ).endpoint_url
                    ):
                        raise ValueError("duplicate endpoint")
                    health = await async_fetch_gateway_health(self.hass, candidate_transport)
                    if (
                        health.health_schema_version < 6
                        or health.provider_id is None
                        or health.status != "ok"
                        or health.reauthentication_required
                        or not health.snapshot_available
                    ):
                        raise PortfolioRestError("Additional Gateway is not ready for live use")
                    if any(item.provider_id == health.provider_id for item in existing):
                        raise ValueError("duplicate provider")
                    if self.config_entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_REST_API:
                        primary = RestSourceConfig.from_mapping(dict(self.config_entry.data))
                        primary_health = await async_fetch_gateway_health(self.hass, primary)
                        if (
                            primary_health.health_schema_version < 6
                            or primary_health.provider_id is None
                            or primary_health.status != "ok"
                            or primary_health.reauthentication_required
                            or not primary_health.snapshot_available
                        ):
                            raise PortfolioRestError(
                                "Primary Gateway is not ready for multi-Gateway configuration"
                            )
                        if primary_health.provider_id == health.provider_id:
                            raise ValueError("duplicate provider")
                    result = await async_fetch_rest_snapshot(self.hass, candidate_transport)
                    snapshot = result.snapshot
                    if snapshot is None:
                        raise PortfolioRestError("Additional Gateway returned no live snapshot")
                    if result.snapshot_sha256 is None or result.position_count is None:
                        raise PortfolioRestError(
                            "Additional Gateway integrity metadata is incomplete"
                        )
                    if result.position_count != len(snapshot.positions):
                        raise PortfolioRestError(
                            "Additional Gateway position count is inconsistent"
                        )
                    if (
                        health.snapshot_generated_at is None
                        or health.snapshot_generated_at != snapshot.generated_at
                        or health.snapshot_position_count != len(snapshot.positions)
                        or health.snapshot_sha256 != result.snapshot_sha256
                    ):
                        raise PortfolioRestError(
                            "Additional Gateway health does not match its live snapshot"
                        )
                except PortfolioRestAuthenticationError:
                    errors["base"] = "invalid_auth"
                except (OSError, ValueError, PortfolioRestError):
                    errors["base"] = "invalid_rest_gateway"
                else:
                    configured = SupplementalRestSourceConfig(
                        provider_id=health.provider_id,
                        endpoint_url=candidate_transport.endpoint_url,
                        api_token=candidate_transport.api_token,
                        tls_ca_certificate=candidate_transport.tls_ca_certificate,
                    )
                    options[CONF_SUPPLEMENTAL_REST_SOURCES] = [
                        *stored,
                        configured.as_storage_dict(),
                    ]
                    return self.async_create_entry(data=options)
        return self.async_show_form(
            step_id="add_rest_gateway",
            data_schema=self.add_suggested_values_to_schema(
                _rest_source_schema(), suggested
            ),
            errors=errors,
        )

    async def async_step_remove_rest_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove one additional Gateway without touching the primary source."""
        options = dict(self.config_entry.options)
        raw_sources = options.get(CONF_SUPPLEMENTAL_REST_SOURCES, [])
        stored = (
            [
                SupplementalRestSourceConfig.from_mapping(item)
                for item in raw_sources
                if isinstance(item, dict)
            ]
            if isinstance(raw_sources, list)
            else []
        )
        if not stored:
            return self.async_abort(reason="no_rest_gateways")
        provider_ids = [item.provider_id for item in stored]
        if user_input is not None:
            selected = str(user_input["provider_id"])
            options[CONF_SUPPLEMENTAL_REST_SOURCES] = [
                item.as_storage_dict() for item in stored if item.provider_id != selected
            ]
            if not options[CONF_SUPPLEMENTAL_REST_SOURCES]:
                options.pop(CONF_SUPPLEMENTAL_REST_SOURCES, None)
            return self.async_create_entry(data=options)
        return self.async_show_form(
            step_id="remove_rest_gateway",
            data_schema=vol.Schema(
                {
                    vol.Required("provider_id"): SelectSelector(
                        SelectSelectorConfig(
                            options=provider_ids,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_plan_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure recurring execution/review scheduling independently of target scope."""
        options = dict(self.config_entry.options)
        suggested = {
            CONF_PLAN_SCHEDULE_ENABLED: bool(
                options.get(CONF_PLAN_SCHEDULE_ENABLED, False)
            ),
            CONF_PLAN_FREQUENCY: options.get(
                CONF_PLAN_FREQUENCY, DEFAULT_PLAN_FREQUENCY
            ),
        }
        if user_input is not None:
            enabled = bool(user_input[CONF_PLAN_SCHEDULE_ENABLED])
            frequency = str(user_input[CONF_PLAN_FREQUENCY])
            if not enabled:
                options[CONF_PLAN_SCHEDULE_ENABLED] = False
                options[CONF_PLAN_FREQUENCY] = frequency
                for key in (
                    CONF_PLAN_EXECUTION_DAYS,
                    CONF_PLAN_EXECUTION_MONTH,
                    CONF_PLAN_EXECUTION_MONTH_OFFSET,
                    CONF_REVIEW_LEAD_DAYS,
                ):
                    options.pop(key, None)
                return self.async_create_entry(data=options)
            self._schedule_settings_draft = {
                CONF_PLAN_SCHEDULE_ENABLED: True,
                CONF_PLAN_FREQUENCY: frequency,
            }
            return await self.async_step_plan_schedule_details()

        schema = vol.Schema(
            {
                vol.Required(CONF_PLAN_SCHEDULE_ENABLED): BooleanSelector(
                    BooleanSelectorConfig()
                ),
                vol.Required(CONF_PLAN_FREQUENCY): SelectSelector(
                    SelectSelectorConfig(
                        options=list(PLAN_FREQUENCIES),
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="plan_frequency",
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="plan_schedule",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
        )

    async def async_step_plan_schedule_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the dates for the independent recurring plan schedule."""
        if not self._schedule_settings_draft:
            return self.async_abort(reason="invalid_schedule")
        frequency = str(self._schedule_settings_draft[CONF_PLAN_FREQUENCY])
        options = dict(self.config_entry.options)
        maximum_day = 7 if frequency == PLAN_FREQUENCY_WEEKLY else 28
        suggested: dict[str, Any] = {
            CONF_REVIEW_LEAD_DAYS: int(
                options.get(CONF_REVIEW_LEAD_DAYS, DEFAULT_REVIEW_LEAD_DAYS)
            ),
            CONF_PLAN_EXECUTION_DAYS: _safe_execution_day_strings(
                options.get(CONF_PLAN_EXECUTION_DAYS), maximum=maximum_day
            ),
        }
        if frequency == PLAN_FREQUENCY_QUARTERLY:
            suggested[CONF_PLAN_EXECUTION_MONTH_OFFSET] = str(
                options.get(CONF_PLAN_EXECUTION_MONTH_OFFSET, 1)
            )
        elif frequency == PLAN_FREQUENCY_YEARLY:
            suggested[CONF_PLAN_EXECUTION_MONTH] = str(
                options.get(CONF_PLAN_EXECUTION_MONTH, 1)
            )

        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            days = [int(value) for value in user_input[CONF_PLAN_EXECUTION_DAYS]]
            month = user_input.get(CONF_PLAN_EXECUTION_MONTH)
            offset = user_input.get(CONF_PLAN_EXECUTION_MONTH_OFFSET)
            try:
                schedule = validate_schedule_config(
                    frequency,
                    days,
                    execution_month=int(month) if month is not None else None,
                    execution_month_offset=int(offset) if offset is not None else None,
                )
            except (TypeError, ValueError):
                errors["base"] = "invalid_schedule"
            else:
                options[CONF_PLAN_SCHEDULE_ENABLED] = True
                options[CONF_PLAN_FREQUENCY] = schedule.frequency
                options[CONF_REVIEW_LEAD_DAYS] = int(
                    user_input[CONF_REVIEW_LEAD_DAYS]
                )
                options[CONF_PLAN_EXECUTION_DAYS] = list(schedule.execution_days)
                if schedule.execution_month is None:
                    options.pop(CONF_PLAN_EXECUTION_MONTH, None)
                else:
                    options[CONF_PLAN_EXECUTION_MONTH] = schedule.execution_month
                if schedule.execution_month_offset is None:
                    options.pop(CONF_PLAN_EXECUTION_MONTH_OFFSET, None)
                else:
                    options[CONF_PLAN_EXECUTION_MONTH_OFFSET] = (
                        schedule.execution_month_offset
                    )
                self._schedule_settings_draft = None
                return self.async_create_entry(data=options)

        return self.async_show_form(
            step_id="plan_schedule_details",
            data_schema=self.add_suggested_values_to_schema(
                _schedule_schema(frequency), suggested
            ),
            errors=errors,
        )

    async def async_step_execution(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the cost-aware execution policy and reserve source."""
        options = dict(self.config_entry.options)
        suggested = {
            CONF_EXECUTION_COST_AWARE_ENABLED: bool(
                options.get(CONF_EXECUTION_COST_AWARE_ENABLED, False)
            ),
            CONF_EXECUTION_POLICY: options.get(CONF_EXECUTION_POLICY, "balanced"),
            CONF_EXECUTION_MAX_COST_RATIO_PCT: options.get(
                CONF_EXECUTION_MAX_COST_RATIO_PCT, 1.5
            ),
            CONF_EXECUTION_MAX_DEFERRAL_PERIODS: options.get(
                CONF_EXECUTION_MAX_DEFERRAL_PERIODS, 3
            ),
            CONF_EXECUTION_MAX_ORDERS: options.get(CONF_EXECUTION_MAX_ORDERS, 1),
            CONF_EXECUTION_RESERVE_MODE: options.get(
                CONF_EXECUTION_RESERVE_MODE, "gateway_balance"
            ),
        }
        if user_input is not None:
            self._execution_draft = dict(user_input)
            return await self.async_step_execution_fees()

        return self.async_show_form(
            step_id="execution",
            data_schema=self.add_suggested_values_to_schema(
                _execution_policy_schema(), suggested
            ),
        )

    async def async_step_execution_fees(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the manual-order fee model with serialization-safe fields."""
        options = dict(self.config_entry.options)
        venue_fee_pct = Decimal(
            str(options.get(CONF_MANUAL_VENUE_FEE_PCT, 0.0025))
        )
        suggested = {
            CONF_MANUAL_COMMISSION_BASE_EUR: options.get(
                CONF_MANUAL_COMMISSION_BASE_EUR, 4.90
            ),
            CONF_MANUAL_COMMISSION_PCT: options.get(
                CONF_MANUAL_COMMISSION_PCT, 0.25
            ),
            CONF_MANUAL_COMMISSION_MIN_EUR: options.get(
                CONF_MANUAL_COMMISSION_MIN_EUR, 9.90
            ),
            CONF_MANUAL_COMMISSION_MAX_EUR: options.get(
                CONF_MANUAL_COMMISSION_MAX_EUR, 59.90
            ),
            CONF_MANUAL_VENUE_FEE_BPS: float(venue_fee_pct * Decimal("100")),
            CONF_MANUAL_VENUE_FEE_MIN_EUR: options.get(
                CONF_MANUAL_VENUE_FEE_MIN_EUR, 2.50
            ),
            CONF_MANUAL_SETTLEMENT_FEE_EUR: options.get(
                CONF_MANUAL_SETTLEMENT_FEE_EUR, 2.90
            ),
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            draft = self._execution_draft or {
                CONF_EXECUTION_COST_AWARE_ENABLED: bool(
                    options.get(CONF_EXECUTION_COST_AWARE_ENABLED, False)
                ),
                CONF_EXECUTION_POLICY: options.get(
                    CONF_EXECUTION_POLICY, "balanced"
                ),
                CONF_EXECUTION_MAX_COST_RATIO_PCT: options.get(
                    CONF_EXECUTION_MAX_COST_RATIO_PCT, 1.5
                ),
                CONF_EXECUTION_MAX_DEFERRAL_PERIODS: options.get(
                    CONF_EXECUTION_MAX_DEFERRAL_PERIODS, 3
                ),
                CONF_EXECUTION_MAX_ORDERS: options.get(
                    CONF_EXECUTION_MAX_ORDERS, 1
                ),
                CONF_EXECUTION_RESERVE_MODE: options.get(
                    CONF_EXECUTION_RESERVE_MODE, "gateway_balance"
                ),
            }
            venue_fee_pct = Decimal(
                str(user_input[CONF_MANUAL_VENUE_FEE_BPS])
            ) / Decimal("100")
            stored = {
                **draft,
                CONF_MANUAL_COMMISSION_BASE_EUR: user_input[
                    CONF_MANUAL_COMMISSION_BASE_EUR
                ],
                CONF_MANUAL_COMMISSION_PCT: user_input[
                    CONF_MANUAL_COMMISSION_PCT
                ],
                CONF_MANUAL_COMMISSION_MIN_EUR: user_input[
                    CONF_MANUAL_COMMISSION_MIN_EUR
                ],
                CONF_MANUAL_COMMISSION_MAX_EUR: user_input[
                    CONF_MANUAL_COMMISSION_MAX_EUR
                ],
                CONF_MANUAL_VENUE_FEE_PCT: float(venue_fee_pct),
                CONF_MANUAL_VENUE_FEE_MIN_EUR: user_input[
                    CONF_MANUAL_VENUE_FEE_MIN_EUR
                ],
                CONF_MANUAL_SETTLEMENT_FEE_EUR: user_input[
                    CONF_MANUAL_SETTLEMENT_FEE_EUR
                ],
            }
            execution_mapping = {
                "enabled": bool(stored[CONF_EXECUTION_COST_AWARE_ENABLED]),
                "policy": stored[CONF_EXECUTION_POLICY],
                "max_cost_ratio_pct": stored[CONF_EXECUTION_MAX_COST_RATIO_PCT],
                "max_deferral_periods": stored[
                    CONF_EXECUTION_MAX_DEFERRAL_PERIODS
                ],
                "max_orders_per_execution": stored[CONF_EXECUTION_MAX_ORDERS],
                "reserve_mode": stored[CONF_EXECUTION_RESERVE_MODE],
                "manual_commission_base_eur": stored[
                    CONF_MANUAL_COMMISSION_BASE_EUR
                ],
                "manual_commission_pct": stored[CONF_MANUAL_COMMISSION_PCT],
                "manual_commission_min_eur": stored[
                    CONF_MANUAL_COMMISSION_MIN_EUR
                ],
                "manual_commission_max_eur": stored[
                    CONF_MANUAL_COMMISSION_MAX_EUR
                ],
                "manual_venue_fee_pct": stored[CONF_MANUAL_VENUE_FEE_PCT],
                "manual_venue_fee_min_eur": stored[
                    CONF_MANUAL_VENUE_FEE_MIN_EUR
                ],
                "manual_settlement_fee_eur": stored[
                    CONF_MANUAL_SETTLEMENT_FEE_EUR
                ],
            }
            try:
                ExecutionConfig.from_mapping(execution_mapping)
            except (ValueError, ArithmeticError):
                errors["base"] = "invalid_execution_config"
            else:
                options.update(stored)
                self._execution_draft = None
                return self.async_create_entry(data=options)

        return self.async_show_form(
            step_id="execution_fees",
            data_schema=self.add_suggested_values_to_schema(
                _execution_fees_schema(), suggested
            ),
            errors=errors,
            last_step=True,
        )

    async def async_step_execution_providers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage provider-aware broker.yaml through native validated forms."""
        del user_input
        try:
            context = await self._async_broker_context()
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        providers = context.document.get("providers", {})
        menu = ["broker_settings", "broker_providers", "broker_savings_plans"]
        if isinstance(providers, dict) and len(providers) >= 2:
            menu.append("funding_topology")
        return self.async_show_menu(step_id="execution_providers", menu_options=menu)

    async def async_step_broker_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the common provider-evidence freshness window."""
        try:
            context = await self._async_broker_context()
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        suggested = {
            CONF_BROKER_FEE_DATA_MAX_AGE_DAYS: int(
                context.document.get("fee_data_max_age_days", 30)
            )
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            try:
                updated = set_general_settings(
                    context.document,
                    fee_data_max_age_days=int(user_input[CONF_BROKER_FEE_DATA_MAX_AGE_DAYS]),
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except (OSError, ValueError):
                errors["base"] = "invalid_broker_config"
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="broker_settings",
            data_schema=self.add_suggested_values_to_schema(_broker_settings_schema(), suggested),
            errors=errors,
            last_step=True,
        )

    async def async_step_broker_providers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose a provider-management action."""
        del user_input
        try:
            context = await self._async_broker_context()
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        providers = context.document.get("providers", {})
        menu = ["add_execution_provider"]
        if isinstance(providers, dict) and providers:
            menu.extend(["edit_execution_provider", "remove_execution_provider"])
        return self.async_show_menu(step_id="broker_providers", menu_options=menu)

    async def async_step_add_execution_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add one provider with explicit evidence and neutral tie-break by default."""
        errors: dict[str, str] = {}
        suggested = {
            CONF_BROKER_PROVIDER_ID: "",
            CONF_BROKER_PROVIDER_NAME: "",
            CONF_BROKER_PROVIDER_SOURCE: "",
            CONF_BROKER_PROVIDER_AS_OF: dt_util.now().date().isoformat(),
            CONF_BROKER_TIE_BREAK: TIE_BREAK_NEUTRAL,
        }
        if user_input is not None:
            suggested.update(user_input)
            try:
                context = await self._async_broker_context()
                updated = upsert_provider(
                    context.document,
                    provider_id=str(user_input[CONF_BROKER_PROVIDER_ID]),
                    name=str(user_input[CONF_BROKER_PROVIDER_NAME]),
                    source=str(user_input[CONF_BROKER_PROVIDER_SOURCE]),
                    as_of=str(user_input[CONF_BROKER_PROVIDER_AS_OF]),
                    tie_break=str(user_input[CONF_BROKER_TIE_BREAK]),
                    create=True,
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except ValueError as err:
                if str(err) == "provider already exists":
                    errors[CONF_BROKER_PROVIDER_ID] = "provider_already_exists"
                else:
                    errors["base"] = "invalid_broker_config"
            except (OSError, PortfolioSourcePathError):
                errors["base"] = "invalid_broker_config"
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="add_execution_provider",
            data_schema=self.add_suggested_values_to_schema(_broker_provider_schema(include_id=True), suggested),
            errors=errors,
            last_step=True,
        )

    async def async_step_edit_execution_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select one provider for editing."""
        try:
            context = await self._async_broker_context()
            options = _broker_provider_select_options(context.document)
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if user_input is not None:
            provider_id = str(user_input[CONF_BROKER_PROVIDER_ID])
            if provider_id not in {item["value"] for item in options}:
                return self.async_abort(reason="broker_editor_unavailable")
            self._broker_provider_id = provider_id
            return await self.async_step_edit_execution_provider_details()
        return self.async_show_form(
            step_id="edit_execution_provider",
            data_schema=_broker_provider_select_schema(options),
        )

    async def async_step_edit_execution_provider_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit evidence and tie-break semantics for the selected provider."""
        provider_id = self._broker_provider_id
        if provider_id is None:
            return self.async_abort(reason="broker_editor_unavailable")
        errors: dict[str, str] = {}
        try:
            context = await self._async_broker_context()
            provider = context.document.get("providers", {}).get(provider_id)
            if not isinstance(provider, dict):
                raise ValueError("provider disappeared")
            suggested = {
                CONF_BROKER_PROVIDER_NAME: provider.get("name", provider_id),
                CONF_BROKER_PROVIDER_SOURCE: provider.get("source", ""),
                CONF_BROKER_PROVIDER_AS_OF: str(provider.get("as_of", "")),
                CONF_BROKER_TIE_BREAK: tie_break_mode(provider),
            }
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if user_input is not None:
            suggested.update(user_input)
            try:
                updated = upsert_provider(
                    context.document,
                    provider_id=provider_id,
                    name=str(user_input[CONF_BROKER_PROVIDER_NAME]),
                    source=str(user_input[CONF_BROKER_PROVIDER_SOURCE]),
                    as_of=str(user_input[CONF_BROKER_PROVIDER_AS_OF]),
                    tie_break=str(user_input[CONF_BROKER_TIE_BREAK]),
                    create=False,
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except (OSError, ValueError):
                errors["base"] = "invalid_broker_config"
            else:
                self._broker_provider_id = None
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="edit_execution_provider_details",
            data_schema=self.add_suggested_values_to_schema(_broker_provider_schema(include_id=False), suggested),
            description_placeholders={
                "provider_name": str(provider.get("name") or provider_id),
                "provider_id": provider_id,
            },
            errors=errors,
            last_step=True,
        )

    async def async_step_remove_execution_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove one provider after its transfer edges have been removed."""
        errors: dict[str, str] = {}
        try:
            context = await self._async_broker_context()
            options = _broker_provider_select_options(context.document)
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if user_input is not None:
            try:
                updated = remove_provider(
                    context.document,
                    provider_id=str(user_input[CONF_BROKER_PROVIDER_ID]),
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except (OSError, ValueError):
                errors["base"] = "invalid_broker_config"
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="remove_execution_provider",
            data_schema=_broker_provider_select_schema(options),
            errors=errors,
            last_step=True,
        )

    async def async_step_broker_savings_plans(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose a savings-plan route action."""
        del user_input
        try:
            context = await self._async_broker_context()
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        routes = _broker_savings_route_options(context.document)
        menu = ["add_savings_plan_route"]
        if routes:
            menu.extend(["edit_savings_plan_route", "remove_savings_plan_route"])
        return self.async_show_menu(step_id="broker_savings_plans", menu_options=menu)

    async def async_step_add_savings_plan_route(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add one instrument-specific savings-plan route."""
        errors: dict[str, str] = {}
        try:
            context = await self._async_broker_context()
            providers = _broker_provider_select_options(context.document)
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        suggested = {
            CONF_BROKER_PROVIDER_ID: providers[0]["value"] if providers else "",
            CONF_BROKER_ISIN: "",
            CONF_BROKER_AVAILABLE: True,
            CONF_BROKER_FEE_PCT: 0.0,
            CONF_BROKER_PROMOTIONAL: False,
            CONF_BROKER_STATUS: "",
            CONF_BROKER_ROUTE_SOURCE: "",
            CONF_BROKER_ROUTE_AS_OF: dt_util.now().date().isoformat(),
        }
        if user_input is not None:
            suggested.update(user_input)
            try:
                updated = upsert_savings_plan(
                    context.document,
                    provider_id=str(user_input[CONF_BROKER_PROVIDER_ID]),
                    isin=str(user_input[CONF_BROKER_ISIN]),
                    available=bool(user_input[CONF_BROKER_AVAILABLE]),
                    fee_pct=float(user_input[CONF_BROKER_FEE_PCT]),
                    promotional=bool(user_input[CONF_BROKER_PROMOTIONAL]),
                    status=str(user_input.get(CONF_BROKER_STATUS, "")),
                    source=str(user_input[CONF_BROKER_ROUTE_SOURCE]),
                    as_of=str(user_input[CONF_BROKER_ROUTE_AS_OF]),
                    create=True,
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except ValueError as err:
                if str(err) == "savings-plan route already exists":
                    errors[CONF_BROKER_ISIN] = "savings_plan_route_already_exists"
                else:
                    errors["base"] = "invalid_broker_config"
            except OSError:
                errors["base"] = "invalid_broker_config"
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="add_savings_plan_route",
            data_schema=self.add_suggested_values_to_schema(_broker_savings_plan_schema(providers, include_identity=True), suggested),
            errors=errors,
            last_step=True,
        )

    async def async_step_edit_savings_plan_route(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select one existing savings-plan route."""
        try:
            context = await self._async_broker_context()
            routes = _broker_savings_route_options(context.document)
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if not routes:
            return self.async_abort(reason="broker_editor_unavailable")
        if user_input is not None:
            token = str(user_input[CONF_BROKER_SAVINGS_ROUTE])
            if token not in {item["value"] for item in routes}:
                return self.async_abort(reason="broker_editor_unavailable")
            self._broker_route_token = token
            return await self.async_step_edit_savings_plan_route_details()
        return self.async_show_form(
            step_id="edit_savings_plan_route",
            data_schema=_broker_route_select_schema(routes),
        )

    async def async_step_edit_savings_plan_route_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit fee and promotional provenance for one savings-plan route."""
        token = self._broker_route_token
        if token is None or "|" not in token:
            return self.async_abort(reason="broker_editor_unavailable")
        provider_id, isin = token.split("|", 1)
        errors: dict[str, str] = {}
        try:
            context = await self._async_broker_context()
            provider = context.document.get("providers", {}).get(provider_id)
            route = provider.get("savings_plans", {}).get(isin) if isinstance(provider, dict) else None
            if not isinstance(route, dict):
                raise ValueError("route disappeared")
            providers = _broker_provider_select_options(context.document)
            suggested = {
                CONF_BROKER_AVAILABLE: bool(route.get("available")),
                CONF_BROKER_FEE_PCT: float(route.get("fee_pct", 0.0)),
                CONF_BROKER_PROMOTIONAL: bool(route.get("promotional", False)),
                CONF_BROKER_STATUS: str(route.get("status") or ""),
                CONF_BROKER_ROUTE_SOURCE: str(route.get("source") or provider.get("source") or ""),
                CONF_BROKER_ROUTE_AS_OF: str(route.get("as_of") or provider.get("as_of") or dt_util.now().date().isoformat()),
            }
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if user_input is not None:
            suggested.update(user_input)
            try:
                updated = upsert_savings_plan(
                    context.document,
                    provider_id=provider_id,
                    isin=isin,
                    available=bool(user_input[CONF_BROKER_AVAILABLE]),
                    fee_pct=float(user_input[CONF_BROKER_FEE_PCT]),
                    promotional=bool(user_input[CONF_BROKER_PROMOTIONAL]),
                    status=str(user_input.get(CONF_BROKER_STATUS, "")),
                    source=str(user_input[CONF_BROKER_ROUTE_SOURCE]),
                    as_of=str(user_input[CONF_BROKER_ROUTE_AS_OF]),
                    create=False,
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except (OSError, ValueError):
                errors["base"] = "invalid_broker_config"
            else:
                self._broker_route_token = None
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="edit_savings_plan_route_details",
            data_schema=self.add_suggested_values_to_schema(_broker_savings_plan_schema(providers, include_identity=False), suggested),
            description_placeholders={
                "provider_name": str(provider.get("name") or provider_id),
                "provider_id": provider_id,
                "isin": isin,
            },
            errors=errors,
            last_step=True,
        )

    async def async_step_remove_savings_plan_route(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove one explicit savings-plan route."""
        errors: dict[str, str] = {}
        try:
            context = await self._async_broker_context()
            routes = _broker_savings_route_options(context.document)
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if not routes:
            return self.async_abort(reason="broker_editor_unavailable")
        if user_input is not None:
            token = str(user_input[CONF_BROKER_SAVINGS_ROUTE])
            try:
                provider_id, isin = token.split("|", 1)
                updated = remove_savings_plan(
                    context.document,
                    provider_id=provider_id,
                    isin=isin,
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except (OSError, ValueError):
                errors["base"] = "invalid_broker_config"
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="remove_savings_plan_route",
            data_schema=_broker_route_select_schema(routes),
            errors=errors,
            last_step=True,
        )

    async def async_step_funding_topology(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage exact directed advisory funding edges."""
        del user_input
        try:
            context = await self._async_broker_context()
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        menu = ["add_funding_transfer"]
        if _broker_funding_edge_options(context.document):
            menu.append("edit_funding_transfer")
            menu.append("remove_funding_transfer")
        return self.async_show_menu(step_id="funding_topology", menu_options=menu)

    async def async_step_add_funding_transfer(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add one exact directed transfer edge with explicit cost and delay."""
        errors: dict[str, str] = {}
        try:
            context = await self._async_broker_context()
            providers = _broker_provider_select_options(context.document)
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if len(providers) < 2:
            return self.async_abort(reason="broker_editor_unavailable")
        suggested = {
            CONF_BROKER_FROM_PROVIDER: providers[0]["value"],
            CONF_BROKER_TO_PROVIDER: providers[1]["value"],
            CONF_BROKER_TRANSFER_FEE_EUR: 0.0,
            CONF_BROKER_SETTLEMENT_DAYS: 0,
            CONF_BROKER_TRANSFER_SOURCE: "",
            CONF_BROKER_TRANSFER_AS_OF: dt_util.now().date().isoformat(),
        }
        if user_input is not None:
            suggested.update(user_input)
            try:
                updated = add_funding_transfer(
                    context.document,
                    from_provider=str(user_input[CONF_BROKER_FROM_PROVIDER]),
                    to_provider=str(user_input[CONF_BROKER_TO_PROVIDER]),
                    fee_eur=float(user_input[CONF_BROKER_TRANSFER_FEE_EUR]),
                    settlement_business_days=int(user_input[CONF_BROKER_SETTLEMENT_DAYS]),
                    source=str(user_input[CONF_BROKER_TRANSFER_SOURCE]),
                    as_of=str(user_input[CONF_BROKER_TRANSFER_AS_OF]),
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except ValueError as err:
                if str(err) == "funding transfer already exists":
                    errors[CONF_BROKER_TO_PROVIDER] = "funding_transfer_already_exists"
                else:
                    errors["base"] = "invalid_broker_config"
            except OSError:
                errors["base"] = "invalid_broker_config"
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="add_funding_transfer",
            data_schema=self.add_suggested_values_to_schema(_broker_funding_schema(providers, include_identity=True), suggested),
            errors=errors,
            last_step=True,
        )

    async def async_step_edit_funding_transfer(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select one existing directed funding edge."""
        try:
            context = await self._async_broker_context()
            edges = _broker_funding_edge_options(context.document)
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if not edges:
            return self.async_abort(reason="broker_editor_unavailable")
        if user_input is not None:
            token = str(user_input[CONF_BROKER_FUNDING_EDGE])
            if token not in {item["value"] for item in edges}:
                return self.async_abort(reason="broker_editor_unavailable")
            self._broker_funding_token = token
            return await self.async_step_edit_funding_transfer_details()
        return self.async_show_form(
            step_id="edit_funding_transfer",
            data_schema=_broker_funding_edge_select_schema(edges),
        )

    async def async_step_edit_funding_transfer_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit economics and evidence for one exact directed funding edge."""
        token = self._broker_funding_token
        if token is None or "|" not in token:
            return self.async_abort(reason="broker_editor_unavailable")
        source, destination = token.split("|", 1)
        errors: dict[str, str] = {}
        try:
            context = await self._async_broker_context()
            providers = _broker_provider_select_options(context.document)
            edges = context.document.get("funding_transfers", [])
            edge = next(
                (
                    item
                    for item in edges
                    if isinstance(item, dict)
                    and item.get("from_provider") == source
                    and item.get("to_provider") == destination
                ),
                None,
            )
            if not isinstance(edge, dict):
                raise ValueError("funding edge disappeared")
            suggested = {
                CONF_BROKER_TRANSFER_FEE_EUR: float(edge.get("fee_eur", 0.0)),
                CONF_BROKER_SETTLEMENT_DAYS: int(edge.get("settlement_business_days", 0)),
                CONF_BROKER_TRANSFER_SOURCE: str(edge.get("source") or ""),
                CONF_BROKER_TRANSFER_AS_OF: str(edge.get("as_of") or dt_util.now().date().isoformat()),
            }
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if user_input is not None:
            suggested.update(user_input)
            try:
                updated = edit_funding_transfer(
                    context.document,
                    from_provider=source,
                    to_provider=destination,
                    fee_eur=float(user_input[CONF_BROKER_TRANSFER_FEE_EUR]),
                    settlement_business_days=int(user_input[CONF_BROKER_SETTLEMENT_DAYS]),
                    source=str(user_input[CONF_BROKER_TRANSFER_SOURCE]),
                    as_of=str(user_input[CONF_BROKER_TRANSFER_AS_OF]),
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except (OSError, ValueError):
                errors["base"] = "invalid_broker_config"
            else:
                self._broker_funding_token = None
                return self.async_create_entry(data=dict(self.config_entry.options))
        provider_names = {item["value"]: item["label"] for item in providers}
        return self.async_show_form(
            step_id="edit_funding_transfer_details",
            data_schema=self.add_suggested_values_to_schema(
                _broker_funding_schema(providers, include_identity=False), suggested
            ),
            description_placeholders={
                "from_provider_name": provider_names.get(source, source),
                "from_provider_id": source,
                "to_provider_name": provider_names.get(destination, destination),
                "to_provider_id": destination,
            },
            errors=errors,
            last_step=True,
        )

    async def async_step_remove_funding_transfer(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove one directed funding edge without inferring its reverse."""
        errors: dict[str, str] = {}
        try:
            context = await self._async_broker_context()
            edges = _broker_funding_edge_options(context.document)
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="broker_editor_unavailable")
        if not edges:
            return self.async_abort(reason="broker_editor_unavailable")
        if user_input is not None:
            try:
                source, destination = str(user_input[CONF_BROKER_FUNDING_EDGE]).split("|", 1)
                updated = remove_funding_transfer(
                    context.document,
                    from_provider=source,
                    to_provider=destination,
                    evaluated_on=dt_util.now().date(),
                )
                await self._async_write_broker(context.path, updated)
            except (OSError, ValueError):
                errors["base"] = "invalid_broker_config"
            else:
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="remove_funding_transfer",
            data_schema=_broker_funding_edge_select_schema(edges),
            errors=errors,
            last_step=True,
        )

    async def _async_broker_context(self):
        configuration = resolve_configuration_directory(
            self.hass,
            self.config_entry.data[CONF_CONFIG_DIRECTORY],
            require_exists=True,
        )
        return await self.hass.async_add_executor_job(
            load_broker_editor_context,
            configuration.config_directory,
            dt_util.now().date(),
        )

    async def _async_write_broker(self, path, document) -> None:
        await self.hass.async_add_executor_job(
            write_broker_document_atomic, path, document, dt_util.now().date()
        )

    async def async_step_plan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure plan budget, cadence, and scope."""
        try:
            context = await self._async_plan_context()
        except (OSError, ValueError, PortfolioSourcePathError):
            return self.async_abort(reason="plan_source_unavailable")

        options = self.config_entry.options
        selected_defaults = [item.isin for item in context.candidates if item.selected]
        suggested = {
            CONF_PLAN_NAME: options.get(CONF_PLAN_NAME, context.plan_name),
            CONF_PLAN_BUDGET_AMOUNT: options.get(
                CONF_PLAN_BUDGET_AMOUNT, context.budget_amount
            ),
            CONF_PLAN_BUDGET_BASIS: options.get(
                CONF_PLAN_BUDGET_BASIS, DEFAULT_PLAN_BUDGET_BASIS
            ),
            CONF_PLAN_FREQUENCY: options.get(
                CONF_PLAN_FREQUENCY, DEFAULT_PLAN_FREQUENCY
            ),
            CONF_PLAN_SCHEDULE_ENABLED: bool(
                options.get(CONF_PLAN_SCHEDULE_ENABLED, False)
            ),
            "selected_instruments": selected_defaults,
        }
        if user_input is not None:
            suggested.update(user_input)
            selected = list(dict.fromkeys(user_input.get("selected_instruments", [])))
            if not 1 <= len(selected) <= MAX_PLAN_INSTRUMENTS:
                return self.async_show_form(
                    step_id="plan",
                    data_schema=self.add_suggested_values_to_schema(
                        _plan_schema(context), suggested
                    ),
                    errors={"selected_instruments": "invalid_instrument_count"},
                )
            known = {item.isin for item in context.candidates}
            if any(value not in known for value in selected):
                return self.async_show_form(
                    step_id="plan",
                    data_schema=self.add_suggested_values_to_schema(
                        _plan_schema(context), suggested
                    ),
                    errors={"selected_instruments": "invalid_instrument"},
                )

            self._selected_isins = selected
            by_isin = {item.isin: item for item in context.candidates}
            used_target_ids = {
                item.target_id
                for item in context.candidates
                if item.target_id is not None
            }
            self._selected_target_ids = {}
            for isin in selected:
                candidate = by_isin[isin]
                target_id = candidate.target_id
                if target_id is None:
                    target_id = generate_target_id(used_target_ids)
                    used_target_ids.add(target_id)
                self._selected_target_ids[isin] = target_id
            self._draft = {
                CONF_PLAN_NAME: str(user_input[CONF_PLAN_NAME]).strip(),
                CONF_PLAN_BUDGET_AMOUNT: float(user_input[CONF_PLAN_BUDGET_AMOUNT]),
                CONF_PLAN_BUDGET_BASIS: user_input[CONF_PLAN_BUDGET_BASIS],
                CONF_PLAN_FREQUENCY: user_input[CONF_PLAN_FREQUENCY],
                CONF_PLAN_SCHEDULE_ENABLED: bool(
                    user_input[CONF_PLAN_SCHEDULE_ENABLED]
                ),
            }
            self._draft_instruments = []
            self._instrument_index = 0
            if self._draft[CONF_PLAN_SCHEDULE_ENABLED]:
                return await self.async_step_schedule()
            self._draft[CONF_PLAN_EXECUTION_DAYS] = []
            self._draft.pop(CONF_PLAN_EXECUTION_MONTH, None)
            self._draft.pop(CONF_PLAN_EXECUTION_MONTH_OFFSET, None)
            return await self.async_step_plan_instrument()

        return self.async_show_form(
            step_id="plan",
            data_schema=self.add_suggested_values_to_schema(
                _plan_schema(context), suggested
            ),
        )

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure frequency-specific recurring execution dates."""
        frequency = self._draft[CONF_PLAN_FREQUENCY]
        options = self.config_entry.options
        maximum_day = 7 if frequency == PLAN_FREQUENCY_WEEKLY else 28
        existing_days = _safe_execution_day_strings(
            options.get(CONF_PLAN_EXECUTION_DAYS), maximum=maximum_day
        )
        suggested: dict[str, Any] = {
            CONF_REVIEW_LEAD_DAYS: int(
                options.get(CONF_REVIEW_LEAD_DAYS, DEFAULT_REVIEW_LEAD_DAYS)
            ),
            CONF_PLAN_EXECUTION_DAYS: existing_days,
        }
        if frequency == PLAN_FREQUENCY_QUARTERLY:
            suggested[CONF_PLAN_EXECUTION_MONTH_OFFSET] = str(
                options.get(CONF_PLAN_EXECUTION_MONTH_OFFSET, 1)
            )
        elif frequency == PLAN_FREQUENCY_YEARLY:
            suggested[CONF_PLAN_EXECUTION_MONTH] = str(
                options.get(CONF_PLAN_EXECUTION_MONTH, 1)
            )

        errors: dict[str, str] = {}
        if user_input is not None:
            suggested.update(user_input)
            days = [int(value) for value in user_input[CONF_PLAN_EXECUTION_DAYS]]
            month = user_input.get(CONF_PLAN_EXECUTION_MONTH)
            offset = user_input.get(CONF_PLAN_EXECUTION_MONTH_OFFSET)
            try:
                schedule = validate_schedule_config(
                    frequency,
                    days,
                    execution_month=int(month) if month is not None else None,
                    execution_month_offset=int(offset) if offset is not None else None,
                )
            except (TypeError, ValueError):
                errors["base"] = "invalid_schedule"
            else:
                self._draft[CONF_REVIEW_LEAD_DAYS] = int(
                    user_input[CONF_REVIEW_LEAD_DAYS]
                )
                self._draft[CONF_PLAN_EXECUTION_DAYS] = list(
                    schedule.execution_days
                )
                if schedule.execution_month is not None:
                    self._draft[CONF_PLAN_EXECUTION_MONTH] = schedule.execution_month
                if schedule.execution_month_offset is not None:
                    self._draft[CONF_PLAN_EXECUTION_MONTH_OFFSET] = (
                        schedule.execution_month_offset
                    )
                return await self.async_step_plan_instrument()

        return self.async_show_form(
            step_id="schedule",
            data_schema=self.add_suggested_values_to_schema(
                _schedule_schema(frequency), suggested
            ),
            errors=errors,
        )

    async def async_step_plan_instrument(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure one selected instrument at a time."""
        context = await self._async_plan_context()
        by_isin = {item.isin: item for item in context.candidates}
        candidate = by_isin[self._selected_isins[self._instrument_index]]
        target_id = self._selected_target_ids[candidate.isin]
        suggested = {
            "target_pct": float(candidate.target_pct),
            "buy_enabled": candidate.buy_enabled,
        }
        if user_input is not None:
            suggested.update(user_input)
            target = Decimal(str(user_input["target_pct"]))
            if not target.is_finite() or target <= 0 or target > 100:
                return self.async_show_form(
                    step_id="plan_instrument",
                    data_schema=self.add_suggested_values_to_schema(
                        _instrument_schema(), suggested
                    ),
                    errors={"target_pct": "invalid_target"},
                    description_placeholders=_candidate_placeholders(candidate, target_id),
                )
            self._draft_instruments.append(
                {
                    "target_id": target_id,
                    "wkn": candidate.wkn,
                    "isin": candidate.isin,
                    "name": candidate.name,
                    "target_pct": float(target),
                    "buy_enabled": bool(user_input["buy_enabled"]),
                }
            )
            self._instrument_index += 1
            if self._instrument_index < len(self._selected_isins):
                return await self.async_step_plan_instrument()
            return await self._async_finish_plan()

        return self.async_show_form(
            step_id="plan_instrument",
            data_schema=self.add_suggested_values_to_schema(
                _instrument_schema(), suggested
            ),
            description_placeholders=_candidate_placeholders(candidate, target_id),
        )

    async def async_step_plan_review(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer explicit normalisation when entered targets do not sum to 100%."""
        total = sum(Decimal(str(item["target_pct"])) for item in self._draft_instruments)
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("normalise_targets"):
                errors["base"] = "targets_not_100"
            else:
                self._draft_instruments = _normalise_targets(
                    self._draft_instruments
                )
                return await self._async_commit_plan()
        return self.async_show_form(
            step_id="plan_review",
            data_schema=vol.Schema(
                {
                    vol.Required("normalise_targets", default=False): BooleanSelector(
                        BooleanSelectorConfig()
                    )
                }
            ),
            errors=errors,
            description_placeholders={
                "target_total": format(total.normalize(), "f"),
                "instrument_count": str(len(self._draft_instruments)),
            },
        )

    async def async_step_reset_plan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Restore the read-only plan definition from portfolio.yaml."""
        if not self.config_entry.options.get(CONF_PLAN_OVERRIDE_ENABLED):
            return self.async_abort(reason="plan_already_uses_yaml")
        if user_input is not None and user_input.get("confirm_reset"):
            options = dict(self.config_entry.options)
            for key in _PLAN_OVERRIDE_OPTION_KEYS:
                options.pop(key, None)
            return self.async_create_entry(data=options)
        return self.async_show_form(
            step_id="reset_plan",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm_reset", default=False): BooleanSelector(
                        BooleanSelectorConfig()
                    )
                }
            ),
        )

    async def async_step_runtime(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure explicit evidence-kind freshness thresholds."""
        options = dict(self.config_entry.options)
        legacy = int(options.get(CONF_FRESHNESS_HOURS, DEFAULT_FRESHNESS_HOURS))
        provider_keys = (
            CONF_FRESHNESS_LIVE_API_HOURS,
            CONF_FRESHNESS_STATEMENT_HOURS,
            CONF_FRESHNESS_CSV_HOURS,
            CONF_FRESHNESS_OTHER_HOURS,
        )
        provider_policy_configured = any(key in options for key in provider_keys)
        legacy_policy_configured = CONF_FRESHNESS_HOURS in options and not provider_policy_configured
        defaults = default_freshness_thresholds(
            str(options.get(CONF_PLAN_FREQUENCY, DEFAULT_PLAN_FREQUENCY)),
            legacy_threshold_hours=legacy,
            preserve_legacy_global=legacy_policy_configured,
        )
        suggested = {
            CONF_FRESHNESS_LIVE_API_HOURS: int(
                options.get(CONF_FRESHNESS_LIVE_API_HOURS, defaults["live_api"])
            ),
            CONF_FRESHNESS_STATEMENT_HOURS: int(
                options.get(CONF_FRESHNESS_STATEMENT_HOURS, defaults["imported_statement"])
            ),
            CONF_FRESHNESS_CSV_HOURS: int(
                options.get(CONF_FRESHNESS_CSV_HOURS, defaults["csv"])
            ),
            CONF_FRESHNESS_OTHER_HOURS: int(
                options.get(CONF_FRESHNESS_OTHER_HOURS, defaults["other"])
            ),
        }
        if user_input is not None:
            for key in (
                CONF_FRESHNESS_LIVE_API_HOURS,
                CONF_FRESHNESS_STATEMENT_HOURS,
                CONF_FRESHNESS_CSV_HOURS,
                CONF_FRESHNESS_OTHER_HOURS,
            ):
                options[key] = int(user_input[key])
            return self.async_create_entry(data=options)

        live_selector = NumberSelector(
            NumberSelectorConfig(
                min=MIN_FRESHNESS_HOURS,
                max=MAX_FRESHNESS_HOURS,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="h",
            )
        )
        document_selector = NumberSelector(
            NumberSelectorConfig(
                min=MIN_FRESHNESS_HOURS,
                max=MAX_DOCUMENT_FRESHNESS_HOURS,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="h",
            )
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_FRESHNESS_LIVE_API_HOURS): live_selector,
                vol.Required(CONF_FRESHNESS_STATEMENT_HOURS): document_selector,
                vol.Required(CONF_FRESHNESS_CSV_HOURS): document_selector,
                vol.Required(CONF_FRESHNESS_OTHER_HOURS): live_selector,
            }
        )
        return self.async_show_form(
            step_id="runtime",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
        )

    async def _async_finish_plan(self) -> ConfigFlowResult:
        total = sum(Decimal(str(item["target_pct"])) for item in self._draft_instruments)
        if total != Decimal("100"):
            return await self.async_step_plan_review()
        return await self._async_commit_plan()

    async def _async_commit_plan(self) -> ConfigFlowResult:
        options = dict(self.config_entry.options)
        executions = max(1, len(self._draft.get(CONF_PLAN_EXECUTION_DAYS, [])))
        plan_override = {
            "enabled": True,
            "name": self._draft[CONF_PLAN_NAME],
            "budget_amount_eur": self._draft[CONF_PLAN_BUDGET_AMOUNT],
            "budget_basis": self._draft[CONF_PLAN_BUDGET_BASIS],
            "frequency": self._draft[CONF_PLAN_FREQUENCY],
            "executions_per_period": executions,
            "instruments": self._draft_instruments,
        }
        try:
            if self.config_entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_REST_API:
                configuration = resolve_configuration_directory(
                    self.hass,
                    self.config_entry.data[CONF_CONFIG_DIRECTORY],
                    require_exists=True,
                )
                coordinator = self.config_entry.runtime_data
                positions = getattr(coordinator, "positions", None)
                generated_at = getattr(coordinator, "data_timestamp", None)
                if not isinstance(positions, dict) or not positions:
                    raise ValueError("REST source has no validated positions")
                if generated_at is None:
                    raise ValueError("REST source has no validated snapshot timestamp")
                payload = await self.hass.async_add_executor_job(
                    _calculate_positions_with_override,
                    dict(positions),
                    configuration.config_directory,
                    generated_at,
                    plan_override,
                    self.config_entry.data[CONF_REST_ENDPOINT_URL],
                )
            else:
                paths = resolve_local_source_paths(
                    self.hass,
                    self.config_entry.data[CONF_CSV_PATH],
                    self.config_entry.data[CONF_CONFIG_DIRECTORY],
                    require_exists=False,
                )
                payload = await self.hass.async_add_executor_job(
                    _calculate_with_override,
                    paths.csv_path,
                    paths.config_directory,
                    plan_override,
                    CsvSourceConfig.from_mapping(dict(self.config_entry.data)),
                )
            _validate_calculated_payload(payload)
        except (OSError, ValueError, PortfolioArchitectDataError, PortfolioSourcePathError):
            return self.async_abort(reason="invalid_plan")

        options.update(self._draft)
        options[CONF_PLAN_OVERRIDE_ENABLED] = True
        options[CONF_PLAN_INSTRUMENTS] = self._draft_instruments
        options.pop(CONF_PLAN_EXECUTION_DAY, None)
        if not self._draft[CONF_PLAN_SCHEDULE_ENABLED]:
            options.pop(CONF_REVIEW_LEAD_DAYS, None)
            options.pop(CONF_PLAN_EXECUTION_MONTH, None)
            options.pop(CONF_PLAN_EXECUTION_MONTH_OFFSET, None)
        return self.async_create_entry(data=options)

    async def _async_plan_context(self) -> PlanEditorContext:
        if self._context is not None:
            return self._context
        configured = self.config_entry.options.get(CONF_PLAN_INSTRUMENTS)
        configured_instruments = configured if isinstance(configured, list) else None
        if self.config_entry.data.get(CONF_SOURCE_TYPE) == SOURCE_TYPE_REST_API:
            configuration = resolve_configuration_directory(
                self.hass,
                self.config_entry.data[CONF_CONFIG_DIRECTORY],
                require_exists=True,
            )
            coordinator = self.config_entry.runtime_data
            positions = getattr(coordinator, "positions", None)
            if not isinstance(positions, dict) or not positions:
                raise ValueError("REST source has no validated positions")
            self._context = await self.hass.async_add_executor_job(
                load_plan_editor_context_from_positions,
                dict(positions),
                configuration.config_directory,
                configured_instruments,
            )
        else:
            paths = resolve_local_source_paths(
                self.hass,
                self.config_entry.data[CONF_CSV_PATH],
                self.config_entry.data[CONF_CONFIG_DIRECTORY],
                require_exists=False,
            )
            self._context = await self.hass.async_add_executor_job(
                load_plan_editor_context,
                paths.csv_path,
                paths.config_directory,
                configured_instruments,
                CsvSourceConfig.from_mapping(dict(self.config_entry.data)),
            )
        return self._context


def _provider_schema(providers: tuple[str, ...] = _SUPPORTED_SOURCE_PROVIDERS) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SOURCE_PROVIDER): SelectSelector(
                SelectSelectorConfig(
                    options=list(providers),
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="source_provider",
                )
            ),
            vol.Required(CONF_CONFIG_DIRECTORY): TextSelector(
                TextSelectorConfig(multiline=False)
            ),
        }
    )


def _csv_source_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_CSV_PATH): TextSelector(
                TextSelectorConfig(multiline=False)
            )
        }
    )



def _hassio_rest_source_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_CONFIG_DIRECTORY): TextSelector(
                TextSelectorConfig(multiline=False)
            ),
            vol.Required(CONF_REST_API_TOKEN): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD,
                    autocomplete="current-password",
                    multiline=False,
                )
            ),
        }
    )


def _rest_source_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_REST_ENDPOINT_URL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL, multiline=False)
            ),
            vol.Required(CONF_REST_API_TOKEN): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD,
                    autocomplete="current-password",
                    multiline=False,
                )
            ),
        }
    )


def _reauth_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_REST_API_TOKEN): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD,
                    autocomplete="current-password",
                    multiline=False,
                )
            )
        }
    )


def _generic_format_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_CSV_ENCODING): SelectSelector(
                SelectSelectorConfig(
                    options=list(CSV_ENCODINGS),
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="csv_encoding",
                )
            ),
            vol.Required(CONF_CSV_DELIMITER): SelectSelector(
                SelectSelectorConfig(
                    options=list(CSV_DELIMITERS),
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="csv_delimiter",
                )
            ),
            vol.Required(CONF_CSV_HEADER_ROW): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=MAX_GENERIC_HEADER_ROW,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_CSV_DECIMAL_FORMAT): SelectSelector(
                SelectSelectorConfig(
                    options=list(DECIMAL_FORMATS),
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="csv_decimal_format",
                )
            ),
        }
    )


def _generic_mapping_schema(headers: tuple[str, ...]) -> vol.Schema:
    required_options = list(headers)
    optional_options = [{"value": "", "label": "—"}] + [
        {"value": value, "label": value} for value in headers
    ]
    return vol.Schema(
        {
            vol.Required(CONF_CSV_COLUMN_IDENTIFIER): SelectSelector(
                SelectSelectorConfig(options=required_options, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_CSV_COLUMN_NAME): SelectSelector(
                SelectSelectorConfig(options=required_options, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_CSV_COLUMN_VALUE): SelectSelector(
                SelectSelectorConfig(options=required_options, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_CSV_COLUMN_ISIN, default=""): SelectSelector(
                SelectSelectorConfig(options=optional_options, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_CSV_COLUMN_TYPE, default=""): SelectSelector(
                SelectSelectorConfig(options=optional_options, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_CSV_COLUMN_CURRENCY, default=""): SelectSelector(
                SelectSelectorConfig(options=optional_options, mode=SelectSelectorMode.DROPDOWN)
            ),
        }
    )


def _mapping_suggestions(
    stored: dict[str, Any], headers: tuple[str, ...]
) -> dict[str, Any]:
    aliases = {value.casefold(): value for value in headers}

    def pick(key: str, candidates: tuple[str, ...], *, required: bool) -> str:
        existing = stored.get(key)
        if existing in headers:
            return str(existing)
        for candidate in candidates:
            match = aliases.get(candidate.casefold())
            if match is not None:
                return match
        return headers[0] if required else ""

    return {
        CONF_CSV_COLUMN_IDENTIFIER: pick(
            CONF_CSV_COLUMN_IDENTIFIER, ("WKN", "ISIN", "Identifier", "Symbol"), required=True
        ),
        CONF_CSV_COLUMN_NAME: pick(
            CONF_CSV_COLUMN_NAME, ("Bezeichnung", "Name", "Instrument", "Security"), required=True
        ),
        CONF_CSV_COLUMN_VALUE: pick(
            CONF_CSV_COLUMN_VALUE, ("Wert in EUR", "Market Value", "Value", "Amount"), required=True
        ),
        CONF_CSV_COLUMN_ISIN: pick(
            CONF_CSV_COLUMN_ISIN, ("ISIN",), required=False
        ),
        CONF_CSV_COLUMN_TYPE: pick(
            CONF_CSV_COLUMN_TYPE, ("Typ", "Type", "Asset Type"), required=False
        ),
        CONF_CSV_COLUMN_CURRENCY: pick(
            CONF_CSV_COLUMN_CURRENCY, ("Währung", "Currency", "CCY"), required=False
        ),
    }



def _plan_schema(context: PlanEditorContext) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_PLAN_NAME): TextSelector(
                TextSelectorConfig(multiline=False)
            ),
            vol.Required(CONF_PLAN_BUDGET_AMOUNT): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_PLAN_BUDGET_EUR,
                    max=MAX_PLAN_BUDGET_EUR,
                    step=0.01,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="EUR",
                )
            ),
            vol.Required(CONF_PLAN_BUDGET_BASIS): SelectSelector(
                SelectSelectorConfig(
                    options=list(PLAN_BUDGET_BASES),
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="plan_budget_basis",
                )
            ),
            vol.Required(CONF_PLAN_FREQUENCY): SelectSelector(
                SelectSelectorConfig(
                    options=list(PLAN_FREQUENCIES),
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="plan_frequency",
                )
            ),
            vol.Required(CONF_PLAN_SCHEDULE_ENABLED): BooleanSelector(
                BooleanSelectorConfig()
            ),
            vol.Required("selected_instruments"): SelectSelector(
                SelectSelectorConfig(
                    options=[item.to_option() for item in context.candidates],
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        }
    )


def _execution_policy_schema() -> vol.Schema:
    """Return a conservative schema using only core Voluptuous primitives."""
    return vol.Schema(
        {
            vol.Required(CONF_EXECUTION_COST_AWARE_ENABLED): bool,
            vol.Required(CONF_EXECUTION_POLICY): vol.In(EXECUTION_POLICIES),
            vol.Required(CONF_EXECUTION_MAX_COST_RATIO_PCT): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=25)
            ),
            vol.Required(CONF_EXECUTION_MAX_DEFERRAL_PERIODS): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=24)
            ),
            vol.Required(CONF_EXECUTION_MAX_ORDERS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=8)
            ),
            vol.Required(CONF_EXECUTION_RESERVE_MODE): vol.In(
                EXECUTION_RESERVE_MODES
            ),
        }
    )


def _execution_fees_schema() -> vol.Schema:
    """Return the manual-order fee form without selector-specific precision."""

    def amount(maximum: float = 100000) -> vol.All:
        return vol.All(vol.Coerce(float), vol.Range(min=0, max=maximum))

    return vol.Schema(
        {
            vol.Required(CONF_MANUAL_COMMISSION_BASE_EUR): amount(),
            vol.Required(CONF_MANUAL_COMMISSION_PCT): amount(10),
            vol.Required(CONF_MANUAL_COMMISSION_MIN_EUR): amount(),
            vol.Required(CONF_MANUAL_COMMISSION_MAX_EUR): amount(),
            vol.Required(CONF_MANUAL_VENUE_FEE_BPS): amount(1000),
            vol.Required(CONF_MANUAL_VENUE_FEE_MIN_EUR): amount(),
            vol.Required(CONF_MANUAL_SETTLEMENT_FEE_EUR): amount(),
        }
    )


def _broker_settings_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_BROKER_FEE_DATA_MAX_AGE_DAYS): NumberSelector(
                NumberSelectorConfig(min=1, max=366, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="d")
            )
        }
    )


def _broker_provider_select_options(document: dict[str, Any]) -> list[dict[str, str]]:
    providers = document.get("providers", {})
    if not isinstance(providers, dict):
        return []
    return [
        {"value": provider_id, "label": str(raw.get("name") or provider_id)}
        for provider_id, raw in sorted(providers.items())
        if isinstance(provider_id, str) and isinstance(raw, dict)
    ]


def _broker_provider_select_schema(options: list[dict[str, str]]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_BROKER_PROVIDER_ID): SelectSelector(
                SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
            )
        }
    )


def _broker_provider_schema(*, include_id: bool) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if include_id:
        fields[vol.Required(CONF_BROKER_PROVIDER_ID)] = TextSelector(TextSelectorConfig(multiline=False))
    fields.update(
        {
            vol.Required(CONF_BROKER_PROVIDER_NAME): TextSelector(TextSelectorConfig(multiline=False)),
            vol.Required(CONF_BROKER_PROVIDER_SOURCE): TextSelector(TextSelectorConfig(multiline=False)),
            vol.Required(CONF_BROKER_PROVIDER_AS_OF): DateSelector(DateSelectorConfig()),
            vol.Required(CONF_BROKER_TIE_BREAK): SelectSelector(
                SelectSelectorConfig(
                    options=[TIE_BREAK_PREFERRED, TIE_BREAK_NEUTRAL, TIE_BREAK_FALLBACK],
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="tie_break_preference",
                )
            ),
        }
    )
    return vol.Schema(fields)


def _broker_savings_route_options(document: dict[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    providers = document.get("providers", {})
    if not isinstance(providers, dict):
        return result
    for provider_id, provider in sorted(providers.items()):
        plans = provider.get("savings_plans", {}) if isinstance(provider, dict) else {}
        if not isinstance(plans, dict):
            continue
        provider_name = str(provider.get("name") or provider_id)
        for isin in sorted(plans):
            result.append({"value": f"{provider_id}|{isin}", "label": f"{provider_name} · {isin}"})
    return result


def _broker_route_select_schema(options: list[dict[str, str]]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_BROKER_SAVINGS_ROUTE): SelectSelector(
                SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
            )
        }
    )


def _broker_savings_plan_schema(
    providers: list[dict[str, str]], *, include_identity: bool
) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if include_identity:
        fields[vol.Required(CONF_BROKER_PROVIDER_ID)] = SelectSelector(
            SelectSelectorConfig(options=providers, mode=SelectSelectorMode.DROPDOWN)
        )
        fields[vol.Required(CONF_BROKER_ISIN)] = TextSelector(TextSelectorConfig(multiline=False))
    fields.update(
        {
            vol.Required(CONF_BROKER_AVAILABLE): BooleanSelector(BooleanSelectorConfig()),
            vol.Required(CONF_BROKER_FEE_PCT): NumberSelector(
                NumberSelectorConfig(min=0, max=25, step=0.001, mode=NumberSelectorMode.BOX, unit_of_measurement="%")
            ),
            vol.Required(CONF_BROKER_PROMOTIONAL): BooleanSelector(BooleanSelectorConfig()),
            vol.Optional(CONF_BROKER_STATUS, default=""): TextSelector(TextSelectorConfig(multiline=False)),
            vol.Required(CONF_BROKER_ROUTE_SOURCE): TextSelector(TextSelectorConfig(multiline=False)),
            vol.Required(CONF_BROKER_ROUTE_AS_OF): DateSelector(DateSelectorConfig()),
        }
    )
    return vol.Schema(fields)


def _broker_funding_schema(
    providers: list[dict[str, str]], *, include_identity: bool = True
) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if include_identity:
        fields.update(
            {
                vol.Required(CONF_BROKER_FROM_PROVIDER): SelectSelector(
                    SelectSelectorConfig(options=providers, mode=SelectSelectorMode.DROPDOWN)
                ),
                vol.Required(CONF_BROKER_TO_PROVIDER): SelectSelector(
                    SelectSelectorConfig(options=providers, mode=SelectSelectorMode.DROPDOWN)
                ),
            }
        )
    fields.update(
        {
            vol.Required(CONF_BROKER_TRANSFER_FEE_EUR): NumberSelector(
                NumberSelectorConfig(min=0, max=10000, step=0.01, mode=NumberSelectorMode.BOX, unit_of_measurement="EUR")
            ),
            vol.Required(CONF_BROKER_SETTLEMENT_DAYS): NumberSelector(
                NumberSelectorConfig(min=0, max=30, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="d")
            ),
            vol.Required(CONF_BROKER_TRANSFER_SOURCE): TextSelector(
                TextSelectorConfig(multiline=False)
            ),
            vol.Required(CONF_BROKER_TRANSFER_AS_OF): DateSelector(DateSelectorConfig()),
        }
    )
    return vol.Schema(fields)


def _broker_funding_edge_options(document: dict[str, Any]) -> list[dict[str, str]]:
    providers = document.get("providers", {})
    names = {
        key: str(value.get("name") or key)
        for key, value in providers.items()
        if isinstance(providers, dict) and isinstance(value, dict)
    } if isinstance(providers, dict) else {}
    edges = document.get("funding_transfers", []) if document.get("schema_version") == 3 else []
    if not isinstance(edges, list):
        return []
    result: list[dict[str, str]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("from_provider")
        destination = edge.get("to_provider")
        if not isinstance(source, str) or not isinstance(destination, str):
            continue
        result.append(
            {
                "value": f"{source}|{destination}",
                "label": f"{names.get(source, source)} → {names.get(destination, destination)}",
            }
        )
    return sorted(result, key=lambda item: item["label"])


def _broker_funding_edge_select_schema(options: list[dict[str, str]]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_BROKER_FUNDING_EDGE): SelectSelector(
                SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
            )
        }
    )


def _schedule_schema(frequency: str) -> vol.Schema:
    fields: dict[Any, Any] = {
        vol.Required(CONF_REVIEW_LEAD_DAYS): NumberSelector(
            NumberSelectorConfig(
                min=MIN_REVIEW_LEAD_DAYS,
                max=MAX_REVIEW_LEAD_DAYS,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="d",
            )
        )
    }
    if frequency == PLAN_FREQUENCY_WEEKLY:
        fields[vol.Required(CONF_PLAN_EXECUTION_DAYS)] = SelectSelector(
            SelectSelectorConfig(
                options=[str(value) for value in range(1, 8)],
                multiple=True,
                mode=SelectSelectorMode.LIST,
                translation_key="weekdays",
            )
        )
    else:
        fields[vol.Required(CONF_PLAN_EXECUTION_DAYS)] = SelectSelector(
            SelectSelectorConfig(
                options=[str(value) for value in range(1, 29)],
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
    if frequency == PLAN_FREQUENCY_QUARTERLY:
        fields[vol.Required(CONF_PLAN_EXECUTION_MONTH_OFFSET)] = SelectSelector(
            SelectSelectorConfig(
                options=[str(value) for value in range(
                    MIN_EXECUTION_MONTH_OFFSET, MAX_EXECUTION_MONTH_OFFSET + 1
                )],
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="quarter_month",
            )
        )
    if frequency == PLAN_FREQUENCY_YEARLY:
        fields[vol.Required(CONF_PLAN_EXECUTION_MONTH)] = SelectSelector(
            SelectSelectorConfig(
                options=[str(value) for value in range(
                    MIN_EXECUTION_MONTH, MAX_EXECUTION_MONTH + 1
                )],
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="months",
            )
        )
    return vol.Schema(fields)


def _safe_execution_day_strings(value: object, *, maximum: int) -> list[str]:
    """Return distinct stored day values that remain valid for the new cadence."""
    if not isinstance(value, list):
        return []
    result: set[int] = set()
    for raw in value:
        if isinstance(raw, bool):
            continue
        try:
            day = int(raw)
        except (TypeError, ValueError):
            continue
        if 1 <= day <= maximum:
            result.add(day)
    return [str(day) for day in sorted(result)]


def _instrument_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("target_pct"): NumberSelector(
                NumberSelectorConfig(
                    min=0.01,
                    max=100,
                    step=0.01,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="%",
                )
            ),
            vol.Required("buy_enabled"): BooleanSelector(BooleanSelectorConfig()),
        }
    )


def _candidate_placeholders(candidate: PlanCandidate, target_id: str) -> dict[str, str]:
    return {
        "instrument_name": candidate.name,
        "isin": candidate.isin,
        "wkn": candidate.wkn or "—",
        "target_id": target_id,
    }


def _normalise_targets(instruments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Scale positive targets to exactly 100.00% without creating zero weights."""
    total = sum(Decimal(str(item["target_pct"])) for item in instruments)
    if total <= 0:
        raise ValueError("target total must be positive")
    if len(instruments) > 10_000:
        raise ValueError("too many targets to normalise")

    raw_basis_points = [
        Decimal(str(item["target_pct"])) / total * Decimal("10000")
        for item in instruments
    ]
    allocated = [
        max(1, int(value.to_integral_value(rounding=ROUND_FLOOR)))
        for value in raw_basis_points
    ]

    difference = 10_000 - sum(allocated)
    if difference > 0:
        order = sorted(
            range(len(instruments)),
            key=lambda index: (
                raw_basis_points[index] - int(raw_basis_points[index]),
                raw_basis_points[index],
                -index,
            ),
            reverse=True,
        )
        for offset in range(difference):
            allocated[order[offset % len(order)]] += 1
    elif difference < 0:
        remaining = -difference
        order = sorted(
            range(len(instruments)),
            key=lambda index: (allocated[index], raw_basis_points[index], -index),
            reverse=True,
        )
        for index in order:
            removable = min(allocated[index] - 1, remaining)
            allocated[index] -= removable
            remaining -= removable
            if remaining == 0:
                break
        if remaining:
            raise ValueError("targets cannot be normalised safely")

    result: list[dict[str, Any]] = []
    for item, basis_points in zip(instruments, allocated, strict=True):
        clone = dict(item)
        clone["target_pct"] = float(Decimal(basis_points) / Decimal("100"))
        result.append(clone)
    return result


def _calculate_with_override(csv_path, config_directory, plan_override, source_config):
    return calculate_portfolio_payload(
        csv_path,
        config_directory,
        plan_override=plan_override,
        source_config=source_config,
    )


def _calculate_source_payload(csv_path, config_directory, source_config):
    return calculate_portfolio_payload(
        csv_path, config_directory, source_config=source_config
    )


def _calculate_positions_with_override(
    positions,
    config_directory,
    generated_at,
    plan_override,
    endpoint_url,
):
    from urllib.parse import urlsplit

    parsed = urlsplit(endpoint_url)
    source_label = f"{parsed.hostname or 'local-rest'}{parsed.path or '/'}"[:255]
    return calculate_portfolio_payload_from_positions(
        positions,
        config_directory,
        evaluated_at=generated_at,
        plan_override=plan_override,
        source_provider=PROVIDER_LOCAL_REST_JSON,
        source_label=source_label,
    )


def _calculate_rest_source_payload(
    positions,
    config_directory,
    generated_at,
    endpoint_url,
):
    from urllib.parse import urlsplit

    parsed = urlsplit(endpoint_url)
    source_label = f"{parsed.hostname or 'local-rest'}{parsed.path or '/'}"[:255]
    return calculate_portfolio_payload_from_positions(
        positions,
        config_directory,
        evaluated_at=generated_at,
        source_provider=PROVIDER_LOCAL_REST_JSON,
        source_label=source_label,
    )


def _validate_calculated_payload(payload: dict[str, Any]) -> None:
    parse_portfolio_data(
        payload.get("recommendations"),
        payload.get("summary"),
        payload.get("policy_findings"),
        holdings=payload.get("holdings"),
    )
