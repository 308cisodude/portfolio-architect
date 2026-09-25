"""Bounded App-private DKB FinTS shadow evidence; never an acquisition source."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any

from .dkb_holdings_review import MAX_REVIEW_ROWS, ReviewRow
from .errors import ProtocolError
from .store import load_json_state, save_json_state

SHADOW_MAX_AGE = timedelta(hours=24)
_ISIN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]\Z")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]{0,9})(?:\.[0-9]{1,12})?\Z")
_CURRENCY = re.compile(r"[A-Z]{3}\Z")


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("invalid shadow timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as err:
        raise ValueError("invalid shadow timestamp") from err
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("invalid shadow timezone")
    return parsed.astimezone(timezone.utc)


def _valid_number(value: Any) -> bool:
    if not isinstance(value, str) or not _DECIMAL.fullmatch(value):
        return False
    try:
        return Decimal(value).is_finite() and Decimal(value) <= Decimal("1000000000")
    except InvalidOperation:
        return False


def validate_shadow(raw: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Reject corrupted, partial, ambiguous and future evidence without using it."""
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "observed_at", "positions"} or raw["schema_version"] != 1:
        raise ValueError("invalid shadow schema")
    observed = _timestamp(raw["observed_at"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if observed > current + timedelta(minutes=5):
        raise ValueError("future shadow observation")
    positions = raw["positions"]
    if not isinstance(positions, list) or len(positions) > MAX_REVIEW_ROWS:
        raise ValueError("invalid shadow positions")
    seen: set[str] = set()
    for row in positions:
        if not isinstance(row, dict) or set(row) != {"isin", "quantity", "total_value", "currency"}:
            raise ValueError("invalid shadow position")
        isin = row["isin"]
        if not isinstance(isin, str) or not _ISIN.fullmatch(isin) or isin in seen:
            raise ValueError("invalid or duplicate shadow identifier")
        seen.add(isin)
        if not _valid_number(row["quantity"]) or not _valid_number(row["total_value"]):
            raise ValueError("invalid shadow amount")
        if not isinstance(row["currency"], str) or not _CURRENCY.fullmatch(row["currency"]):
            raise ValueError("invalid shadow currency")
    return raw


def project_shadow(rows: tuple[ReviewRow, ...], observed_at: str) -> dict[str, Any] | None:
    """Persist only complete fixed fields; never raw PyFinTS or review details."""
    payload = {"schema_version": 1, "observed_at": observed_at,
               "positions": [{"isin": row.isin, "quantity": row.quantity,
                              "total_value": row.value, "currency": row.currency} for row in rows]}
    try:
        return validate_shadow(payload)
    except ValueError:
        return None


def load_shadow(path: Path) -> dict[str, Any] | None:
    raw = load_json_state(path)
    return validate_shadow(raw) if raw is not None else None


def shadow_summary(path: Path, now: datetime | None = None) -> dict[str, Any]:
    """Status has no position detail; stale evidence is never considered current."""
    try:
        shadow = load_shadow(path)
    except (ValueError, OSError, ProtocolError):
        return {"state": "invalid", "observed_at": None, "position_count": None}
    if shadow is None:
        return {"state": "absent", "observed_at": None, "position_count": None}
    observed = _timestamp(shadow["observed_at"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    state = "fresh" if timedelta(0) <= current - observed < SHADOW_MAX_AGE else "stale"
    return {"state": state, "observed_at": observed.isoformat(timespec="seconds"),
            "position_count": len(shadow["positions"])}


def save_shadow(path: Path, value: dict[str, Any]) -> None:
    save_json_state(path, validate_shadow(value))
