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
SUPPORTED_MODES: Final = frozenset({MODE_ALL_AVAILABLE, MODE_CAPPED})
MAX_CASH_EUR: Final = Decimal("1000000000")
_EUR_RE = re.compile(r"^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,2})?$")


@dataclass(frozen=True, slots=True)
class InvestmentCashPolicy:
    """One validated Gateway-side authorization policy."""

    mode: str = MODE_ALL_AVAILABLE
    cap_eur: Decimal | None = None

    def __post_init__(self) -> None:
        if self.mode not in SUPPORTED_MODES:
            raise ProtocolError("Investment cash policy mode is invalid")
        if self.mode == MODE_ALL_AVAILABLE:
            if self.cap_eur is not None:
                raise ProtocolError("All-available investment cash policy must not define a cap")
            return
        if self.cap_eur is None:
            raise ProtocolError("Capped investment cash policy requires a cap")
        _validate_amount(self.cap_eur, field="Investment cash cap")

    def authorize(self, eligible_eur: Decimal) -> Decimal:
        """Return the amount that Portfolio Architect is allowed to allocate."""
        _validate_amount(eligible_eur, field="Eligible investment cash")
        if self.mode == MODE_ALL_AVAILABLE:
            return eligible_eur
        assert self.cap_eur is not None
        return min(eligible_eur, self.cap_eur)

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"schema_version": 1, "mode": self.mode}
        if self.cap_eur is not None:
            data["cap_eur"] = _canonical_amount(self.cap_eur)
        return data


def load_investment_cash_policy(path: Path) -> InvestmentCashPolicy:
    """Load one policy; absence preserves the pre-v1.19 all-available behavior."""
    raw = load_json_state(path)
    if raw is None:
        return InvestmentCashPolicy()
    if raw.get("schema_version") != 1:
        raise ProtocolError("Unsupported investment cash policy schema")
    allowed = {"schema_version", "mode", "cap_eur"}
    if set(raw) - allowed:
        raise ProtocolError("Investment cash policy contains unsupported fields")
    mode = raw.get("mode")
    if not isinstance(mode, str) or mode not in SUPPORTED_MODES:
        raise ProtocolError("Investment cash policy mode is invalid")
    cap_raw = raw.get("cap_eur")
    if mode == MODE_ALL_AVAILABLE:
        if cap_raw is not None:
            raise ProtocolError("All-available investment cash policy must not define a cap")
        return InvestmentCashPolicy(mode=mode)
    if not isinstance(cap_raw, str) or _EUR_RE.fullmatch(cap_raw) is None:
        raise ProtocolError("Capped investment cash policy requires a canonical EUR cap")
    try:
        cap = Decimal(cap_raw)
    except InvalidOperation as err:
        raise ProtocolError("Investment cash policy cap is invalid") from err
    return InvestmentCashPolicy(mode=mode, cap_eur=cap)


def save_investment_cash_policy(path: Path, policy: InvestmentCashPolicy) -> None:
    """Persist one validated non-secret policy atomically with mode 0600."""
    save_json_state(path, policy.as_dict())


def parse_policy_input(mode: str, cap_eur: str) -> InvestmentCashPolicy:
    """Validate one bounded Ingress form submission."""
    cleaned_mode = mode.strip()
    if cleaned_mode == MODE_ALL_AVAILABLE:
        if cap_eur.strip():
            raise ValueError("All-available policy must not include a cap")
        return InvestmentCashPolicy(mode=MODE_ALL_AVAILABLE)
    if cleaned_mode != MODE_CAPPED:
        raise ValueError("Unknown investment cash policy")
    token = cap_eur.strip()
    if _EUR_RE.fullmatch(token) is None:
        raise ValueError("Cash cap must be a canonical EUR amount with at most two decimals")
    try:
        cap = Decimal(token)
    except InvalidOperation as err:
        raise ValueError("Cash cap is invalid") from err
    try:
        return InvestmentCashPolicy(mode=MODE_CAPPED, cap_eur=cap)
    except ProtocolError as err:
        raise ValueError(str(err)) from err


def _validate_amount(value: Decimal, *, field: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0 or value > MAX_CASH_EUR:
        raise ProtocolError(f"{field} must be a finite non-negative EUR amount")


def _canonical_amount(value: Decimal) -> str:
    _validate_amount(value, field="Investment cash amount")
    token = format(value, "f")
    if "." in token:
        token = token.rstrip("0").rstrip(".")
    return token or "0"
