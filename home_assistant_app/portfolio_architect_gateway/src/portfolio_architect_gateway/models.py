"""Provider-neutral snapshot model shared with the v1.4 REST contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Final

from .errors import ProtocolError

MAX_POSITIONS: Final = 512
MAX_SNAPSHOT_BYTES: Final = 1024 * 1024
MAX_POSITION_VALUE_EUR: Final = Decimal("1000000000")
_IDENTIFIER_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:/+-]{3,15}$")
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?$")


@dataclass(frozen=True, slots=True)
class Position:
    """One canonical EUR position exposed to Home Assistant."""

    identifier: str
    name: str
    market_value_eur: Decimal
    quantity: Decimal | None = None
    isin: str = ""
    instrument_type: str = "Other"

    def as_dict(self) -> dict[str, str]:
        data = {
            "identifier": self.identifier,
            "name": self.name,
            "market_value_eur": canonical_decimal(self.market_value_eur),
            "instrument_type": self.instrument_type,
        }
        if self.quantity is not None:
            data["quantity"] = canonical_decimal(self.quantity)
        if self.isin:
            data["isin"] = self.isin
        return data


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """One immutable schema-1 REST snapshot."""

    generated_at: datetime
    positions: tuple[Position, ...]
    investment_reserve_eur: Decimal | None = None
    investment_reserve_as_of: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        timestamp = self.generated_at.astimezone(timezone.utc).isoformat(timespec="seconds")
        if timestamp.endswith("+00:00"):
            timestamp = f"{timestamp[:-6]}Z"
        data = {
            "schema_version": 1,
            "generated_at": timestamp,
            "currency": "EUR",
            "positions": [position.as_dict() for position in self.positions],
        }
        if self.investment_reserve_eur is not None and self.investment_reserve_as_of is not None:
            reserve_timestamp = self.investment_reserve_as_of.astimezone(timezone.utc).isoformat(timespec="seconds")
            if reserve_timestamp.endswith("+00:00"):
                reserve_timestamp = f"{reserve_timestamp[:-6]}Z"
            data["investment_reserve"] = {
                "available_eur": canonical_decimal(self.investment_reserve_eur),
                "as_of": reserve_timestamp,
            }
        return data

    def to_bytes(self) -> bytes:
        body = json.dumps(
            self.as_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(body) > MAX_SNAPSHOT_BYTES:
            raise ProtocolError("Generated snapshot exceeds the 1 MiB contract limit")
        return body

    @property
    def etag(self) -> str:
        return f'"sha256-{hashlib.sha256(self.to_bytes()).hexdigest()}"'


def canonical_decimal(value: Decimal) -> str:
    """Render a finite non-negative Decimal without grouping or exponent notation."""
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ProtocolError("Market value must be a finite non-negative decimal")
    token = format(value, "f")
    if "." in token:
        token = token.rstrip("0").rstrip(".")
    token = token or "0"
    if _DECIMAL_RE.fullmatch(token) is None:
        raise ProtocolError("Market value is outside the canonical REST decimal contract")
    return token


def validate_snapshot(snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
    """Validate the same externally visible invariants enforced by Home Assistant."""
    if snapshot.generated_at.tzinfo is None or snapshot.generated_at.utcoffset() is None:
        raise ProtocolError("Snapshot timestamp must include a timezone")
    if not snapshot.positions or len(snapshot.positions) > MAX_POSITIONS:
        raise ProtocolError("Snapshot must contain between 1 and 512 positions")

    identifiers: set[str] = set()
    isins: set[str] = set()
    total = Decimal("0")
    validated: list[Position] = []
    for position in snapshot.positions:
        identifier = position.identifier.strip().upper()
        if _IDENTIFIER_RE.fullmatch(identifier) is None:
            raise ProtocolError("Position contains an invalid stable identifier")
        if identifier in identifiers:
            raise ProtocolError("Snapshot contains a duplicate identifier")
        identifiers.add(identifier)

        name = _clean_text(position.name, maximum=160, field="position name")
        instrument_type = _clean_text(
            position.instrument_type or "Other",
            maximum=64,
            field="instrument type",
        )
        isin = position.isin.strip().upper()
        if isin and _ISIN_RE.fullmatch(isin) is None:
            raise ProtocolError("Position contains an invalid ISIN")
        if isin and isin in isins:
            raise ProtocolError("Snapshot contains a duplicate ISIN")
        if isin:
            isins.add(isin)
        canonical_decimal(position.market_value_eur)
        if position.market_value_eur > MAX_POSITION_VALUE_EUR:
            raise ProtocolError("Position market value exceeds the contract limit")
        total += position.market_value_eur
        validated.append(
            Position(
                identifier=identifier,
                name=name,
                market_value_eur=position.market_value_eur,
                quantity=position.quantity,
                isin=isin,
                instrument_type=instrument_type,
            )
        )
    if total <= 0:
        raise ProtocolError("Whole portfolio value must be positive")
    reserve = snapshot.investment_reserve_eur
    reserve_as_of = snapshot.investment_reserve_as_of
    if (reserve is None) != (reserve_as_of is None):
        raise ProtocolError("Investment reserve amount and timestamp must be supplied together")
    if reserve is not None:
        canonical_decimal(reserve)
        if reserve > MAX_POSITION_VALUE_EUR:
            raise ProtocolError("Investment reserve exceeds the contract limit")
        if reserve_as_of is None or reserve_as_of.tzinfo is None or reserve_as_of.utcoffset() is None:
            raise ProtocolError("Investment reserve timestamp must include a timezone")
        reserve_as_of = reserve_as_of.astimezone(timezone.utc)
    result = PortfolioSnapshot(
        generated_at=snapshot.generated_at.astimezone(timezone.utc),
        positions=tuple(validated),
        investment_reserve_eur=reserve,
        investment_reserve_as_of=reserve_as_of,
    )
    result.to_bytes()
    return result


def parse_snapshot_bytes(data: bytes) -> PortfolioSnapshot:
    """Parse a cached snapshot using duplicate-key rejection and strict bounds."""
    if not data or len(data) > MAX_SNAPSHOT_BYTES:
        raise ProtocolError("Cached snapshot is empty or exceeds the 1 MiB limit")
    try:
        raw = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ProtocolError) as err:
        raise ProtocolError("Cached snapshot is not valid strict UTF-8 JSON") from err
    if not isinstance(raw, dict) or raw.get("schema_version") != 1 or raw.get("currency") != "EUR":
        raise ProtocolError("Cached snapshot has an unsupported schema")
    timestamp = raw.get("generated_at")
    if not isinstance(timestamp, str):
        raise ProtocolError("Cached snapshot timestamp is missing")
    if timestamp.endswith("Z"):
        timestamp = f"{timestamp[:-1]}+00:00"
    try:
        generated_at = datetime.fromisoformat(timestamp)
    except ValueError as err:
        raise ProtocolError("Cached snapshot timestamp is invalid") from err
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ProtocolError("Cached snapshot timestamp lacks a timezone")
    raw_positions = raw.get("positions")
    if not isinstance(raw_positions, list):
        raise ProtocolError("Cached snapshot positions are invalid")
    positions: list[Position] = []
    for item in raw_positions:
        if not isinstance(item, dict):
            raise ProtocolError("Cached snapshot position is invalid")
        market_value = item.get("market_value_eur")
        if not isinstance(market_value, str) or _DECIMAL_RE.fullmatch(market_value) is None:
            raise ProtocolError("Cached snapshot market value is invalid")
        try:
            amount = Decimal(market_value)
        except InvalidOperation as err:
            raise ProtocolError("Cached snapshot market value is invalid") from err
        positions.append(
            Position(
                identifier=_required_string(item, "identifier"),
                name=_required_string(item, "name"),
                market_value_eur=amount,
                isin=_optional_string(item, "isin"),
                instrument_type=_optional_string(item, "instrument_type") or "Other",
            )
        )
    reserve_eur = None
    reserve_as_of = None
    raw_reserve = raw.get("investment_reserve")
    if raw_reserve is not None:
        if not isinstance(raw_reserve, dict) or set(raw_reserve) != {"available_eur", "as_of"}:
            raise ProtocolError("Cached snapshot investment reserve is invalid")
        amount = raw_reserve.get("available_eur")
        if not isinstance(amount, str) or _DECIMAL_RE.fullmatch(amount) is None:
            raise ProtocolError("Cached snapshot investment reserve is invalid")
        try:
            reserve_eur = Decimal(amount)
        except InvalidOperation as err:
            raise ProtocolError("Cached snapshot investment reserve is invalid") from err
        reserve_timestamp = raw_reserve.get("as_of")
        if not isinstance(reserve_timestamp, str):
            raise ProtocolError("Cached snapshot investment reserve timestamp is invalid")
        if reserve_timestamp.endswith("Z"):
            reserve_timestamp = f"{reserve_timestamp[:-1]}+00:00"
        try:
            reserve_as_of = datetime.fromisoformat(reserve_timestamp)
        except ValueError as err:
            raise ProtocolError("Cached snapshot investment reserve timestamp is invalid") from err
    return validate_snapshot(
        PortfolioSnapshot(
            generated_at=generated_at,
            positions=tuple(positions),
            investment_reserve_eur=reserve_eur,
            investment_reserve_as_of=reserve_as_of,
        )
    )


def _clean_text(value: str, *, maximum: int, field: str) -> str:
    if not isinstance(value, str):
        raise ProtocolError(f"{field} must be a string")
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum or any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise ProtocolError(f"{field} is empty, too long, or contains control characters")
    return cleaned


def _required_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str):
        raise ProtocolError(f"Cached snapshot {key} must be a string")
    return value


def _optional_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key, "")
    if not isinstance(value, str):
        raise ProtocolError(f"Cached snapshot {key} must be a string")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("JSON document contains a duplicate object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ProtocolError(f"JSON constant {value} is not allowed")
