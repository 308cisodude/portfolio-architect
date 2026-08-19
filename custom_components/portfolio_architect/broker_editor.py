"""Bounded native editor support for provider-aware broker configuration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Final

import yaml

from .engine.execution import execution_providers
from .engine.funding import funding_transfers
from .engine.io import load_yaml

_MAX_BROKER_FILE_BYTES: Final = 1024 * 1024
_PROVIDER_ID_RE: Final = re.compile(r"^[a-z0-9_]{1,32}$")
_ISIN_RE: Final = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
TIE_BREAK_PREFERRED: Final = "preferred"
TIE_BREAK_NEUTRAL: Final = "neutral"
TIE_BREAK_FALLBACK: Final = "fallback"
TIE_BREAK_MODES: Final = (
    TIE_BREAK_PREFERRED,
    TIE_BREAK_NEUTRAL,
    TIE_BREAK_FALLBACK,
)
_UI_PRIORITY = {
    TIE_BREAK_PREFERRED: 50,
    TIE_BREAK_NEUTRAL: None,
    TIE_BREAK_FALLBACK: 150,
}


@dataclass(frozen=True, slots=True)
class BrokerEditorContext:
    """One validated editable broker document and its path."""

    path: Path
    document: dict[str, Any]


def load_broker_editor_context(config_directory: Path) -> BrokerEditorContext:
    """Load and validate a provider-aware broker document for native editing."""

    path = config_directory / "broker.yaml"
    document = load_yaml(path)
    _validate_editable_document(document)
    return BrokerEditorContext(path=path, document=deepcopy(document))


def _validate_editable_document(document: dict[str, Any]) -> None:
    schema = document.get("schema_version")
    if schema not in {2, 3}:
        raise ValueError("native broker editor requires broker schema 2 or 3")
    execution_providers(document, evaluated_on=date.today())
    if schema == 3:
        funding_transfers(document)


def tie_break_mode(provider: dict[str, Any]) -> str:
    """Map advanced numeric YAML priority to a simple native UI preference."""

    value = provider.get("priority")
    if value is None or value == 100:
        return TIE_BREAK_NEUTRAL
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("provider priority is invalid")
    return TIE_BREAK_PREFERRED if value < 100 else TIE_BREAK_FALLBACK


def set_general_settings(document: dict[str, Any], *, fee_data_max_age_days: int) -> dict[str, Any]:
    updated = deepcopy(document)
    updated["fee_data_max_age_days"] = fee_data_max_age_days
    _validate_editable_document(updated)
    return updated


def upsert_provider(
    document: dict[str, Any],
    *,
    provider_id: str,
    name: str,
    source: str,
    as_of: str,
    tie_break: str,
    create: bool,
) -> dict[str, Any]:
    """Add or edit one provider while preserving its route profiles."""

    provider_id = provider_id.strip()
    if _PROVIDER_ID_RE.fullmatch(provider_id) is None:
        raise ValueError("provider id is invalid")
    if tie_break not in TIE_BREAK_MODES:
        raise ValueError("tie-break preference is invalid")
    try:
        parsed_date = date.fromisoformat(as_of.strip())
    except ValueError as err:
        raise ValueError("provider evidence date is invalid") from err
    if parsed_date > date.today():
        raise ValueError("provider evidence date is in the future")

    updated = deepcopy(document)
    providers = updated.get("providers")
    if not isinstance(providers, dict):
        raise ValueError("providers map is invalid")
    exists = provider_id in providers
    if create and exists:
        raise ValueError("provider already exists")
    if not create and not exists:
        raise ValueError("provider does not exist")
    existing = deepcopy(providers.get(provider_id) or {})
    existing["name"] = name.strip()
    existing["source"] = source.strip()
    existing["as_of"] = parsed_date.isoformat()
    # Editing unrelated evidence must not silently renumber an advanced numeric
    # priority already present in YAML. Preserve it when the user leaves the
    # derived preference tier unchanged; normalize only when the tier changes.
    preserve_priority = not create and tie_break_mode(existing) == tie_break
    if not preserve_priority:
        priority = _UI_PRIORITY[tie_break]
        if priority is None:
            existing.pop("priority", None)
        else:
            existing["priority"] = priority
    existing.setdefault("savings_plans", {})
    providers[provider_id] = existing
    _validate_editable_document(updated)
    return updated


def remove_provider(document: dict[str, Any], *, provider_id: str) -> dict[str, Any]:
    updated = deepcopy(document)
    providers = updated.get("providers")
    if not isinstance(providers, dict) or provider_id not in providers:
        raise ValueError("provider does not exist")
    if len(providers) <= 1:
        raise ValueError("at least one execution provider is required")
    for edge in updated.get("funding_transfers", []) or []:
        if isinstance(edge, dict) and provider_id in {
            edge.get("from_provider"),
            edge.get("to_provider"),
        }:
            raise ValueError("remove funding transfers that reference the provider first")
    del providers[provider_id]
    _validate_editable_document(updated)
    return updated


def upsert_savings_plan(
    document: dict[str, Any],
    *,
    provider_id: str,
    isin: str,
    available: bool,
    fee_pct: float | None,
    promotional: bool,
    status: str,
    create: bool,
) -> dict[str, Any]:
    """Add or edit one explicit per-provider savings-plan route."""

    canonical_isin = isin.strip().upper()
    if _ISIN_RE.fullmatch(canonical_isin) is None:
        raise ValueError("savings-plan ISIN is invalid")
    if not isinstance(promotional, bool):
        raise ValueError("promotional must be boolean")
    updated = deepcopy(document)
    providers = updated.get("providers")
    provider = providers.get(provider_id) if isinstance(providers, dict) else None
    if not isinstance(provider, dict):
        raise ValueError("provider does not exist")
    plans = provider.setdefault("savings_plans", {})
    if not isinstance(plans, dict):
        raise ValueError("provider savings plans are invalid")
    exists = canonical_isin in plans
    if create and exists:
        raise ValueError("savings-plan route already exists")
    if not create and not exists:
        raise ValueError("savings-plan route does not exist")
    route: dict[str, Any] = {
        "available": bool(available),
        "promotional": promotional,
    }
    if available:
        if fee_pct is None:
            raise ValueError("available savings plan requires fee")
        route["fee_pct"] = float(fee_pct)
    if status.strip():
        route["status"] = status.strip()
    plans[canonical_isin] = route
    _validate_editable_document(updated)
    return updated


def remove_savings_plan(document: dict[str, Any], *, provider_id: str, isin: str) -> dict[str, Any]:
    updated = deepcopy(document)
    providers = updated.get("providers")
    provider = providers.get(provider_id) if isinstance(providers, dict) else None
    plans = provider.get("savings_plans") if isinstance(provider, dict) else None
    if not isinstance(plans, dict) or isin not in plans:
        raise ValueError("savings-plan route does not exist")
    del plans[isin]
    _validate_editable_document(updated)
    return updated


def add_funding_transfer(
    document: dict[str, Any],
    *,
    from_provider: str,
    to_provider: str,
    fee_eur: float,
    settlement_business_days: int,
) -> dict[str, Any]:
    """Add one exact directed transfer edge and opt into schema 3 when needed."""

    updated = deepcopy(document)
    updated["schema_version"] = 3
    edges = updated.setdefault("funding_transfers", [])
    if not isinstance(edges, list):
        raise ValueError("funding transfer list is invalid")
    if any(
        isinstance(edge, dict)
        and edge.get("from_provider") == from_provider
        and edge.get("to_provider") == to_provider
        for edge in edges
    ):
        raise ValueError("funding transfer already exists")
    edges.append(
        {
            "from_provider": from_provider,
            "to_provider": to_provider,
            "fee_eur": float(fee_eur),
            "settlement_business_days": int(settlement_business_days),
        }
    )
    _validate_editable_document(updated)
    return updated


def remove_funding_transfer(
    document: dict[str, Any], *, from_provider: str, to_provider: str
) -> dict[str, Any]:
    updated = deepcopy(document)
    if updated.get("schema_version") != 3:
        raise ValueError("funding topology is not enabled")
    edges = updated.get("funding_transfers")
    if not isinstance(edges, list):
        raise ValueError("funding transfer list is invalid")
    before = len(edges)
    updated["funding_transfers"] = [
        edge
        for edge in edges
        if not (
            isinstance(edge, dict)
            and edge.get("from_provider") == from_provider
            and edge.get("to_provider") == to_provider
        )
    ]
    if len(updated["funding_transfers"]) == before:
        raise ValueError("funding transfer does not exist")
    _validate_editable_document(updated)
    return updated


def write_broker_document_atomic(path: Path, document: dict[str, Any]) -> None:
    """Validate and atomically replace broker.yaml while preserving its file mode."""

    _validate_editable_document(document)
    body = yaml.safe_dump(
        document,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).encode("utf-8")
    if not body or len(body) > _MAX_BROKER_FILE_BYTES:
        raise ValueError("broker document exceeds the supported size")
    mode = path.stat().st_mode & 0o777
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
