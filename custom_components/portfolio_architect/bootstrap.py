"""Integration-owned first-run initialization for Portfolio Architect.

The bootstrap layer intentionally owns only service lifecycle and local configuration
material. Gateway Apps never create or modify Portfolio Architect configuration.
A newly initialized entry may therefore exist without a source and without an
investment plan; both states are explicit and fail closed until the user completes
setup through the integration's Configure flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Any

import yaml

from .engine.calculator import calculate_portfolio_payload_from_positions, validate_configuration_source
from .engine.models import Position
from .engine.targets import generate_target_id
REQUIRED_CONFIGURATION_FILES = (
    "portfolio.yaml",
    "policy.yaml",
    "instruments.yaml",
    "broker.yaml",
)

_MAX_BOOTSTRAP_FILE_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class BootstrapInstrument:
    """One explicitly configured target plus its policy metadata."""

    position: Position
    target_pct: Decimal
    buy_enabled: bool
    ucits: bool
    domicile: str
    distribution: str
    fund_currency: str
    ter_pct: Decimal
    fund_size_eur: Decimal
    metadata_source: str


@dataclass(frozen=True, slots=True)
class BootstrapPlan:
    """Complete user-supplied initial plan and policy configuration."""

    name: str
    budget_amount_eur: Decimal
    corridor_pp: Decimal
    minimum_trade_eur: Decimal
    rounding_step_eur: Decimal
    instruments: tuple[BootstrapInstrument, ...]
    ucits_required: bool
    accumulating_preferred: bool
    ireland_preferred: bool
    max_ter_pct: Decimal
    minimum_fund_size_eur: Decimal
    savings_plan_required: bool
    free_savings_plan_preferred: bool


def configuration_complete(config_directory: Path) -> bool:
    """Return whether the established four-file engine configuration is complete."""
    try:
        validate_configuration_source(config_directory)
    except (OSError, ValueError):
        return False
    return True


def configuration_state(config_directory: Path) -> str:
    """Return ``missing``, ``empty``, ``partial`` or ``configured``."""
    if not config_directory.exists():
        return "missing"
    if not config_directory.is_dir():
        return "partial"
    present = {name for name in REQUIRED_CONFIGURATION_FILES if (config_directory / name).is_file()}
    if len(present) == len(REQUIRED_CONFIGURATION_FILES):
        return "configured"
    try:
        any_entries = any(config_directory.iterdir())
    except OSError:
        return "partial"
    if not present and not any_entries:
        return "empty"
    return "partial"


def initialize_configuration_directory(config_directory: Path) -> str:
    """Create an empty PA-owned directory or validate an existing one safely.

    Existing complete configurations are preserved. A partially populated directory
    is never rewritten or guessed because that could destroy an advanced user's
    configuration or silently reinterpret incomplete state.
    """
    state = configuration_state(config_directory)
    if state == "missing":
        config_directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        state = configuration_state(config_directory)
    if state not in {"empty", "configured"}:
        raise ValueError(
            "Portfolio configuration directory is partially populated; complete or move it before initialization"
        )
    if state == "configured" and not configuration_complete(config_directory):
        raise ValueError(
            "Existing Portfolio Architect configuration is complete in shape but invalid"
        )
    return state


def _safe_dump(document: dict[str, Any]) -> bytes:
    body = yaml.safe_dump(
        document,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).encode("utf-8")
    if not body or len(body) > _MAX_BOOTSTRAP_FILE_BYTES:
        raise ValueError("Generated bootstrap configuration exceeds the supported size")
    return body


def _portfolio_id(name: str) -> str:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
    return f"portfolio_{digest}"


def build_configuration_documents(plan: BootstrapPlan) -> dict[str, dict[str, Any]]:
    """Build the four established engine documents from explicit user inputs."""
    if not plan.instruments:
        raise ValueError("At least one target instrument is required")
    total = sum((item.target_pct for item in plan.instruments), Decimal("0"))
    if total != Decimal("100"):
        raise ValueError("Initial target weights must sum to 100")

    used_target_ids: set[str] = set()
    allocation: list[dict[str, Any]] = []
    metadata: dict[str, dict[str, Any]] = {}
    for item in plan.instruments:
        isin = str(item.position.isin or "").strip().upper()
        if len(isin) != 12:
            raise ValueError("Initial plan targets require a valid ISIN")
        target_id = generate_target_id(used_target_ids)
        used_target_ids.add(target_id)
        allocation.append(
            {
                "target_id": target_id,
                "name": item.position.name,
                "wkn": str(item.position.wkn or "").strip().upper(),
                "isin": isin,
                "target_pct": float(item.target_pct),
                "buy_enabled": item.buy_enabled,
            }
        )
        metadata[isin] = {
            "ucits": item.ucits,
            "domicile": item.domicile,
            "distribution": item.distribution,
            "fund_currency": item.fund_currency,
            "ter_pct": float(item.ter_pct),
            "fund_size_eur": float(item.fund_size_eur),
            "metadata_status": "user_confirmed",
            "metadata_source": item.metadata_source,
        }

    today = date.today().isoformat()
    return {
        "portfolio.yaml": {
            "schema_version": 2,
            "portfolio": {
                "id": _portfolio_id(plan.name),
                "name": plan.name,
                "currency": "EUR",
                "strategy": "buy_only",
                "monthly_contribution": float(plan.budget_amount_eur),
                "allocation": allocation,
            },
            "rebalancing": {
                "corridor_pp": float(plan.corridor_pp),
                "minimum_trade": float(plan.minimum_trade_eur),
                "rounding_step": float(plan.rounding_step_eur),
            },
        },
        "policy.yaml": {
            "schema_version": 1,
            "policy": {
                "id": "portfolio_architect_native_setup",
                "name": "Portfolio Architect native setup policy",
                "rules": {
                    "ucits_required": plan.ucits_required,
                    "accumulating_preferred": plan.accumulating_preferred,
                    "ireland_preferred": plan.ireland_preferred,
                    "max_ter_pct": float(plan.max_ter_pct),
                    "minimum_fund_size_eur": float(plan.minimum_fund_size_eur),
                    "savings_plan_required": plan.savings_plan_required,
                    "free_savings_plan_preferred": plan.free_savings_plan_preferred,
                    "allowed_portfolio_currency": ["EUR"],
                },
                "severities": {
                    "ucits_required": "error",
                    "accumulating_preferred": "warning",
                    "ireland_preferred": "warning",
                    "max_ter_pct": "warning",
                    "minimum_fund_size_eur": "warning",
                    "savings_plan_required": "error",
                    "free_savings_plan_preferred": "info",
                },
            },
        },
        "instruments.yaml": {
            "schema_version": 1,
            "as_of": today,
            "valuation_currency": "EUR",
            "instruments": metadata,
        },
        # Provider-aware schema 3 deliberately starts with no invented execution
        # venue. Users can add evidence-backed execution providers later through
        # the native broker editor. The engine treats an empty provider map as an
        # explicit route-unavailable state rather than inventing fees or venues.
        "broker.yaml": {
            "schema_version": 3,
            "fee_data_max_age_days": 30,
            "providers": {},
            "funding_transfers": [],
        },
    }


def write_initial_configuration(
    config_directory: Path,
    documents: dict[str, dict[str, Any]],
    *,
    positions: dict[str, Position],
    evaluated_at,
    source_provider: str,
    source_label: str,
    source_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and install a first configuration without overwriting user files.

    The documents are fully validated in a private staging directory before any
    target file is replaced. The destination must contain none of the four required
    files. Ordinary write failures roll back files installed by this call. A crash
    midway remains fail-closed because partial configuration is never considered
    configured by ``configuration_state``.
    """
    if configuration_state(config_directory) not in {"empty"}:
        raise ValueError("Initial setup refuses to overwrite an existing configuration")
    if set(documents) != set(REQUIRED_CONFIGURATION_FILES):
        raise ValueError("Initial setup documents are incomplete")

    config_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pa-bootstrap-", dir=config_directory.parent) as raw_stage:
        stage = Path(raw_stage)
        for name in REQUIRED_CONFIGURATION_FILES:
            (stage / name).write_bytes(_safe_dump(documents[name]))
        payload = calculate_portfolio_payload_from_positions(
            positions,
            stage,
            evaluated_at=evaluated_at,
            source_provider=source_provider,
            source_label=source_label,
            source_metadata=source_metadata,
        )

        installed: list[Path] = []
        try:
            for name in REQUIRED_CONFIGURATION_FILES:
                target = config_directory / name
                if target.exists():
                    raise ValueError(f"Refusing to overwrite existing {name}")
                source = stage / name
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=f".{name}.", dir=config_directory
                )
                temporary = Path(temporary_name)
                try:
                    os.fchmod(descriptor, 0o600)
                    with os.fdopen(descriptor, "wb", closefd=True) as handle:
                        handle.write(source.read_bytes())
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary, target)
                    installed.append(target)
                finally:
                    try:
                        temporary.unlink()
                    except FileNotFoundError:
                        pass
            try:
                directory_fd = os.open(config_directory, os.O_RDONLY)
            except OSError:
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except Exception:
            for target in reversed(installed):
                try:
                    target.unlink()
                except OSError:
                    pass
            raise
    return payload


__all__ = [
    "BootstrapInstrument",
    "BootstrapPlan",
    "REQUIRED_CONFIGURATION_FILES",
    "build_configuration_documents",
    "configuration_complete",
    "configuration_state",
    "initialize_configuration_directory",
    "write_initial_configuration",
]
