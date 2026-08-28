"""Constants for the Portfolio Architect integration."""

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "portfolio_architect"
INSTANCE_UNIQUE_ID: Final = "portfolio_architect"
NAME: Final = "Portfolio Architect"
VERSION: Final = "1.55.0"

CONF_SOURCE_TYPE: Final = "source_type"

CONF_SOURCE_PROVIDER: Final = "source_provider"
CONF_CSV_ENCODING: Final = "csv_encoding"
CONF_CSV_DELIMITER: Final = "csv_delimiter"
CONF_CSV_HEADER_ROW: Final = "csv_header_row"
CONF_CSV_DECIMAL_FORMAT: Final = "csv_decimal_format"
CONF_CSV_COLUMN_IDENTIFIER: Final = "csv_column_identifier"
CONF_CSV_COLUMN_NAME: Final = "csv_column_name"
CONF_CSV_COLUMN_VALUE: Final = "csv_column_value"
CONF_CSV_COLUMN_ISIN: Final = "csv_column_isin"
CONF_CSV_COLUMN_TYPE: Final = "csv_column_type"
CONF_CSV_COLUMN_CURRENCY: Final = "csv_column_currency"
CONF_CSV_PATH: Final = "csv_path"
CONF_REST_ENDPOINT_URL: Final = "rest_endpoint_url"
CONF_REST_API_TOKEN: Final = "rest_api_token"
CONF_REST_TLS_CA_CERTIFICATE: Final = "rest_tls_ca_certificate"
CONF_CONFIG_DIRECTORY: Final = "config_directory"
CONF_SOURCE_ENTITY_ID: Final = "source_entity_id"  # v1.0 compatibility only
CONF_FRESHNESS_HOURS: Final = "freshness_hours"  # pre-v1.33 compatibility fallback
CONF_FRESHNESS_LIVE_API_HOURS: Final = "freshness_live_api_hours"
CONF_FRESHNESS_STATEMENT_HOURS: Final = "freshness_statement_hours"
CONF_FRESHNESS_CSV_HOURS: Final = "freshness_csv_hours"
CONF_FRESHNESS_OTHER_HOURS: Final = "freshness_other_hours"
CONF_PLAN_EXECUTION_DAY: Final = "plan_execution_day"  # v1.0-v1.1 migration only
CONF_REVIEW_LEAD_DAYS: Final = "review_lead_days"
CONF_SUPPLEMENTAL_REST_SOURCES: Final = "supplemental_rest_sources"

CONF_PLAN_OVERRIDE_ENABLED: Final = "plan_override_enabled"
CONF_PLAN_NAME: Final = "plan_name"
CONF_PLAN_BUDGET_AMOUNT: Final = "plan_budget_amount"
CONF_PLAN_BUDGET_BASIS: Final = "plan_budget_basis"
CONF_PLAN_FREQUENCY: Final = "plan_frequency"
CONF_PLAN_SCHEDULE_ENABLED: Final = "plan_schedule_enabled"
CONF_PLAN_EXECUTION_DAYS: Final = "plan_execution_days"
CONF_PLAN_EXECUTION_MONTH: Final = "plan_execution_month"
CONF_PLAN_EXECUTION_MONTH_OFFSET: Final = "plan_execution_month_offset"
CONF_PLAN_INSTRUMENTS: Final = "plan_instruments"
CONF_EXECUTION_COST_AWARE_ENABLED: Final = "execution_cost_aware_enabled"
CONF_EXECUTION_POLICY: Final = "execution_policy"
CONF_EXECUTION_MAX_COST_RATIO_PCT: Final = "execution_max_cost_ratio_pct"
CONF_EXECUTION_MAX_DEFERRAL_PERIODS: Final = "execution_max_deferral_periods"
CONF_EXECUTION_MAX_ORDERS: Final = "execution_max_orders"
CONF_EXECUTION_RESERVE_MODE: Final = "execution_reserve_mode"
CONF_MANUAL_COMMISSION_BASE_EUR: Final = "manual_commission_base_eur"
CONF_MANUAL_COMMISSION_PCT: Final = "manual_commission_pct"
CONF_MANUAL_COMMISSION_MIN_EUR: Final = "manual_commission_min_eur"
CONF_MANUAL_COMMISSION_MAX_EUR: Final = "manual_commission_max_eur"
CONF_MANUAL_VENUE_FEE_PCT: Final = "manual_venue_fee_pct"
CONF_MANUAL_VENUE_FEE_MIN_EUR: Final = "manual_venue_fee_min_eur"
CONF_MANUAL_SETTLEMENT_FEE_EUR: Final = "manual_settlement_fee_eur"

EXECUTION_POLICIES: Final = ("monthly_continuity", "balanced", "efficiency_first")
EXECUTION_RESERVE_MODES: Final = ("contribution_only", "gateway_balance")

SOURCE_TYPE_LOCAL_FILES: Final = "local_files"
SOURCE_TYPE_REST_API: Final = "rest_api"
SOURCE_TYPE_LEGACY_SENSOR: Final = "legacy_sensor"
DEFAULT_CSV_PATH: Final = "portfolio/depot.csv"
DEFAULT_REST_ENDPOINT_URL: Final = "https://local-portfolio-architect-gateway:8787/api/v1/portfolio"
LEGACY_COMDIRECT_CSV_PROVIDER: Final = "comdirect_csv"
DEFAULT_SOURCE_PROVIDER: Final = "local_rest_json"
DEFAULT_CONFIG_DIRECTORY: Final = "portfolio-architect"
DEFAULT_SOURCE_ENTITY_ID: Final = "sensor.portfolio_architect"
DEFAULT_FRESHNESS_HOURS: Final = 24
MIN_FRESHNESS_HOURS: Final = 1
MAX_FRESHNESS_HOURS: Final = 168
MAX_DOCUMENT_FRESHNESS_HOURS: Final = 31 * 24
DEFAULT_REVIEW_LEAD_DAYS: Final = 2
MIN_REVIEW_LEAD_DAYS: Final = 1
MAX_REVIEW_LEAD_DAYS: Final = 7
MIN_PLAN_EXECUTION_DAY: Final = 1
MAX_PLAN_EXECUTION_DAY: Final = 28
DEFAULT_UPDATE_INTERVAL_MINUTES: Final = 15
DEFAULT_HOME_ASSISTANT_LKG_MAX_AGE_SECONDS: Final = 7 * 24 * 60 * 60
MAX_SUPPLEMENTAL_SOURCES: Final = 8
MAX_SUPPLEMENTAL_REST_SOURCES: Final = 4

PLAN_BUDGET_BASIS_PERIOD: Final = "per_period"
PLAN_BUDGET_BASIS_EXECUTION: Final = "per_execution"
PLAN_BUDGET_BASES: Final = (
    PLAN_BUDGET_BASIS_PERIOD,
    PLAN_BUDGET_BASIS_EXECUTION,
)
PLAN_FREQUENCY_WEEKLY: Final = "weekly"
PLAN_FREQUENCY_MONTHLY: Final = "monthly"
PLAN_FREQUENCY_QUARTERLY: Final = "quarterly"
PLAN_FREQUENCY_YEARLY: Final = "yearly"
PLAN_FREQUENCIES: Final = (
    PLAN_FREQUENCY_WEEKLY,
    PLAN_FREQUENCY_MONTHLY,
    PLAN_FREQUENCY_QUARTERLY,
    PLAN_FREQUENCY_YEARLY,
)
DEFAULT_PLAN_FREQUENCY: Final = PLAN_FREQUENCY_MONTHLY
DEFAULT_PLAN_BUDGET_BASIS: Final = PLAN_BUDGET_BASIS_PERIOD
MIN_PLAN_BUDGET_EUR: Final = 0.01
MAX_PLAN_BUDGET_EUR: Final = 10_000_000.0
MAX_PLAN_INSTRUMENTS: Final = 32
MIN_EXECUTION_MONTH: Final = 1
MAX_EXECUTION_MONTH: Final = 12
MIN_EXECUTION_MONTH_OFFSET: Final = 1
MAX_EXECUTION_MONTH_OFFSET: Final = 3
MIN_WEEKDAY: Final = 1
MAX_WEEKDAY: Final = 7

ATTR_RECOMMENDATIONS: Final = "recommendations"
ATTR_HOLDINGS: Final = "holdings"
ATTR_SUMMARY: Final = "summary"
ATTR_POLICY_FINDINGS: Final = "policy_findings"
PLATFORMS: Final = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.DATE]

ALLOCATION_KINDS: Final = ("current", "target")
