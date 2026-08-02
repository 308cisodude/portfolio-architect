"""Canonical JSON-safe representation for persisted calculated payloads."""

from __future__ import annotations

from decimal import Decimal
import math
from typing import Any


def json_safe_payload(value: Any) -> Any:
    """Return a detached JSON-safe copy while preserving decimal precision.

    The calculation engine deliberately uses ``Decimal`` internally. Home
    Assistant's storage helper accepts JSON-compatible values only, so decimals
    are stored as plain decimal strings. The integration's payload parser
    accepts those strings and converts them to bounded numeric values when the
    cache is restored.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Calculated payload contains a non-finite decimal")
        return format(value, "f")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Calculated payload contains a non-finite float")
        return value
    if isinstance(value, dict):
        converted: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("Calculated payload contains a non-string mapping key")
            converted[key] = json_safe_payload(item)
        return converted
    if isinstance(value, (list, tuple)):
        return [json_safe_payload(item) for item in value]
    raise TypeError(
        f"Calculated payload contains unsupported value type {type(value).__name__}"
    )
