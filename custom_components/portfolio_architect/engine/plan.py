"""Validated UI plan overrides for the calculation engine."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Any

D = Decimal
_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")
_WKN_RE = re.compile(r"^[A-Z0-9]{5,16}$")
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_MAX_NAME_LENGTH = 160
_MAX_INSTRUMENTS = 32
_MAX_BUDGET = D("10000000")
_BUDGET_BASES = {"per_period", "per_execution"}
_FREQUENCIES = {"weekly", "monthly", "quarterly", "yearly"}


@dataclass(frozen=True, slots=True)
class PlanRuntime:
    """Canonical plan values exposed through the stable payload."""

    name: str
    configuration_source: str
    budget_amount_eur: Decimal
    budget_basis: str
    frequency: str
    executions_per_period: int
    contribution_per_execution_eur: Decimal


def apply_plan_override(
    portfolio_document: dict[str, Any],
    override: dict[str, Any] | None,
) -> tuple[dict[str, Any], PlanRuntime]:
    """Apply an optional validated UI plan to a copy of ``portfolio_document``."""
    document = deepcopy(portfolio_document)
    portfolio = document.get("portfolio")
    if not isinstance(portfolio, dict):
        raise ValueError("portfolio.yaml is missing the portfolio mapping")

    base_name = _bounded_text(portfolio.get("name", "Investment plan"), "plan name")
    base_amount = _money(portfolio.get("monthly_contribution"), "monthly_contribution")

    if not override or not override.get("enabled"):
        runtime = PlanRuntime(
            name=base_name,
            configuration_source="yaml",
            budget_amount_eur=base_amount,
            budget_basis="per_period",
            frequency="monthly",
            executions_per_period=1,
            contribution_per_execution_eur=base_amount,
        )
        return document, runtime

    name = _bounded_text(override.get("name", base_name), "plan name")
    budget_amount = _money(override.get("budget_amount_eur"), "plan budget")
    budget_basis = override.get("budget_basis")
    if budget_basis not in _BUDGET_BASES:
        raise ValueError("plan budget basis is invalid")
    frequency = override.get("frequency")
    if frequency not in _FREQUENCIES:
        raise ValueError("plan frequency is invalid")
    executions = _positive_int(
        override.get("executions_per_period"),
        "executions_per_period",
        maximum=28,
    )
    contribution = (
        budget_amount
        if budget_basis == "per_execution"
        else budget_amount / D(executions)
    ).quantize(D("0.01"))
    if contribution <= 0:
        raise ValueError("contribution per execution must be positive")

    instruments = _validate_instruments(override.get("instruments"))
    portfolio["name"] = name
    portfolio["monthly_contribution"] = contribution
    portfolio["allocation"] = instruments

    runtime = PlanRuntime(
        name=name,
        configuration_source="ui",
        budget_amount_eur=budget_amount,
        budget_basis=budget_basis,
        frequency=frequency,
        executions_per_period=executions,
        contribution_per_execution_eur=contribution,
    )
    return document, runtime


def _validate_instruments(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("at least one plan instrument is required")
    if len(raw) > _MAX_INSTRUMENTS:
        raise ValueError(f"plan may contain at most {_MAX_INSTRUMENTS} instruments")

    seen_ids: set[str] = set()
    seen_wkns: set[str] = set()
    seen_isins: set[str] = set()
    result: list[dict[str, Any]] = []
    target_sum = D("0")

    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            raise ValueError(f"plan instrument {index} must be an object")
        fund_id = str(value.get("id", "")).strip()
        if _ID_RE.fullmatch(fund_id) is None or fund_id in seen_ids:
            raise ValueError(f"plan instrument {index} has an invalid or duplicate id")
        seen_ids.add(fund_id)

        wkn = str(value.get("wkn", "")).strip().upper()
        isin = str(value.get("isin", "")).strip().upper()
        if _WKN_RE.fullmatch(wkn) is None or wkn in seen_wkns:
            raise ValueError(f"plan instrument {index} has an invalid or duplicate WKN")
        if _ISIN_RE.fullmatch(isin) is None or isin in seen_isins:
            raise ValueError(f"plan instrument {index} has an invalid or duplicate ISIN")
        seen_wkns.add(wkn)
        seen_isins.add(isin)

        name = _bounded_text(value.get("name"), f"plan instrument {index} name")
        target = D(str(value.get("target_pct")))
        if not target.is_finite() or target <= 0 or target > 100:
            raise ValueError(f"plan instrument {index} target must be above 0 and at most 100")
        buy_enabled = value.get("buy_enabled", True)
        if not isinstance(buy_enabled, bool):
            raise ValueError(f"plan instrument {index} buy_enabled must be boolean")

        target_sum += target
        result.append(
            {
                "id": fund_id,
                "wkn": wkn,
                "isin": isin,
                "name": name,
                "target_pct": target,
                "buy_enabled": buy_enabled,
            }
        )

    if target_sum != D("100"):
        raise ValueError(f"plan target weights must sum to 100%, got {target_sum}%")
    if not any(item["buy_enabled"] for item in result):
        raise ValueError("at least one plan instrument must be enabled for purchases")
    return result


def _bounded_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    cleaned = value.strip()
    if (
        not cleaned
        or len(cleaned) > _MAX_NAME_LENGTH
        or any(ord(character) < 32 for character in cleaned)
    ):
        raise ValueError(f"{field} is empty, too long, or contains control characters")
    return cleaned


def _money(value: object, field: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        amount = D(str(value))
    except Exception as err:  # Decimal raises several input-specific exceptions.
        raise ValueError(f"{field} must be numeric") from err
    if not amount.is_finite() or amount <= 0 or amount > _MAX_BUDGET:
        raise ValueError(f"{field} must be positive and at most {_MAX_BUDGET}")
    return amount.quantize(D("0.01"))


def _positive_int(value: object, field: str, *, maximum: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{field} must be an integer") from err
    if not 1 <= parsed <= maximum:
        raise ValueError(f"{field} must be between 1 and {maximum}")
    return parsed
