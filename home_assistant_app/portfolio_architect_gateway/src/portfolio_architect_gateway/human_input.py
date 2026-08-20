"""Shared bounded parsing primitives for human-entered Gateway values.

These helpers are deliberately opt-in. They normalize only fields whose semantics are
explicitly human-numeric. Protocol identifiers, registrations, credentials, tokens and
other exact strings must bypass this module and retain exact string semantics.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Final, Literal

MAX_HUMAN_NUMERIC_TOKEN_LENGTH: Final = 64
_GROUPING_CHARS: Final = frozenset({".", ",", " ", "'"})
_ALLOWED_NUMERIC_CHARS: Final = frozenset("0123456789., '")


class HumanInputError(ValueError):
    """Bounded validation failure for one human-entered value.

    Error messages intentionally describe only the expected shape/range and never echo
    the rejected token.
    """


_AmbiguousThreeDigits = Literal["decimal", "grouping", "reject"]


def parse_human_eur(
    value: str,
    *,
    label: str = "Amount",
    minimum: Decimal = Decimal("0"),
    maximum: Decimal = Decimal("1000000000"),
) -> Decimal:
    """Parse a human EUR amount with at most two fractional digits.

    Common English/German grouping and decimal conventions are accepted. A single dot
    or comma followed by exactly three digits is interpreted as thousands grouping,
    preserving the live-proven v1.35.4 Comdirect cash-input behavior.
    """

    return _parse_human_decimal(
        value,
        label=label,
        minimum=minimum,
        maximum=maximum,
        max_fractional_digits=2,
        ambiguous_three_digits="grouping",
    )


def parse_human_percentage(
    value: str,
    *,
    label: str = "Percentage",
    minimum: Decimal = Decimal("0"),
    maximum: Decimal = Decimal("100"),
    max_fractional_digits: int = 4,
) -> Decimal:
    """Parse a bounded human percentage.

    A single dot/comma followed by three digits is interpreted as a decimal separator,
    because fractional percentages are common while thousands-grouped percentages are
    not. Callers still own any narrower provider/field-specific semantic bounds.
    """

    return _parse_human_decimal(
        value,
        label=label,
        minimum=minimum,
        maximum=maximum,
        max_fractional_digits=max_fractional_digits,
        ambiguous_three_digits="decimal",
    )


def parse_human_quantity(
    value: str,
    *,
    label: str = "Quantity",
    minimum: Decimal = Decimal("0"),
    maximum: Decimal,
    max_fractional_digits: int = 8,
) -> Decimal:
    """Parse a bounded human quantity while rejecting three-digit separator ambiguity.

    Quantities often legitimately use three or more fractional digits. Therefore a
    lone ``1.234``-style token is ambiguous across locales and is rejected rather than
    guessed. Unambiguous grouped forms (for example ``1 234,5678``) remain accepted.
    """

    return _parse_human_decimal(
        value,
        label=label,
        minimum=minimum,
        maximum=maximum,
        max_fractional_digits=max_fractional_digits,
        ambiguous_three_digits="reject",
    )


def parse_bounded_integer(
    value: str,
    *,
    label: str = "Value",
    minimum: int,
    maximum: int,
) -> int:
    """Parse one non-signed human integer with validated thousands grouping."""

    if isinstance(minimum, bool) or isinstance(maximum, bool) or minimum > maximum:
        raise ValueError("invalid integer bounds")
    token = _normalize_token(value, label=label)
    if "." in token and "," in token:
        raise _error(label, "must be a whole number")
    try:
        digits = _ungroup_integer(token, decimal_sep=None)
        parsed = int(digits)
    except (TypeError, ValueError) as err:
        raise _error(label, "must be a whole number") from err
    if not minimum <= parsed <= maximum:
        raise _error(label, f"must be between {minimum} and {maximum}")
    return parsed


def _parse_human_decimal(
    value: str,
    *,
    label: str,
    minimum: Decimal,
    maximum: Decimal,
    max_fractional_digits: int,
    ambiguous_three_digits: _AmbiguousThreeDigits,
) -> Decimal:
    _validate_decimal_bounds(minimum, maximum, max_fractional_digits)
    token = _normalize_token(value, label=label)
    try:
        canonical = _canonicalize_decimal_token(
            token,
            max_fractional_digits=max_fractional_digits,
            ambiguous_three_digits=ambiguous_three_digits,
        )
        parsed = Decimal(canonical)
    except (InvalidOperation, ValueError) as err:
        raise _error(
            label,
            f"must be a non-negative number with at most {max_fractional_digits} decimals",
        ) from err
    if not parsed.is_finite() or parsed < minimum or parsed > maximum:
        raise _error(label, f"must be between {_plain(minimum)} and {_plain(maximum)}")
    return parsed


def _normalize_token(value: str, *, label: str) -> str:
    if not isinstance(value, str):
        raise _error(label, "has an invalid value")
    token = value.strip()
    if not token or len(token) > MAX_HUMAN_NUMERIC_TOKEN_LENGTH:
        raise _error(label, "has an invalid value")
    normalized = token.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2019", "'")
    if any(char not in _ALLOWED_NUMERIC_CHARS for char in normalized):
        raise _error(label, "has an invalid value")
    return normalized


def _canonicalize_decimal_token(
    token: str,
    *,
    max_fractional_digits: int,
    ambiguous_three_digits: _AmbiguousThreeDigits,
) -> str:
    dot_count = token.count(".")
    comma_count = token.count(",")
    decimal_sep: str | None = None

    if dot_count and comma_count:
        decimal_sep = "." if token.rfind(".") > token.rfind(",") else ","
        if token.count(decimal_sep) != 1:
            raise ValueError("repeated decimal separator")
    elif dot_count == 1 or comma_count == 1:
        separator = "." if dot_count else ","
        trailing = len(token) - token.rfind(separator) - 1
        if trailing <= 0:
            raise ValueError("missing fractional/grouped digits")
        if trailing == 3:
            if ambiguous_three_digits == "decimal":
                if max_fractional_digits >= 3:
                    decimal_sep = separator
            elif ambiguous_three_digits == "reject":
                raise ValueError("ambiguous single separator")
            # grouping deliberately leaves decimal_sep as None
        elif trailing <= max_fractional_digits:
            decimal_sep = separator
    # Multiple occurrences of only one punctuation are validated as grouping below.

    if decimal_sep is None:
        integer_part = token
        fraction = ""
    else:
        integer_part, fraction = token.rsplit(decimal_sep, 1)
        if not fraction or len(fraction) > max_fractional_digits or not fraction.isdigit():
            raise ValueError("invalid fractional part")
        if decimal_sep in integer_part:
            raise ValueError("decimal separator reused as grouping")

    digits = _ungroup_integer(integer_part, decimal_sep=decimal_sep)
    return digits + (("." + fraction) if fraction else "")


def _ungroup_integer(value: str, *, decimal_sep: str | None) -> str:
    if not value:
        raise ValueError("missing integer part")
    grouping_candidates = set(_GROUPING_CHARS)
    if decimal_sep is not None:
        grouping_candidates.discard(decimal_sep)
    present = {char for char in grouping_candidates if char in value}
    if len(present) > 1:
        raise ValueError("mixed grouping separators")
    if not present:
        if not value.isdigit() or (len(value) > 1 and value.startswith("0")):
            raise ValueError("invalid integer part")
        return value

    separator = next(iter(present))
    groups = value.split(separator)
    if any(not group.isdigit() for group in groups):
        raise ValueError("invalid grouped integer")
    first = groups[0]
    if not 1 <= len(first) <= 3 or (len(first) > 1 and first.startswith("0")) or first == "0":
        raise ValueError("invalid first grouping")
    if any(len(group) != 3 for group in groups[1:]):
        raise ValueError("invalid thousands grouping")
    return "".join(groups)


def _validate_decimal_bounds(minimum: Decimal, maximum: Decimal, max_fractional_digits: int) -> None:
    if (
        not isinstance(minimum, Decimal)
        or not isinstance(maximum, Decimal)
        or not minimum.is_finite()
        or not maximum.is_finite()
        or minimum < 0
        or minimum > maximum
        or isinstance(max_fractional_digits, bool)
        or not isinstance(max_fractional_digits, int)
        or not 0 <= max_fractional_digits <= 18
    ):
        raise ValueError("invalid decimal input policy")


def _error(label: str, guidance: str) -> HumanInputError:
    safe_label = label if isinstance(label, str) and 1 <= len(label) <= 48 else "Value"
    return HumanInputError(f"{safe_label} {guidance}")


def _plain(value: Decimal) -> str:
    token = format(value, "f")
    if "." in token:
        token = token.rstrip("0").rstrip(".")
    return token or "0"
