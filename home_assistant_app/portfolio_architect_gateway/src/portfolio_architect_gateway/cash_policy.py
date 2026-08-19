"""Provider-owned authorization policy for investment cash."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any, Final

from .errors import ProtocolError
from .store import load_json_state, save_json_state

MODE_ALL_AVAILABLE: Final = "all_available"
MODE_CAPPED: Final = "capped"
MODE_RETAIN: Final = "retain"
SUPPORTED_MODES: Final = frozenset({MODE_ALL_AVAILABLE, MODE_CAPPED, MODE_RETAIN})
MAX_CASH_EUR: Final = Decimal("1000000000")
_EUR_RE = re.compile(r"^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,2})?$")


@dataclass(frozen=True, slots=True)
class InvestmentCashPolicy:
    """One validated Gateway-side authorization policy."""

    mode: str = MODE_ALL_AVAILABLE
    cap_eur: Decimal | None = None
    retain_eur: Decimal | None = None

    def __post_init__(self) -> None:
        if self.mode not in SUPPORTED_MODES:
            raise ProtocolError("Investment cash policy mode is invalid")
        if self.mode == MODE_ALL_AVAILABLE:
            if self.cap_eur is not None or self.retain_eur is not None:
                raise ProtocolError("All-available investment cash policy must not define an amount")
            return
        if self.mode == MODE_CAPPED:
            if self.cap_eur is None or self.retain_eur is not None:
                raise ProtocolError("Capped investment cash policy requires only a cap")
            _validate_amount(self.cap_eur, field="Investment cash cap")
            return
        if self.retain_eur is None or self.cap_eur is not None:
            raise ProtocolError("Retained-cash investment policy requires only a retained amount")
        _validate_amount(self.retain_eur, field="Investment cash retained amount")

    def authorize(self, eligible_eur: Decimal) -> Decimal:
        """Return the amount that Portfolio Architect is allowed to allocate."""
        _validate_amount(eligible_eur, field="Eligible investment cash")
        if self.mode == MODE_ALL_AVAILABLE:
            return eligible_eur
        if self.mode == MODE_CAPPED:
            assert self.cap_eur is not None
            return min(eligible_eur, self.cap_eur)
        assert self.retain_eur is not None
        return max(Decimal("0"), eligible_eur - self.retain_eur)

    def as_dict(self) -> dict[str, Any]:
        # Schema 2 is required only for the new retained-cash mode. Existing
        # all-available/capped saves intentionally stay on schema 1, preserving
        # a clean rollback path to pre-1.35.2 Gateway packages.
        data: dict[str, Any] = {
            "schema_version": 2 if self.mode == MODE_RETAIN else 1,
            "mode": self.mode,
        }
        if self.cap_eur is not None:
            data["cap_eur"] = _canonical_amount(self.cap_eur)
        if self.retain_eur is not None:
            data["retain_eur"] = _canonical_amount(self.retain_eur)
        return data


def load_investment_cash_policy(path: Path) -> InvestmentCashPolicy:
    """Load one policy; absence preserves the pre-v1.19 all-available behavior."""
    raw = load_json_state(path)
    if raw is None:
        return InvestmentCashPolicy()
    schema = raw.get("schema_version")
    if schema not in {1, 2}:
        raise ProtocolError("Unsupported investment cash policy schema")
    allowed = {"schema_version", "mode", "cap_eur"}
    if schema == 2:
        allowed.add("retain_eur")
    if set(raw) - allowed:
        raise ProtocolError("Investment cash policy contains unsupported fields")
    mode = raw.get("mode")
    supported = {MODE_ALL_AVAILABLE, MODE_CAPPED} if schema == 1 else SUPPORTED_MODES
    if not isinstance(mode, str) or mode not in supported:
        raise ProtocolError("Investment cash policy mode is invalid")
    cap = _parse_optional_canonical_amount(raw.get("cap_eur"), field="Investment cash cap")
    retain = _parse_optional_canonical_amount(raw.get("retain_eur"), field="Investment cash retained amount")
    if mode == MODE_ALL_AVAILABLE:
        if cap is not None or retain is not None:
            if cap is not None and retain is None:
                raise ProtocolError("All-available investment cash policy must not define a cap")
            raise ProtocolError("All-available investment cash policy must not define an amount")
        return InvestmentCashPolicy(mode=mode)
    if mode == MODE_CAPPED:
        if cap is None or retain is not None:
            if cap is None and retain is None:
                raise ProtocolError("Capped investment cash policy requires a canonical EUR cap")
            raise ProtocolError("Capped investment cash policy requires only a canonical EUR cap")
        return InvestmentCashPolicy(mode=mode, cap_eur=cap)
    if retain is None or cap is not None:
        raise ProtocolError("Retained-cash policy requires only a canonical EUR retained amount")
    return InvestmentCashPolicy(mode=mode, retain_eur=retain)


def save_investment_cash_policy(path: Path, policy: InvestmentCashPolicy) -> None:
    """Persist one validated non-secret policy atomically with mode 0600."""
    save_json_state(path, policy.as_dict())


def parse_policy_input(mode: str, cap_eur: str, retain_eur: str = "") -> InvestmentCashPolicy:
    """Validate one bounded Ingress form submission."""
    cleaned_mode = mode.strip()
    if cleaned_mode == MODE_ALL_AVAILABLE:
        # Hidden/disabled browser fields are not trusted as policy input. Ignore stale
        # values and persist the canonical all-available state with no amount fields.
        return InvestmentCashPolicy(mode=MODE_ALL_AVAILABLE)
    if cleaned_mode == MODE_CAPPED:
        cap = _parse_form_amount(cap_eur, label="Cash cap")
        try:
            return InvestmentCashPolicy(mode=MODE_CAPPED, cap_eur=cap)
        except ProtocolError as err:
            raise ValueError(str(err)) from err
    if cleaned_mode == MODE_RETAIN:
        retain = _parse_form_amount(retain_eur, label="Cash reserve")
        try:
            return InvestmentCashPolicy(mode=MODE_RETAIN, retain_eur=retain)
        except ProtocolError as err:
            raise ValueError(str(err)) from err
    raise ValueError("Unknown investment cash policy")


def _parse_optional_canonical_amount(value: Any, *, field: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str) or _EUR_RE.fullmatch(value) is None:
        raise ProtocolError(f"{field} must be a canonical EUR amount")
    try:
        parsed = Decimal(value)
    except InvalidOperation as err:
        raise ProtocolError(f"{field} is invalid") from err
    _validate_amount(parsed, field=field)
    return parsed


def _parse_form_amount(value: str, *, label: str) -> Decimal:
    """Parse a bounded human EUR amount while keeping persisted state canonical.

    The Ingress UI is intentionally locale-tolerant: comma or dot may be the
    decimal separator, while comma, dot, spaces or apostrophes may group thousands.
    Ambiguous single punctuation with exactly three trailing digits is treated as a
    thousands separator because cash-policy amounts support at most two decimals.
    """
    token = value.strip()
    try:
        canonical = _canonicalize_form_amount(token)
        parsed = Decimal(canonical)
    except (InvalidOperation, ValueError) as err:
        raise ValueError(
            f"{label} must be a non-negative EUR amount with at most two decimals"
        ) from err
    try:
        _validate_amount(parsed, field=label)
    except ProtocolError as err:
        raise ValueError(str(err)) from err
    return parsed


def _canonicalize_form_amount(token: str) -> str:
    if not token:
        raise ValueError("empty amount")
    normalized = token.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2019", "'")
    allowed = set("0123456789., '")
    if any(char not in allowed for char in normalized):
        raise ValueError("unsupported amount character")

    dot_count = normalized.count(".")
    comma_count = normalized.count(",")
    decimal_sep: str | None = None
    if dot_count and comma_count:
        decimal_sep = "." if normalized.rfind(".") > normalized.rfind(",") else ","
        if normalized.count(decimal_sep) != 1:
            raise ValueError("repeated decimal separator")
    elif dot_count == 1:
        trailing = len(normalized) - normalized.rfind(".") - 1
        if trailing in {1, 2}:
            decimal_sep = "."
    elif comma_count == 1:
        trailing = len(normalized) - normalized.rfind(",") - 1
        if trailing in {1, 2}:
            decimal_sep = ","

    if decimal_sep is None:
        integer_part = normalized
        fraction = ""
    else:
        integer_part, fraction = normalized.rsplit(decimal_sep, 1)
        if not fraction or len(fraction) > 2 or not fraction.isdigit():
            raise ValueError("invalid fractional part")
        if decimal_sep in integer_part:
            raise ValueError("decimal separator reused as grouping")

    digits = _ungroup_integer(integer_part, decimal_sep=decimal_sep)
    return digits + (("." + fraction) if fraction else "")


def _ungroup_integer(value: str, *, decimal_sep: str | None) -> str:
    if not value:
        raise ValueError("missing integer part")
    grouping_candidates = {".", ",", " ", "'"}
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


def _validate_amount(value: Decimal, *, field: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0 or value > MAX_CASH_EUR:
        raise ProtocolError(f"{field} must be a finite non-negative EUR amount")


def _canonical_amount(value: Decimal) -> str:
    _validate_amount(value, field="Investment cash amount")
    token = format(value, "f")
    if "." in token:
        token = token.rstrip("0").rstrip(".")
    return token or "0"
