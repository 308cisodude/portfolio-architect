"""Provider-scoped investment-cash and explicit funding-transfer topology."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any, Final

D = Decimal
_PROVIDER_ID_RE: Final = re.compile(r"^[a-z0-9_]{1,32}$")
_MAX_FUNDING_TRANSFERS: Final = 64
_MAX_TRANSFER_FEE_EUR: Final = D("10000")
_MAX_SETTLEMENT_DAYS: Final = 30
_MAX_PROVIDER_NAME: Final = 80
_MAX_PROVIDER_CASH_SOURCES: Final = 16
_MAX_TRANSFER_EVIDENCE_SOURCE: Final = 160


@dataclass(frozen=True, slots=True)
class FundingTransfer:
    """One explicitly configured directed funding relationship."""

    from_provider: str
    to_provider: str
    fee_eur: Decimal
    settlement_business_days: int
    evidence_source: str | None = None
    evidence_as_of: date | None = None
    evidence_fresh: bool = True


@dataclass(frozen=True, slots=True)
class ProviderCash:
    """One provider-scoped authorized investment-cash pool."""

    provider_id: str
    provider_name: str
    available_eur: Decimal
    as_of: str | None = None
    account_balance_eur: Decimal | None = None
    eligible_eur: Decimal | None = None
    authorized_eur: Decimal | None = None
    authorization_policy: str | None = None
    authorization_cap_eur: Decimal | None = None
    authorization_retain_eur: Decimal | None = None


def _provider_id(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or _PROVIDER_ID_RE.fullmatch(value) is None:
        raise ValueError(f"{field} is invalid")
    return value


def _money(value: Any, *, field: str, maximum: Decimal = D("1000000000")) -> Decimal:
    try:
        parsed = D(str(value))
    except Exception as err:  # Decimal raises several concrete numeric exceptions.
        raise ValueError(f"{field} is invalid") from err
    if not parsed.is_finite() or parsed < 0 or parsed > maximum:
        raise ValueError(f"{field} is invalid")
    return parsed.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def _evidence_source(value: Any, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value.strip()) > _MAX_TRANSFER_EVIDENCE_SOURCE
        or any(ord(char) < 32 for char in value)
    ):
        raise ValueError(f"{field} is invalid")
    return value.strip()


def funding_transfers(
    broker: dict[str, Any], *, evaluated_on: date | None = None
) -> tuple[FundingTransfer, ...]:
    """Return strict directed transfer edges from broker schema 3.

    Broker schemas 1 and 2 intentionally contain no cross-provider funding
    relationships. Same-provider cash is always usable locally and needs no edge.
    Schema 3 adds only explicit directed edges; reverse transferability is never
    inferred. v1.40 optionally binds an edge to operator-owned evidence using
    ``source`` + ``as_of``. Evidenced edges use the existing broker
    ``fee_data_max_age_days`` window and become ineligible when stale.

    Legacy schema-3 edges without provenance remain accepted for backward
    compatibility, but the native editor creates evidence-backed edges.
    """

    if not isinstance(broker, dict):
        raise ValueError("broker document must be an object")
    schema = broker.get("schema_version", 1)
    if isinstance(schema, bool) or not isinstance(schema, int):
        raise ValueError("broker schema_version is invalid")
    if schema in {1, 2}:
        return ()
    if schema != 3:
        raise ValueError("broker schema_version is unsupported")

    providers = broker.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ValueError("broker schema 3 requires providers")
    provider_ids = {
        _provider_id(provider_id, field="provider id") for provider_id in providers
    }
    raw_edges = broker.get("funding_transfers")
    if not isinstance(raw_edges, list) or len(raw_edges) > _MAX_FUNDING_TRANSFERS:
        raise ValueError("broker schema 3 requires a bounded funding_transfers list")

    max_age_raw = broker.get("fee_data_max_age_days")
    if isinstance(max_age_raw, bool) or not isinstance(max_age_raw, int) or not 1 <= max_age_raw <= 366:
        raise ValueError("broker fee_data_max_age_days is invalid")
    today = evaluated_on or date.today()

    seen: set[tuple[str, str]] = set()
    result: list[FundingTransfer] = []
    required = {
        "from_provider",
        "to_provider",
        "fee_eur",
        "settlement_business_days",
    }
    evidence_fields = {"source", "as_of"}
    for index, raw in enumerate(raw_edges):
        if not isinstance(raw, dict):
            raise ValueError(f"funding_transfers[{index}] is invalid")
        keys = set(raw)
        if frozenset(keys) not in {frozenset(required), frozenset(required | evidence_fields)}:
            raise ValueError(f"funding_transfers[{index}] is invalid")
        source = _provider_id(raw["from_provider"], field=f"funding_transfers[{index}].from_provider")
        destination = _provider_id(raw["to_provider"], field=f"funding_transfers[{index}].to_provider")
        if source not in provider_ids or destination not in provider_ids:
            raise ValueError(f"funding_transfers[{index}] references an unknown provider")
        if source == destination:
            raise ValueError("same-provider funding must not be configured as a transfer")
        edge = (source, destination)
        if edge in seen:
            raise ValueError("duplicate funding transfer relationship")
        seen.add(edge)
        days = raw["settlement_business_days"]
        if isinstance(days, bool) or not isinstance(days, int) or not 0 <= days <= _MAX_SETTLEMENT_DAYS:
            raise ValueError(f"funding_transfers[{index}].settlement_business_days is invalid")

        evidence_source: str | None = None
        evidence_as_of: date | None = None
        evidence_fresh = True
        if evidence_fields.issubset(keys):
            evidence_source = _evidence_source(
                raw["source"], field=f"funding_transfers[{index}].source"
            )
            try:
                evidence_as_of = date.fromisoformat(str(raw["as_of"]))
            except ValueError as err:
                raise ValueError(f"funding_transfers[{index}].as_of is invalid") from err
            if evidence_as_of > today:
                raise ValueError(f"funding_transfers[{index}].as_of is in the future")
            evidence_fresh = (today - evidence_as_of).days <= max_age_raw

        result.append(
            FundingTransfer(
                from_provider=source,
                to_provider=destination,
                fee_eur=_money(
                    raw["fee_eur"],
                    field=f"funding_transfers[{index}].fee_eur",
                    maximum=_MAX_TRANSFER_FEE_EUR,
                ),
                settlement_business_days=days,
                evidence_source=evidence_source,
                evidence_as_of=evidence_as_of,
                evidence_fresh=evidence_fresh,
            )
        )
    return tuple(sorted(result, key=lambda item: (item.from_provider, item.to_provider)))


def transfer_for(
    broker: dict[str, Any], *, from_provider: str, to_provider: str, evaluated_on: date | None = None
) -> FundingTransfer | None:
    """Return one explicit fresh directed transfer edge, or None when unavailable."""

    if from_provider == to_provider:
        return FundingTransfer(from_provider, to_provider, D("0"), 0)
    for item in funding_transfers(broker, evaluated_on=evaluated_on):
        if (
            item.from_provider == from_provider
            and item.to_provider == to_provider
            and item.evidence_fresh
        ):
            return item
    return None


def provider_cash_from_metadata(raw: Any) -> tuple[ProviderCash, ...]:
    """Validate bounded provider-scoped cash metadata from the coordinator."""

    if raw is None:
        return ()
    if not isinstance(raw, list) or len(raw) > _MAX_PROVIDER_CASH_SOURCES:
        raise ValueError("provider investment cash metadata is invalid")
    seen: set[str] = set()
    result: list[ProviderCash] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("provider investment cash entry is invalid")
        allowed = {
            "provider_id",
            "provider_name",
            "available_eur",
            "as_of",
            "account_balance_eur",
            "eligible_eur",
            "authorized_eur",
            "authorization_policy",
            "authorization_cap_eur",
            "authorization_retain_eur",
        }
        if not set(item).issubset(allowed) or not {"provider_id", "provider_name", "available_eur"}.issubset(item):
            raise ValueError("provider investment cash entry has unexpected fields")
        provider_id = _provider_id(item["provider_id"], field=f"provider cash {index} provider_id")
        if provider_id in seen:
            raise ValueError("duplicate provider investment cash entry")
        seen.add(provider_id)
        name = item["provider_name"]
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name.strip()) > _MAX_PROVIDER_NAME
            or any(ord(char) < 32 for char in name)
        ):
            raise ValueError("provider investment cash name is invalid")
        as_of = item.get("as_of")
        if as_of is not None and (not isinstance(as_of, str) or not as_of or len(as_of) > 64):
            raise ValueError("provider investment cash timestamp is invalid")
        available = _money(item["available_eur"], field="provider investment cash available_eur")
        account = None if item.get("account_balance_eur") is None else _money(item["account_balance_eur"], field="provider investment account balance")
        eligible = None if item.get("eligible_eur") is None else _money(item["eligible_eur"], field="provider eligible investment cash")
        authorized = None if item.get("authorized_eur") is None else _money(item["authorized_eur"], field="provider authorized investment cash")
        policy = item.get("authorization_policy")
        cap = None if item.get("authorization_cap_eur") is None else _money(item["authorization_cap_eur"], field="provider investment cash authorization cap")
        retain = None if item.get("authorization_retain_eur") is None else _money(item["authorization_retain_eur"], field="provider investment cash retained amount")
        if policy is not None and policy not in {"all_available", "capped", "retain"}:
            raise ValueError("provider investment cash authorization policy is invalid")
        rich = any(value is not None for value in (account, eligible, authorized, policy, cap, retain))
        if rich:
            if account is None or eligible is None or authorized is None or policy is None:
                raise ValueError("provider investment cash authorization metadata is incomplete")
            if authorized != available:
                raise ValueError("provider investment cash available and authorized values differ")
            if eligible > account or authorized > eligible:
                raise ValueError("provider investment cash authorization values are inconsistent")
            if policy == "all_available":
                if cap is not None or retain is not None or authorized != eligible:
                    raise ValueError("all-available provider cash authorization is inconsistent")
            elif policy == "capped":
                if cap is None or retain is not None or authorized != min(eligible, cap):
                    raise ValueError("capped provider cash authorization is inconsistent")
            elif retain is None or cap is not None or authorized != max(D("0"), eligible - retain):
                raise ValueError("retained provider cash authorization is inconsistent")
        result.append(
            ProviderCash(
                provider_id=provider_id,
                provider_name=name.strip(),
                available_eur=available,
                as_of=as_of,
                account_balance_eur=account,
                eligible_eur=eligible,
                authorized_eur=authorized,
                authorization_policy=policy,
                authorization_cap_eur=cap,
                authorization_retain_eur=retain,
            )
        )
    return tuple(sorted(result, key=lambda item: item.provider_id))
