"""Strict provider-neutral REST snapshot contract.

The REST transport lives in the Home Assistant integration layer.  This module is
pure Python and only validates one already-decoded JSON document into canonical
``Position`` objects plus a source-owned snapshot timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Final

from .models import Position

D = Decimal

PROVIDER_LOCAL_REST_JSON: Final = "local_rest_json"
REST_SCHEMA_VERSION: Final = 1
MAX_REST_POSITIONS: Final = 512
MAX_REST_NAME_LENGTH: Final = 160
MAX_REST_TYPE_LENGTH: Final = 64
MAX_REST_POSITION_VALUE_EUR: Final = D("1000000000")
MAX_REST_POSITION_QUANTITY: Final = D("1000000000000")
MAX_REST_CLOCK_SKEW: Final = timedelta(minutes=5)

_IDENTIFIER_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:/+-]{3,15}$")
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_CANONICAL_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?$")

_INSTRUMENT_TYPE_MAP = {
    "etf": "etf",
    "exchange traded fund": "etf",
    "aktie": "stock",
    "stock": "stock",
    "share": "stock",
    "fonds": "fund",
    "fund": "fund",
    "investmentfonds": "fund",
    "mutual fund": "fund",
    "anleihe": "bond",
    "bond": "bond",
    "zertifikat": "certificate",
    "certificate": "certificate",
    "optionsschein": "warrant",
    "warrant": "warrant",
    "etc": "commodity",
    "commodity": "commodity",
    "etn": "note",
    "note": "note",
}


@dataclass(frozen=True, slots=True)
class RestSnapshot:
    """One validated provider-neutral portfolio snapshot."""

    generated_at: datetime
    positions: dict[str, Position]
    investment_reserve_eur: Decimal | None = None
    investment_reserve_as_of: datetime | None = None


def parse_rest_snapshot(
    payload: Any,
    *,
    now: datetime | None = None,
) -> RestSnapshot:
    """Validate schema version 1 and return canonical positions.

    The timestamp is supplied by the source service rather than by the polling
    client.  This keeps freshness and review scheduling stable when Home Assistant
    repeatedly polls an unchanged snapshot.
    """
    if not isinstance(payload, dict):
        raise ValueError("REST response must be a JSON object")

    schema_version = payload.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != REST_SCHEMA_VERSION:
        raise ValueError(
            f"REST response schema_version must be {REST_SCHEMA_VERSION}"
        )

    if payload.get("currency") != "EUR":
        raise ValueError("REST response currency must be EUR")

    generated_at = _parse_generated_at(payload.get("generated_at"), now=now)
    raw_positions = payload.get("positions")
    if not isinstance(raw_positions, list) or not raw_positions:
        raise ValueError("REST response positions must be a non-empty array")
    if len(raw_positions) > MAX_REST_POSITIONS:
        raise ValueError(
            f"REST response may contain at most {MAX_REST_POSITIONS} positions"
        )

    positions: dict[str, Position] = {}
    seen_isins: set[str] = set()
    for index, raw in enumerate(raw_positions, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"REST position {index} must be a JSON object")

        identifier = _clean_identifier(raw.get("identifier"), index=index)
        if identifier in positions:
            raise ValueError(
                f"REST response contains duplicate instrument identifier {identifier}"
            )

        isin = _clean_isin(raw.get("isin"), index=index)
        if isin and isin in seen_isins:
            raise ValueError(f"REST response contains duplicate ISIN {isin}")
        if isin:
            seen_isins.add(isin)

        name = _clean_text(
            raw.get("name"),
            field=f"REST position {index} name",
            maximum=MAX_REST_NAME_LENGTH,
            required=True,
        )
        source_type = _clean_text(
            raw.get("instrument_type", "Other"),
            field=f"REST position {index} instrument_type",
            maximum=MAX_REST_TYPE_LENGTH,
            required=True,
        )
        value_eur = _parse_market_value(raw.get("market_value_eur"), index=index)
        quantity = _parse_optional_quantity(raw.get("quantity"), index=index)

        positions[identifier] = Position(
            wkn=identifier,
            isin=isin,
            name=name,
            instrument_type=_INSTRUMENT_TYPE_MAP.get(
                source_type.strip().casefold(), "other"
            ),
            source_type=source_type,
            value_eur=value_eur,
            quantity=quantity,
        )

    total = sum(item.value_eur for item in positions.values())
    if total <= 0:
        raise ValueError("REST response whole portfolio value must be positive")

    reserve_eur = None
    reserve_as_of = None
    raw_reserve = payload.get("investment_reserve")
    if raw_reserve is not None:
        if not isinstance(raw_reserve, dict):
            raise ValueError("REST response investment_reserve must be an object")
        if set(raw_reserve) != {"available_eur", "as_of"}:
            raise ValueError("REST response investment_reserve has an unexpected schema")
        reserve_eur = _parse_reserve_value(raw_reserve.get("available_eur"))
        reserve_as_of = _parse_generated_at(raw_reserve.get("as_of"), now=now)
        if reserve_as_of > generated_at + MAX_REST_CLOCK_SKEW:
            raise ValueError("REST investment reserve timestamp is newer than the snapshot")
    return RestSnapshot(
        generated_at=generated_at,
        positions=positions,
        investment_reserve_eur=reserve_eur,
        investment_reserve_as_of=reserve_as_of,
    )



def _parse_optional_quantity(value: Any, *, index: int) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"REST position {index} quantity must be a decimal string")
    token = value.strip()
    if _CANONICAL_DECIMAL_RE.fullmatch(token) is None:
        raise ValueError(f"REST position {index} quantity must be a canonical decimal")
    try:
        parsed = D(token)
    except InvalidOperation as err:
        raise ValueError(f"REST position {index} quantity is invalid") from err
    if not parsed.is_finite() or parsed < 0 or parsed > MAX_REST_POSITION_QUANTITY:
        raise ValueError(f"REST position {index} quantity is outside the allowed range")
    return parsed


def _parse_reserve_value(value: Any) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("REST investment reserve must be a decimal string")
    token = value.strip()
    if _CANONICAL_DECIMAL_RE.fullmatch(token) is None:
        raise ValueError("REST investment reserve must be a canonical EUR decimal")
    try:
        parsed = D(token)
    except InvalidOperation as err:
        raise ValueError("REST investment reserve is invalid") from err
    if not parsed.is_finite() or parsed < 0 or parsed > MAX_REST_POSITION_VALUE_EUR:
        raise ValueError("REST investment reserve is outside the allowed range")
    return parsed

def _parse_generated_at(value: Any, *, now: datetime | None) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("REST response generated_at must be an ISO-8601 timestamp")
    token = value.strip()
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError as err:
        raise ValueError(
            "REST response generated_at must be an ISO-8601 timestamp"
        ) from err
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("REST response generated_at must include a timezone")
    parsed = parsed.astimezone(timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    if parsed > current + MAX_REST_CLOCK_SKEW:
        raise ValueError("REST response generated_at is too far in the future")
    return parsed


def _clean_identifier(value: Any, *, index: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"REST position {index} identifier must be a string")
    cleaned = value.strip().upper()
    if _IDENTIFIER_RE.fullmatch(cleaned) is None:
        raise ValueError(f"REST position {index} contains an invalid identifier")
    return cleaned


def _clean_isin(value: Any, *, index: int) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError(f"REST position {index} ISIN must be a string")
    cleaned = value.strip().upper()
    if _ISIN_RE.fullmatch(cleaned) is None:
        raise ValueError(f"REST position {index} contains an invalid ISIN")
    return cleaned


def _clean_text(value: Any, *, field: str, maximum: int, required: bool) -> str:
    if value is None:
        cleaned = ""
    elif isinstance(value, str):
        cleaned = value.strip()
    else:
        raise ValueError(f"{field} must be a string")
    if required and not cleaned:
        raise ValueError(f"{field} is required")
    if len(cleaned) > maximum or any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise ValueError(f"{field} is too long or contains control characters")
    return cleaned


def _parse_market_value(value: Any, *, index: int) -> Decimal:
    # Require a JSON string so no binary floating-point conversion can occur
    # before Decimal parses the source-owned monetary value.
    if not isinstance(value, str):
        raise ValueError(
            f"REST position {index} market_value_eur must be a decimal string"
        )
    token = value.strip()
    if _CANONICAL_DECIMAL_RE.fullmatch(token) is None:
        raise ValueError(
            f"REST position {index} market_value_eur must be a canonical EUR decimal"
        )
    try:
        parsed = D(token)
    except InvalidOperation as err:
        raise ValueError(
            f"REST position {index} market_value_eur is invalid"
        ) from err
    if not parsed.is_finite() or parsed < 0 or parsed > MAX_REST_POSITION_VALUE_EUR:
        raise ValueError(
            f"REST position {index} market_value_eur is outside the allowed range"
        )
    return parsed


__all__ = [
    "MAX_REST_POSITIONS",
    "PROVIDER_LOCAL_REST_JSON",
    "REST_SCHEMA_VERSION",
    "RestSnapshot",
    "parse_rest_snapshot",
]
