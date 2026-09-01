"""Cost-aware execution-route modelling for long-term investment plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any, Final

from .funding import funding_transfers, transfer_for

D = Decimal

POLICY_MONTHLY_CONTINUITY: Final = "monthly_continuity"
POLICY_BALANCED: Final = "balanced"
POLICY_EFFICIENCY_FIRST: Final = "efficiency_first"
EXECUTION_POLICIES: Final = {
    POLICY_MONTHLY_CONTINUITY,
    POLICY_BALANCED,
    POLICY_EFFICIENCY_FIRST,
}

ROUTE_FREE_SAVINGS_PLAN: Final = "free_savings_plan"
ROUTE_PAID_SAVINGS_PLAN: Final = "paid_savings_plan"
ROUTE_MANUAL_ORDER: Final = "manual_order"
ROUTE_UNAVAILABLE: Final = "unavailable"

_PROVIDER_ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")
_MAX_PROVIDER_NAME = 80
_MAX_PROVIDER_SOURCE = 160
_MAX_PROVIDERS = 16
_MAX_SAVINGS_PLANS = 256


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Validated execution-policy settings.

    The manual fee fields remain the legacy single-broker profile used by
    ``broker.yaml`` schema 1. Provider-aware schema 2 keeps manual-order fees
    with the individual provider instead.
    """

    enabled: bool = False
    policy: str = POLICY_MONTHLY_CONTINUITY
    max_cost_ratio_pct: Decimal = D("1.50")
    max_deferral_periods: int = 3
    max_orders_per_execution: int = 1
    reserve_mode: str = "contribution_only"
    manual_commission_base_eur: Decimal = D("4.90")
    manual_commission_pct: Decimal = D("0.25")
    manual_commission_min_eur: Decimal = D("9.90")
    manual_commission_max_eur: Decimal = D("59.90")
    manual_venue_fee_pct: Decimal = D("0.0025")
    manual_venue_fee_min_eur: Decimal = D("2.50")
    manual_settlement_fee_eur: Decimal = D("2.90")

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> "ExecutionConfig":
        if not raw:
            return cls()
        enabled = raw.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("execution.enabled must be boolean")
        policy = str(raw.get("policy", POLICY_MONTHLY_CONTINUITY))
        if policy not in EXECUTION_POLICIES:
            raise ValueError("execution.policy is invalid")
        reserve_mode = str(raw.get("reserve_mode", "contribution_only"))
        if reserve_mode not in {"contribution_only", "gateway_balance"}:
            raise ValueError("execution.reserve_mode is invalid")

        def money(key: str, default: str, *, maximum: str = "100000") -> Decimal:
            value = D(str(raw.get(key, default)))
            if not value.is_finite() or value < 0 or value > D(maximum):
                raise ValueError(f"execution.{key} is invalid")
            return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)

        def percentage(key: str, default: str, *, maximum: str = "100") -> Decimal:
            value = D(str(raw.get(key, default)))
            if not value.is_finite() or value < 0 or value > D(maximum):
                raise ValueError(f"execution.{key} is invalid")
            return value.quantize(D("0.0001"), rounding=ROUND_HALF_UP)

        def integer(key: str, default: int, *, minimum: int, maximum: int) -> int:
            value = raw.get(key, default)
            if isinstance(value, bool):
                raise ValueError(f"execution.{key} is invalid")
            try:
                parsed = int(value)
            except (TypeError, ValueError) as err:
                raise ValueError(f"execution.{key} is invalid") from err
            if not minimum <= parsed <= maximum:
                raise ValueError(f"execution.{key} is invalid")
            return parsed

        result = cls(
            enabled=enabled,
            policy=policy,
            max_cost_ratio_pct=percentage("max_cost_ratio_pct", "1.50", maximum="25"),
            max_deferral_periods=integer("max_deferral_periods", 3, minimum=0, maximum=24),
            max_orders_per_execution=integer("max_orders_per_execution", 1, minimum=1, maximum=8),
            reserve_mode=reserve_mode,
            manual_commission_base_eur=money("manual_commission_base_eur", "4.90"),
            manual_commission_pct=percentage("manual_commission_pct", "0.25", maximum="10"),
            manual_commission_min_eur=money("manual_commission_min_eur", "9.90"),
            manual_commission_max_eur=money("manual_commission_max_eur", "59.90"),
            manual_venue_fee_pct=percentage("manual_venue_fee_pct", "0.0025", maximum="10"),
            manual_venue_fee_min_eur=money("manual_venue_fee_min_eur", "2.50"),
            manual_settlement_fee_eur=money("manual_settlement_fee_eur", "2.90"),
        )
        if result.manual_commission_max_eur < result.manual_commission_min_eur:
            raise ValueError("execution manual commission maximum is below its minimum")
        return result


@dataclass(frozen=True, slots=True)
class ManualFeeProfile:
    """Provider-local manual-order fee formula."""

    commission_base_eur: Decimal
    commission_pct: Decimal
    commission_min_eur: Decimal
    commission_max_eur: Decimal
    venue_fee_pct: Decimal
    venue_fee_min_eur: Decimal
    settlement_fee_eur: Decimal

    @classmethod
    def from_execution_config(cls, config: ExecutionConfig) -> "ManualFeeProfile":
        return cls(
            commission_base_eur=config.manual_commission_base_eur,
            commission_pct=config.manual_commission_pct,
            commission_min_eur=config.manual_commission_min_eur,
            commission_max_eur=config.manual_commission_max_eur,
            venue_fee_pct=config.manual_venue_fee_pct,
            venue_fee_min_eur=config.manual_venue_fee_min_eur,
            settlement_fee_eur=config.manual_settlement_fee_eur,
        )

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "ManualFeeProfile":
        if not isinstance(raw, dict) or raw.get("available") is not True:
            raise ValueError("provider manual_order must be available to define a fee profile")

        def money(key: str, default: str = "0") -> Decimal:
            value = D(str(raw.get(key, default)))
            if not value.is_finite() or value < 0 or value > D("100000"):
                raise ValueError(f"provider manual_order.{key} is invalid")
            return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)

        def percentage(key: str, default: str = "0") -> Decimal:
            value = D(str(raw.get(key, default)))
            if not value.is_finite() or value < 0 or value > D("25"):
                raise ValueError(f"provider manual_order.{key} is invalid")
            return value.quantize(D("0.0001"), rounding=ROUND_HALF_UP)

        result = cls(
            commission_base_eur=money("commission_base_eur"),
            commission_pct=percentage("commission_pct"),
            commission_min_eur=money("commission_min_eur"),
            commission_max_eur=money("commission_max_eur", "100000"),
            venue_fee_pct=percentage("venue_fee_pct"),
            venue_fee_min_eur=money("venue_fee_min_eur"),
            settlement_fee_eur=money("settlement_fee_eur"),
        )
        if result.commission_max_eur < result.commission_min_eur:
            raise ValueError("provider manual-order commission maximum is below its minimum")
        return result


@dataclass(frozen=True, slots=True)
class ExecutionProvider:
    """One bounded provider fee-data record."""

    provider_id: str
    name: str
    priority: int
    as_of: date | None
    source: str | None
    fresh: bool
    savings_plans: dict[str, dict[str, Any]]
    manual_profile: ManualFeeProfile | None
    legacy: bool = False


@dataclass(frozen=True, slots=True)
class SavingsPlanRoute:
    """Validated savings-plan evidence for one provider/instrument."""

    provider_id: str
    provider_name: str
    priority: int
    fee_pct: Decimal
    as_of: date | None
    source: str | None


@dataclass(frozen=True, slots=True)
class RouteEstimate:
    route: str
    order_amount_eur: Decimal
    fee_eur: Decimal
    cash_outlay_eur: Decimal
    cost_ratio_pct: Decimal
    provider_id: str | None = None
    provider_name: str | None = None
    fee_data_as_of: str | None = None
    provider_priority: int = 100
    funding_provider_id: str | None = None
    funding_provider_name: str | None = None
    funding_transfer_required: bool = False
    funding_transfer_fee_eur: Decimal = D("0")
    funding_transfer_business_days: int = 0


def _bounded_text(value: Any, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    token = value.strip()
    if not token or len(token) > maximum or any(ord(char) < 32 for char in token):
        raise ValueError(f"{field} is invalid")
    return token


def _provider_priority(value: Any) -> int:
    if value is None:
        return 100
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("provider priority is invalid")
    parsed = value
    if not 0 <= parsed <= 10000:
        raise ValueError("provider priority is invalid")
    return parsed


def _validate_savings_plans(
    raw: Any,
    *,
    provider_id: str,
    evaluated_on: date | None = None,
    max_age_days: int | None = None,
    provider_source: str | None = None,
    provider_as_of: date | None = None,
    provider_fresh: bool = True,
) -> dict[str, dict[str, Any]]:
    """Validate route profiles and normalize their effective evidence.

    Route-level ``source`` + ``as_of`` is optional for compatibility. When the
    pair is absent, the route inherits the provider-level evidence exactly as
    schemas 2/3 did before v1.43. When present, route freshness is evaluated
    independently with the same broker fee-data age window.
    """

    if raw is None:
        return {}
    if not isinstance(raw, dict) or len(raw) > _MAX_SAVINGS_PLANS:
        raise ValueError(f"provider {provider_id} savings_plans is invalid")
    today = evaluated_on or date.today()
    result: dict[str, dict[str, Any]] = {}
    for isin, item in raw.items():
        if not isinstance(isin, str) or not 1 <= len(isin) <= 32 or not isinstance(item, dict):
            raise ValueError(f"provider {provider_id} savings-plan entry is invalid")
        available = item.get("available")
        if not isinstance(available, bool):
            raise ValueError(f"provider {provider_id} savings-plan availability is invalid")
        normalized = dict(item)
        if available:
            value = D(str(item.get("fee_pct")))
            if not value.is_finite() or value < 0 or value > D("25"):
                raise ValueError(f"provider {provider_id} savings-plan fee for {isin} is invalid")
            normalized["fee_pct"] = value.quantize(D("0.0001"), rounding=ROUND_HALF_UP)
        elif item.get("fee_pct") is not None:
            raise ValueError(f"provider {provider_id} unavailable savings plan must not declare a fee")
        promotional = item.get("promotional")
        if promotional is not None and not isinstance(promotional, bool):
            raise ValueError(
                f"provider {provider_id} savings-plan promotional flag for {isin} is invalid"
            )
        status = item.get("status")
        if status is not None:
            _bounded_text(status, field=f"provider {provider_id} savings-plan status", maximum=96)

        has_source = "source" in item
        has_as_of = "as_of" in item
        if has_source != has_as_of:
            raise ValueError(
                f"provider {provider_id} savings-plan evidence for {isin} is incomplete"
            )
        if has_source:
            if max_age_days is None:
                raise ValueError(
                    f"provider {provider_id} savings-plan evidence for {isin} requires provider-aware schema"
                )
            evidence_source = _bounded_text(
                item.get("source"),
                field=f"provider {provider_id} savings-plan source for {isin}",
                maximum=_MAX_PROVIDER_SOURCE,
            )
            try:
                evidence_as_of = date.fromisoformat(str(item.get("as_of")))
            except ValueError as err:
                raise ValueError(
                    f"provider {provider_id} savings-plan as_of for {isin} is invalid"
                ) from err
            if evidence_as_of > today:
                raise ValueError(
                    f"provider {provider_id} savings-plan as_of for {isin} is in the future"
                )
            evidence_fresh = (today - evidence_as_of).days <= max_age_days
            normalized["source"] = evidence_source
            normalized["as_of"] = evidence_as_of.isoformat()
        else:
            evidence_source = provider_source
            evidence_as_of = provider_as_of
            evidence_fresh = provider_fresh

        # Private normalized values are never serialized back to broker.yaml;
        # they keep route selection independent from provider-level freshness.
        normalized["_evidence_source"] = evidence_source
        normalized["_evidence_as_of"] = evidence_as_of
        normalized["_evidence_fresh"] = evidence_fresh
        result[isin] = normalized
    return result


def execution_providers(
    broker: dict[str, Any],
    *,
    evaluated_on: date | None = None,
) -> tuple[ExecutionProvider, ...]:
    """Return validated execution providers from broker schemas 1 through 3.

    Schema 1 remains a compatibility contract: its single broker is usable
    without freshness enforcement, exactly as before v1.30. Schemas 2 and 3 opt
    into provider-aware routing and require explicit provider provenance plus a
    bounded fee-data freshness window. Schema 3 additionally validates its full
    directed funding topology even if no current recommendation needs an edge.
    From v1.43, a savings-plan route may carry its own evidence pair and therefore
    remain fresh independently of stale provider-level fallback/manual-order evidence.
    """

    if not isinstance(broker, dict):
        raise ValueError("broker document must be an object")
    schema_version = broker.get("schema_version", 1)
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise ValueError("broker schema_version is invalid")
    if schema_version == 1:
        raw = broker.get("broker")
        if not isinstance(raw, dict):
            raise ValueError("broker schema 1 requires broker")
        provider_id = str(raw.get("id") or "legacy_broker")
        if not _PROVIDER_ID_RE.fullmatch(provider_id):
            raise ValueError("broker id is invalid")
        name = str(raw.get("name") or provider_id)
        name = _bounded_text(name, field="broker name", maximum=_MAX_PROVIDER_NAME)
        as_of: date | None = None
        if broker.get("as_of") is not None:
            try:
                as_of = date.fromisoformat(str(broker["as_of"]))
            except ValueError as err:
                raise ValueError("broker.as_of is invalid") from err
        plans = _validate_savings_plans(
            raw.get("savings_plans", {}),
            provider_id=provider_id,
            evaluated_on=evaluated_on,
            provider_as_of=as_of,
            provider_fresh=True,
        )
        return (
            ExecutionProvider(
                provider_id=provider_id,
                name=name,
                priority=0,
                as_of=as_of,
                source=None,
                fresh=True,
                savings_plans=plans,
                manual_profile=None,
                legacy=True,
            ),
        )

    if schema_version not in {2, 3}:
        raise ValueError("broker schema_version is unsupported")
    if schema_version == 3:
        # Validate the complete topology up front; an invalid unused edge must not
        # survive merely because today's allocation happens to use local cash.
        funding_transfers(broker, evaluated_on=evaluated_on)
    max_age = broker.get("fee_data_max_age_days")
    if isinstance(max_age, bool) or not isinstance(max_age, int):
        raise ValueError("broker fee_data_max_age_days is invalid")
    max_age_days = max_age
    if not 1 <= max_age_days <= 366:
        raise ValueError("broker fee_data_max_age_days is invalid")
    raw_providers = broker.get("providers")
    if not isinstance(raw_providers, dict) or len(raw_providers) > _MAX_PROVIDERS:
        raise ValueError(f"broker schema {schema_version} requires a bounded providers map")

    today = evaluated_on or date.today()
    result: list[ExecutionProvider] = []
    for provider_id, raw in raw_providers.items():
        if not isinstance(provider_id, str) or _PROVIDER_ID_RE.fullmatch(provider_id) is None:
            raise ValueError("provider id is invalid")
        if not isinstance(raw, dict):
            raise ValueError(f"provider {provider_id} must be an object")
        name = _bounded_text(
            raw.get("name"), field=f"provider {provider_id} name", maximum=_MAX_PROVIDER_NAME
        )
        source = _bounded_text(
            raw.get("source"), field=f"provider {provider_id} source", maximum=_MAX_PROVIDER_SOURCE
        )
        try:
            as_of = date.fromisoformat(str(raw.get("as_of")))
        except ValueError as err:
            raise ValueError(f"provider {provider_id} as_of is invalid") from err
        if as_of > today:
            raise ValueError(f"provider {provider_id} as_of is in the future")
        age_days = (today - as_of).days
        fresh = age_days <= max_age_days
        plans = _validate_savings_plans(
            raw.get("savings_plans", {}),
            provider_id=provider_id,
            evaluated_on=today,
            max_age_days=max_age_days,
            provider_source=source,
            provider_as_of=as_of,
            provider_fresh=fresh,
        )
        manual_raw = raw.get("manual_order")
        manual_profile: ManualFeeProfile | None = None
        if manual_raw is not None:
            if not isinstance(manual_raw, dict):
                raise ValueError(f"provider {provider_id} manual_order is invalid")
            available = manual_raw.get("available")
            if not isinstance(available, bool):
                raise ValueError(f"provider {provider_id} manual_order availability is invalid")
            if available:
                manual_profile = ManualFeeProfile.from_mapping(manual_raw)
        result.append(
            ExecutionProvider(
                provider_id=provider_id,
                name=name,
                priority=_provider_priority(raw.get("priority")),
                as_of=as_of,
                source=source,
                fresh=fresh,
                savings_plans=plans,
                manual_profile=manual_profile,
                legacy=False,
            )
        )
    return tuple(sorted(result, key=lambda item: (item.priority, item.provider_id)))


def savings_plan_routes(
    broker: dict[str, Any],
    isin: str,
    *,
    evaluated_on: date | None = None,
) -> tuple[SavingsPlanRoute, ...]:
    """Return fresh available savings-plan routes for an instrument."""

    routes: list[SavingsPlanRoute] = []
    for provider in execution_providers(broker, evaluated_on=evaluated_on):
        item = provider.savings_plans.get(isin)
        if (
            not isinstance(item, dict)
            or item.get("available") is not True
            or item.get("_evidence_fresh") is not True
        ):
            continue
        fee = item.get("fee_pct")
        if not isinstance(fee, Decimal):
            fee = D(str(fee))
        evidence_as_of = item.get("_evidence_as_of")
        if evidence_as_of is not None and not isinstance(evidence_as_of, date):
            raise ValueError(f"provider {provider.provider_id} savings-plan evidence is invalid")
        evidence_source = item.get("_evidence_source")
        if evidence_source is not None and not isinstance(evidence_source, str):
            raise ValueError(f"provider {provider.provider_id} savings-plan evidence is invalid")
        routes.append(
            SavingsPlanRoute(
                provider_id=provider.provider_id,
                provider_name=provider.name,
                priority=provider.priority,
                fee_pct=fee,
                as_of=evidence_as_of,
                source=evidence_source,
            )
        )
    return tuple(
        sorted(
            routes,
            key=lambda item: (
                item.fee_pct,
                item.priority,
                item.provider_id,
            ),
        )
    )


def preferred_savings_plan_route(
    broker: dict[str, Any],
    isin: str,
    *,
    evaluated_on: date | None = None,
) -> SavingsPlanRoute | None:
    routes = savings_plan_routes(broker, isin, evaluated_on=evaluated_on)
    return routes[0] if routes else None


def estimate_manual_order(
    amount: Decimal,
    config: ExecutionConfig | ManualFeeProfile,
    *,
    provider_id: str | None = None,
    provider_name: str | None = None,
    fee_data_as_of: str | None = None,
    provider_priority: int = 100,
) -> RouteEstimate:
    """Estimate one configurable manual-order fee."""

    profile = (
        ManualFeeProfile.from_execution_config(config)
        if isinstance(config, ExecutionConfig)
        else config
    )
    if amount <= 0:
        return RouteEstimate(
            ROUTE_MANUAL_ORDER,
            D("0"),
            D("0"),
            D("0"),
            D("0"),
            provider_id,
            provider_name,
            fee_data_as_of,
            provider_priority,
        )
    commission = profile.commission_base_eur + amount * profile.commission_pct / D("100")
    commission = min(max(commission, profile.commission_min_eur), profile.commission_max_eur)
    venue = max(profile.venue_fee_min_eur, amount * profile.venue_fee_pct / D("100"))
    fee = (commission + venue + profile.settlement_fee_eur).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    ratio = (fee / amount * D("100")).quantize(D("0.000001"), rounding=ROUND_HALF_UP)
    cash_outlay = (amount + fee).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    return RouteEstimate(
        ROUTE_MANUAL_ORDER,
        amount,
        fee,
        cash_outlay,
        ratio,
        provider_id,
        provider_name,
        fee_data_as_of,
        provider_priority,
    )


def estimate_savings_plan(
    amount: Decimal,
    fee_pct: Decimal,
    *,
    provider_id: str | None = None,
    provider_name: str | None = None,
    fee_data_as_of: str | None = None,
    provider_priority: int = 100,
) -> RouteEstimate:
    if amount <= 0:
        return RouteEstimate(
            ROUTE_UNAVAILABLE,
            D("0"),
            D("0"),
            D("0"),
            D("0"),
            provider_id,
            provider_name,
            fee_data_as_of,
            provider_priority,
        )
    fee = (amount * fee_pct / D("100")).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    ratio = fee_pct.quantize(D("0.000001"), rounding=ROUND_HALF_UP)
    route = ROUTE_FREE_SAVINGS_PLAN if fee_pct == 0 else ROUTE_PAID_SAVINGS_PLAN
    cash_outlay = (amount + fee).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    return RouteEstimate(
        route,
        amount,
        fee,
        cash_outlay,
        ratio,
        provider_id,
        provider_name,
        fee_data_as_of,
        provider_priority,
    )


def savings_plan_fee_pct(
    broker: dict[str, Any],
    isin: str,
    *,
    evaluated_on: date | None = None,
) -> Decimal | None:
    """Return the cheapest fresh configured savings-plan fee, if available."""

    route = preferred_savings_plan_route(broker, isin, evaluated_on=evaluated_on)
    return route.fee_pct if route is not None else None


def _provider_manual_profile(
    provider: ExecutionProvider,
    config: ExecutionConfig,
) -> ManualFeeProfile | None:
    if provider.legacy:
        return ManualFeeProfile.from_execution_config(config)
    return provider.manual_profile


def choose_route(
    *,
    isin: str,
    savings_plan_amount_eur: Decimal,
    manual_order_amount_eur: Decimal,
    broker: dict[str, Any],
    config: ExecutionConfig,
    evaluated_on: date | None = None,
) -> RouteEstimate:
    """Choose the lowest-ratio configured provider/method route.

    This keeps the historical caller contract while extending the candidate set
    across provider-aware routes. Savings-plan freshness may be route-specific;
    manual-order freshness remains provider-level. For schema 1 the numerical
    result is unchanged and the estimate still carries the broker identity.
    """

    candidates: list[RouteEstimate] = []
    providers = execution_providers(broker, evaluated_on=evaluated_on)
    savings_by_provider = {
        item.provider_id: item
        for item in savings_plan_routes(broker, isin, evaluated_on=evaluated_on)
    }
    for provider in providers:
        savings = savings_by_provider.get(provider.provider_id)
        if savings is not None and savings_plan_amount_eur > 0:
            candidates.append(
                estimate_savings_plan(
                    savings_plan_amount_eur,
                    savings.fee_pct,
                    provider_id=provider.provider_id,
                    provider_name=provider.name,
                    fee_data_as_of=(savings.as_of.isoformat() if savings.as_of else None),
                    provider_priority=provider.priority,
                )
            )
        profile = _provider_manual_profile(provider, config) if provider.fresh else None
        if profile is not None and manual_order_amount_eur > 0:
            candidates.append(
                estimate_manual_order(
                    manual_order_amount_eur,
                    profile,
                    provider_id=provider.provider_id,
                    provider_name=provider.name,
                    fee_data_as_of=(provider.as_of.isoformat() if provider.as_of else None),
                    provider_priority=provider.priority,
                )
            )
    candidates = [item for item in candidates if item.order_amount_eur > 0]
    if not candidates:
        return RouteEstimate(ROUTE_UNAVAILABLE, D("0"), D("0"), D("0"), D("0"))
    return min(
        candidates,
        key=lambda item: (
            item.cost_ratio_pct,
            item.provider_priority,
            -item.order_amount_eur,
            item.fee_eur,
            item.route,
            item.provider_id or "",
        ),
    )


def maximum_savings_plan_order_for_cash(
    cash_available_eur: Decimal, fee_pct: Decimal
) -> Decimal:
    """Return the maximum whole-cent savings-plan principal funded by cash."""
    if cash_available_eur <= 0:
        return D("0")
    divisor = D("1") + fee_pct / D("100")
    if divisor <= 0:
        return D("0")
    cents = (cash_available_eur / divisor).quantize(D("0.01"), rounding="ROUND_DOWN")
    while cents > 0 and estimate_savings_plan(cents, fee_pct).cash_outlay_eur > cash_available_eur:
        cents -= D("0.01")
    while estimate_savings_plan(cents + D("0.01"), fee_pct).cash_outlay_eur <= cash_available_eur:
        cents += D("0.01")
    return max(D("0"), cents)


def maximum_manual_order_for_cash(
    cash_available_eur: Decimal,
    config: ExecutionConfig | ManualFeeProfile,
) -> Decimal:
    """Return the maximum whole-cent manual-order principal funded by cash."""
    if cash_available_eur <= 0:
        return D("0")
    low = D("0")
    high = cash_available_eur.quantize(D("0.01"), rounding="ROUND_DOWN")
    for _ in range(48):
        midpoint = ((low + high) / D("2")).quantize(D("0.01"), rounding="ROUND_DOWN")
        if midpoint <= low:
            break
        if estimate_manual_order(midpoint, config).cash_outlay_eur <= cash_available_eur:
            low = midpoint
        else:
            high = midpoint
    while low > 0 and estimate_manual_order(low, config).cash_outlay_eur > cash_available_eur:
        low -= D("0.01")
    return max(D("0"), low.quantize(D("0.01"), rounding="ROUND_DOWN"))


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value.quantize(D("0.01"), rounding="ROUND_DOWN")
    units = (value / step).to_integral_value(rounding="ROUND_DOWN")
    return (units * step).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def choose_route_for_cash(
    *,
    isin: str,
    desired_amount_eur: Decimal,
    periodic_cash_budget_eur: Decimal,
    reserve_cash_budget_eur: Decimal,
    minimum_order_eur: Decimal,
    rounding_step_eur: Decimal,
    broker: dict[str, Any],
    config: ExecutionConfig,
    evaluated_on: date | None = None,
    execution_provider_id: str | None = None,
) -> RouteEstimate:
    """Choose a provider-aware route while respecting the real cash budgets."""

    candidates: list[RouteEstimate] = []
    providers = execution_providers(broker, evaluated_on=evaluated_on)
    savings_by_provider = {
        item.provider_id: item
        for item in savings_plan_routes(broker, isin, evaluated_on=evaluated_on)
    }
    for provider in providers:
        if execution_provider_id is not None and provider.provider_id != execution_provider_id:
            continue
        provider_as_of = provider.as_of.isoformat() if provider.as_of else None
        savings = savings_by_provider.get(provider.provider_id)
        if savings is not None:
            savings_cash = min(reserve_cash_budget_eur, periodic_cash_budget_eur)
            principal = min(
                desired_amount_eur,
                maximum_savings_plan_order_for_cash(savings_cash, savings.fee_pct),
            ).quantize(D("0.01"), rounding=ROUND_HALF_UP)
            while (
                principal > 0
                and estimate_savings_plan(principal, savings.fee_pct).cash_outlay_eur
                > savings_cash
            ):
                principal -= D("0.01")
            if principal >= minimum_order_eur:
                candidates.append(
                    estimate_savings_plan(
                        principal,
                        savings.fee_pct,
                        provider_id=provider.provider_id,
                        provider_name=provider.name,
                        fee_data_as_of=(savings.as_of.isoformat() if savings.as_of else None),
                        provider_priority=provider.priority,
                    )
                )
        profile = _provider_manual_profile(provider, config) if provider.fresh else None
        if profile is not None:
            principal = _floor_to_step(
                min(
                    desired_amount_eur,
                    maximum_manual_order_for_cash(reserve_cash_budget_eur, profile),
                ),
                rounding_step_eur,
            )
            if principal >= minimum_order_eur:
                candidates.append(
                    estimate_manual_order(
                        principal,
                        profile,
                        provider_id=provider.provider_id,
                        provider_name=provider.name,
                        fee_data_as_of=provider_as_of,
                        provider_priority=provider.priority,
                    )
                )
    if not candidates:
        return RouteEstimate(ROUTE_UNAVAILABLE, D("0"), D("0"), D("0"), D("0"))
    return min(
        candidates,
        key=lambda item: (
            item.cost_ratio_pct,
            item.provider_priority,
            -item.order_amount_eur,
            item.fee_eur,
            item.route,
            item.provider_id or "",
        ),
    )


def _route_with_funding(
    route: RouteEstimate,
    *,
    funding_provider_id: str,
    funding_provider_name: str,
    transfer_required: bool,
    transfer_fee_eur: Decimal,
    transfer_days: int,
) -> RouteEstimate:
    """Attach one funding source and include transfer cost in route economics."""

    if route.route == ROUTE_UNAVAILABLE or route.order_amount_eur <= 0:
        return route
    total_fee = route.fee_eur + transfer_fee_eur
    total_outlay = route.cash_outlay_eur + transfer_fee_eur
    ratio = (total_fee / route.order_amount_eur * D("100")).quantize(
        D("0.0001"), rounding=ROUND_HALF_UP
    )
    return RouteEstimate(
        route=route.route,
        order_amount_eur=route.order_amount_eur,
        fee_eur=route.fee_eur,
        cash_outlay_eur=total_outlay,
        cost_ratio_pct=ratio,
        provider_id=route.provider_id,
        provider_name=route.provider_name,
        fee_data_as_of=route.fee_data_as_of,
        provider_priority=route.provider_priority,
        funding_provider_id=funding_provider_id,
        funding_provider_name=funding_provider_name,
        funding_transfer_required=transfer_required,
        funding_transfer_fee_eur=transfer_fee_eur,
        funding_transfer_business_days=transfer_days,
    )


def choose_funded_route_for_cash(
    *,
    isin: str,
    desired_amount_eur: Decimal,
    periodic_cash_budget_eur: Decimal,
    minimum_order_eur: Decimal,
    rounding_step_eur: Decimal,
    broker: dict[str, Any],
    config: ExecutionConfig,
    funding_cash_by_provider: dict[str, Decimal],
    funding_provider_names: dict[str, str],
    charged_transfer_edges: frozenset[tuple[str, str]] = frozenset(),
    evaluated_on: date | None = None,
) -> RouteEstimate:
    """Choose execution provider and provider-scoped funding source together.

    Same-provider funding is implicit and free. Cross-provider funding is eligible
    only when broker schema 3 contains the exact directed edge. A configured fixed
    transfer fee is charged once per source/destination edge in one allocation run;
    subsequent purchases funded through the same edge reuse that planned transfer.
    """

    candidates: list[RouteEstimate] = []
    providers = execution_providers(broker, evaluated_on=evaluated_on)
    for execution_provider in providers:
        for funding_provider_id, raw_cash in sorted(funding_cash_by_provider.items()):
            cash = D(str(raw_cash))
            if not cash.is_finite() or cash <= 0:
                continue
            transfer = transfer_for(
                broker,
                from_provider=funding_provider_id,
                to_provider=execution_provider.provider_id,
                evaluated_on=evaluated_on,
            )
            if transfer is None:
                continue
            edge = (funding_provider_id, execution_provider.provider_id)
            transfer_required = funding_provider_id != execution_provider.provider_id
            transfer_fee = (
                D("0")
                if not transfer_required or edge in charged_transfer_edges
                else transfer.fee_eur
            )
            if cash <= transfer_fee:
                continue
            usable_cash = cash - transfer_fee
            periodic_budget = max(D("0"), periodic_cash_budget_eur - transfer_fee)
            route = choose_route_for_cash(
                isin=isin,
                desired_amount_eur=desired_amount_eur,
                periodic_cash_budget_eur=periodic_budget,
                reserve_cash_budget_eur=usable_cash,
                minimum_order_eur=minimum_order_eur,
                rounding_step_eur=rounding_step_eur,
                broker=broker,
                config=config,
                evaluated_on=evaluated_on,
                execution_provider_id=execution_provider.provider_id,
            )
            if route.route == ROUTE_UNAVAILABLE:
                continue
            candidates.append(
                _route_with_funding(
                    route,
                    funding_provider_id=funding_provider_id,
                    funding_provider_name=funding_provider_names.get(
                        funding_provider_id, funding_provider_id.replace("_", " ").title()
                    ),
                    transfer_required=transfer_required,
                    transfer_fee_eur=transfer_fee,
                    transfer_days=transfer.settlement_business_days if transfer_required else 0,
                )
            )
    if not candidates:
        return RouteEstimate(ROUTE_UNAVAILABLE, D("0"), D("0"), D("0"), D("0"))
    return min(
        candidates,
        key=lambda item: (
            item.cost_ratio_pct,
            item.funding_transfer_business_days,
            item.provider_priority,
            -item.order_amount_eur,
            item.fee_eur + item.funding_transfer_fee_eur,
            item.funding_transfer_required,
            item.route,
            item.provider_id or "",
            item.funding_provider_id or "",
        ),
    )


def preferred_execution_route(
    *,
    isin: str,
    reference_amount_eur: Decimal,
    broker: dict[str, Any],
    config: ExecutionConfig,
    evaluated_on: date | None = None,
) -> RouteEstimate:
    """Return the best nominal route used for exception-assumption review."""

    if reference_amount_eur <= 0:
        return RouteEstimate(ROUTE_UNAVAILABLE, D("0"), D("0"), D("0"), D("0"))
    return choose_route(
        isin=isin,
        savings_plan_amount_eur=reference_amount_eur,
        manual_order_amount_eur=reference_amount_eur,
        broker=broker,
        config=config,
        evaluated_on=evaluated_on,
    )


def efficient_manual_cash_required(config: ExecutionConfig) -> Decimal:
    """Return cash required for the smallest cost-efficient legacy manual order."""
    minimum = efficient_manual_order_minimum(config)
    return estimate_manual_order(minimum, config).cash_outlay_eur


def efficient_manual_order_minimum(
    config: ExecutionConfig,
    profile: ManualFeeProfile | None = None,
) -> Decimal:
    """Return the smallest whole-cent manual order meeting the cost ceiling."""
    if config.max_cost_ratio_pct <= 0:
        return D("0")
    fee_profile: ExecutionConfig | ManualFeeProfile = profile or config
    low = D("0.01")
    high = D("10000000")
    if estimate_manual_order(high, fee_profile).cost_ratio_pct > config.max_cost_ratio_pct:
        return high
    for _ in range(48):
        midpoint = ((low + high) / D("2")).quantize(D("0.01"), rounding=ROUND_HALF_UP)
        if midpoint <= low:
            break
        if estimate_manual_order(midpoint, fee_profile).cost_ratio_pct <= config.max_cost_ratio_pct:
            high = midpoint
        else:
            low = midpoint
    return high.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def efficient_manual_cash_required_for_broker(
    broker: dict[str, Any],
    config: ExecutionConfig,
    *,
    evaluated_on: date | None = None,
) -> Decimal:
    """Return the least cash that makes any fresh provider's manual route efficient."""

    requirements: list[Decimal] = []
    for provider in execution_providers(broker, evaluated_on=evaluated_on):
        if not provider.fresh:
            continue
        profile = _provider_manual_profile(provider, config)
        if profile is None:
            continue
        minimum = efficient_manual_order_minimum(config, profile)
        requirements.append(estimate_manual_order(minimum, profile).cash_outlay_eur)
    return min(requirements, default=D("0"))
