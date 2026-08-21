"""Bounded presentation-only execution instructions for the next decided plan.

The engine and parsed payload already decide which instruments to buy, where to
execute them, and which provider-scoped cash pool funds each purchase.  This
module does not rerun route selection.  It only normalizes that decided plan
into a small machine-readable step list plus English/German display strings for
native Home Assistant presentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable

EXECUTION_PATH_SCHEMA_VERSION = 1
EXECUTION_PATH_MODES = frozenset({"local_cash", "transfer", "mixed", "purchase_only"})
_MAX_EXECUTION_PATH_STEPS = 80
_MONEY_QUANTUM = Decimal("0.01")
_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class ExecutionPathPresentation:
    """Normalized already-decided execution path for Home Assistant presentation."""

    mode: str
    steps: tuple[dict[str, Any], ...]
    instruction: str
    instruction_de: str
    markdown: str
    markdown_de: str


def _money(value: Any) -> Decimal:
    """Return one safe two-decimal monetary value from validated model input."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as err:
        raise ValueError("execution-path money value is invalid") from err
    if not amount.is_finite() or amount < 0:
        raise ValueError("execution-path money value is invalid")
    return amount.quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _eur_en(value: Any) -> str:
    return f"€{_money(value):,.2f}"


def _eur_de(value: Any) -> str:
    text = f"{_money(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} €"


def _settlement_en(days: int) -> str:
    if days == 0:
        return "same business day"
    if days == 1:
        return "in 1 business day"
    return f"in {days} business days"


def _settlement_de(days: int) -> str:
    if days == 0:
        return "am selben Geschäftstag"
    if days == 1:
        return "in 1 Geschäftstag"
    return f"in {days} Geschäftstagen"


def _route_en(route: str) -> str | None:
    if route in {"free_savings_plan", "paid_savings_plan"}:
        return "savings plan"
    if route == "manual_order":
        return "manual order"
    return None


def _route_de(route: str) -> str | None:
    if route in {"free_savings_plan", "paid_savings_plan"}:
        return "Sparplan"
    if route == "manual_order":
        return "Einzelorder"
    return None


def _markdown_escape(value: str) -> str:
    """Escape bounded local labels before inserting them into Markdown text."""
    escaped = value.replace("\\", "\\\\")
    for token in ("`", "*", "_", "[", "]", "(", ")", "#", ">"):
        escaped = escaped.replace(token, f"\\{token}")
    return escaped


def _purchase_positions(positions: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(
        position
        for position in positions
        if bool(getattr(position, "buy_enabled", False))
        and not bool(getattr(position, "deferred", False))
        and _money(getattr(position, "proposed_buy_eur", 0)) > _ZERO
    )


def _provider_name(position: Any, *, funding: bool) -> str | None:
    if funding:
        return getattr(position, "funding_provider_name", None) or getattr(
            position, "funding_provider", None
        )
    return getattr(position, "execution_provider_name", None) or getattr(
        position, "execution_provider", None
    )


def _local_cash_steps(purchases: tuple[Any, ...]) -> tuple[dict[str, Any], ...]:
    """Aggregate already-decided same-provider cash requirements by provider."""
    by_provider: dict[str, dict[str, Any]] = {}
    for position in purchases:
        provider_id = getattr(position, "funding_provider", None)
        if provider_id is None or bool(getattr(position, "funding_transfer_required", False)):
            continue
        amount = _money(getattr(position, "estimated_cash_outlay_eur", 0))
        if amount <= _ZERO:
            amount = _money(getattr(position, "proposed_buy_eur", 0)) + _money(
                getattr(position, "estimated_fee_eur", 0)
            )
        existing = by_provider.get(provider_id)
        if existing is None:
            by_provider[provider_id] = {
                "action": "use_local_cash",
                "provider_id": provider_id,
                "provider_name": _provider_name(position, funding=True) or provider_id,
                "amount_eur": float(amount),
            }
        else:
            existing["amount_eur"] = float(_money(existing["amount_eur"]) + amount)
    return tuple(by_provider.values())


def _transfer_steps(plan: Any) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "action": "funding_transfer",
            "from_provider": item.from_provider,
            "from_provider_name": item.from_provider_name,
            "to_provider": item.to_provider,
            "to_provider_name": item.to_provider_name,
            "amount_eur": float(_money(item.amount_eur)),
            "fee_eur": float(_money(item.fee_eur)),
            "settlement_business_days": int(item.settlement_business_days),
        }
        for item in getattr(plan, "funding_transfers", ())
    )


def _purchase_steps(purchases: tuple[Any, ...]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for position in purchases:
        funding_provider = getattr(position, "funding_provider", None)
        execution_provider = getattr(position, "execution_provider", None)
        transfer_required = bool(getattr(position, "funding_transfer_required", False))
        funding_mode = (
            "transfer"
            if transfer_required
            else ("local_cash" if funding_provider is not None else "unscoped")
        )
        result.append(
            {
                "action": "purchase",
                "fund_id": position.fund_id,
                "isin": position.isin,
                "instrument_name": position.name,
                "amount_eur": float(_money(position.proposed_buy_eur)),
                "execution_route": position.execution_route,
                "execution_provider": execution_provider,
                "execution_provider_name": _provider_name(position, funding=False),
                "execution_fee_eur": float(_money(position.estimated_fee_eur)),
                "funding_mode": funding_mode,
                "funding_provider": funding_provider,
                "funding_provider_name": _provider_name(position, funding=True),
            }
        )
    return tuple(result)


def _mode(*, transfers: tuple[dict[str, Any], ...], local: tuple[dict[str, Any], ...], purchases: tuple[dict[str, Any], ...]) -> str:
    has_unscoped = any(item["funding_mode"] == "unscoped" for item in purchases)
    if transfers and (local or has_unscoped):
        return "mixed"
    if transfers:
        return "transfer"
    if local and has_unscoped:
        return "mixed"
    if local:
        return "local_cash"
    return "purchase_only"


def _plain_step(step: dict[str, Any], *, german: bool) -> str:
    action = step["action"]
    if action == "funding_transfer":
        if german:
            return (
                f"{_eur_de(step['amount_eur'])} von {step['from_provider_name']} zu "
                f"{step['to_provider_name']} übertragen; Gebühr {_eur_de(step['fee_eur'])}; "
                f"verfügbar {_settlement_de(step['settlement_business_days'])}."
            )
        return (
            f"Transfer {_eur_en(step['amount_eur'])} from {step['from_provider_name']} to "
            f"{step['to_provider_name']}; fee {_eur_en(step['fee_eur'])}; "
            f"available {_settlement_en(step['settlement_business_days'])}."
        )
    if action == "use_local_cash":
        if german:
            return (
                f"{_eur_de(step['amount_eur'])} bereits verfügbares Guthaben bei "
                f"{step['provider_name']} verwenden."
            )
        return (
            f"Use {_eur_en(step['amount_eur'])} already available at "
            f"{step['provider_name']}."
        )
    if action == "purchase":
        provider = step.get("execution_provider_name")
        route = _route_de(step["execution_route"]) if german else _route_en(step["execution_route"])
        if german:
            where = f" bei {provider}" if provider else ""
            via = f" per {route}" if route else ""
            return (
                f"{_eur_de(step['amount_eur'])} {step['instrument_name']}{where}{via} kaufen; "
                f"ISIN {step['isin']}; Ausführungsgebühr {_eur_de(step['execution_fee_eur'])}."
            )
        where = f" at {provider}" if provider else ""
        via = f" via {route}" if route else ""
        return (
            f"Buy {_eur_en(step['amount_eur'])} of {step['instrument_name']}{where}{via}; "
            f"ISIN {step['isin']}; execution fee {_eur_en(step['execution_fee_eur'])}."
        )
    raise ValueError("execution-path step action is invalid")


def _markdown_step(step: dict[str, Any], *, german: bool) -> str:
    action = step["action"]
    if action == "funding_transfer":
        source = _markdown_escape(str(step["from_provider_name"]))
        destination = _markdown_escape(str(step["to_provider_name"]))
        if german:
            return (
                f"**Übertragen:** {_eur_de(step['amount_eur'])} von {source} zu {destination} · "
                f"Gebühr {_eur_de(step['fee_eur'])} · verfügbar {_settlement_de(step['settlement_business_days'])}"
            )
        return (
            f"**Transfer:** {_eur_en(step['amount_eur'])} from {source} to {destination} · "
            f"fee {_eur_en(step['fee_eur'])} · available {_settlement_en(step['settlement_business_days'])}"
        )
    if action == "use_local_cash":
        provider = _markdown_escape(str(step["provider_name"]))
        if german:
            return f"**Lokales Guthaben verwenden:** {_eur_de(step['amount_eur'])} bereits bei {provider} verfügbar"
        return f"**Use local cash:** {_eur_en(step['amount_eur'])} already available at {provider}"
    if action == "purchase":
        name = _markdown_escape(str(step["instrument_name"]))
        provider_raw = step.get("execution_provider_name")
        provider = _markdown_escape(str(provider_raw)) if provider_raw else None
        route = _route_de(step["execution_route"]) if german else _route_en(step["execution_route"])
        isin = _markdown_escape(str(step["isin"]))
        if german:
            where = f" bei {provider}" if provider else ""
            via = f" per {route}" if route else ""
            return (
                f"**Kaufen:** {_eur_de(step['amount_eur'])} {name}{where}{via} · "
                f"ISIN {isin} · Ausführungsgebühr {_eur_de(step['execution_fee_eur'])}"
            )
        where = f" at {provider}" if provider else ""
        via = f" via {route}" if route else ""
        return (
            f"**Buy:** {_eur_en(step['amount_eur'])} of {name}{where}{via} · "
            f"ISIN {isin} · execution fee {_eur_en(step['execution_fee_eur'])}"
        )
    raise ValueError("execution-path step action is invalid")


def _render_plain(steps: tuple[dict[str, Any], ...], *, german: bool) -> str:
    return "\n".join(
        f"{index}. {_plain_step(step, german=german)}"
        for index, step in enumerate(steps, start=1)
    )


def _render_markdown(steps: tuple[dict[str, Any], ...], *, german: bool) -> str:
    lines = [
        f"{index}. {_markdown_step(step, german=german)}"
        for index, step in enumerate(steps, start=1)
    ]
    lines.extend(
        [
            "",
            (
                "_Nur Empfehlung — Portfolio Architect führt weder Geldtransfers noch Orders aus._"
                if german
                else "_Advisory only — Portfolio Architect does not move cash or place orders._"
            ),
        ]
    )
    return "\n".join(lines)


def build_execution_path(plan: Any, positions: Iterable[Any]) -> ExecutionPathPresentation | None:
    """Return presentation instructions from an already-decided actionable plan.

    The caller owns actionability/freshness gating.  This helper only consumes
    validated plan/recommendation facts; it never calls routing or funding-selection
    code and therefore cannot alter the engine's decision.
    """

    purchases = _purchase_positions(positions)
    if not purchases:
        return None

    transfers = _transfer_steps(plan)
    local = _local_cash_steps(purchases)
    purchase_steps = _purchase_steps(purchases)
    steps = (*transfers, *local, *purchase_steps)
    if not steps or len(steps) > _MAX_EXECUTION_PATH_STEPS:
        raise ValueError("execution path exceeds bounded presentation contract")

    normalized = tuple({"sequence": index, **step} for index, step in enumerate(steps, start=1))
    mode = _mode(transfers=transfers, local=local, purchases=purchase_steps)
    if mode not in EXECUTION_PATH_MODES:
        raise ValueError("execution-path mode is invalid")

    return ExecutionPathPresentation(
        mode=mode,
        steps=normalized,
        instruction=_render_plain(normalized, german=False),
        instruction_de=_render_plain(normalized, german=True),
        markdown=_render_markdown(normalized, german=False),
        markdown_de=_render_markdown(normalized, german=True),
    )
