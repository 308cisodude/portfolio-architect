"""Provider-neutral acquisition-method and capability arbitration state.

Health schema 9 extends the established method-level control plane with bounded
capability authority. Provider Apps remain solely responsible for acquisition
configuration and activation; Portfolio Architect consumes this state read-only
for provenance, diagnostics, and fail-closed validation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import re
from typing import Final

from .errors import ConfigurationError

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
METHOD_READY: Final = "ready"
METHOD_NOT_READY: Final = "not_ready"
METHOD_UNAVAILABLE: Final = "unavailable"
METHOD_RESEARCH_ONLY: Final = "research_only"
METHOD_STATES: Final = frozenset(
    {METHOD_READY, METHOD_NOT_READY, METHOD_UNAVAILABLE, METHOD_RESEARCH_ONLY}
)
FALLBACK_NONE: Final = "none"
CHANGE_REASON_OPERATOR: Final = "operator"
MAX_METHODS: Final = 8
MAX_CAPABILITIES: Final = 8

CAPABILITY_HOLDINGS: Final = "holdings"
CAPABILITY_CASH: Final = "cash"
AUTHORITY_ACTIVE_METHOD: Final = "active_method"
AUTHORITY_PROVIDER_FIXED: Final = "provider_fixed"
AUTHORITY_SUPPLEMENTAL: Final = "supplemental"
AUTHORITY_REASONS: Final = frozenset(
    {AUTHORITY_ACTIVE_METHOD, AUTHORITY_PROVIDER_FIXED, AUTHORITY_SUPPLEMENTAL}
)


@dataclass(frozen=True, slots=True)
class AcquisitionMethod:
    """One bounded acquisition method advertised by a provider Gateway."""

    method_id: str
    state: str
    active: bool
    can_activate: bool

    def __post_init__(self) -> None:
        if _ID_RE.fullmatch(self.method_id) is None:
            raise ConfigurationError("Gateway acquisition method ID is invalid")
        if self.state not in METHOD_STATES:
            raise ConfigurationError("Gateway acquisition method state is invalid")
        if not isinstance(self.active, bool) or not isinstance(self.can_activate, bool):
            raise ConfigurationError("Gateway acquisition method flags are invalid")
        if self.can_activate and self.state != METHOD_READY:
            raise ConfigurationError(
                "Only a ready Gateway acquisition method may be activatable"
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.method_id,
            "state": self.state,
            "active": self.active,
            "can_activate": self.can_activate,
        }


@dataclass(frozen=True, slots=True)
class AcquisitionCapability:
    """One canonical provider capability and its explicit source authority."""

    capability_id: str
    authoritative_method: str
    supported_methods: tuple[str, ...]
    authority_reason: str
    fallback_policy: str = FALLBACK_NONE

    def __post_init__(self) -> None:
        if _ID_RE.fullmatch(self.capability_id) is None:
            raise ConfigurationError("Gateway acquisition capability ID is invalid")
        if _ID_RE.fullmatch(self.authoritative_method) is None:
            raise ConfigurationError("Gateway capability authority method is invalid")
        if not 1 <= len(self.supported_methods) <= MAX_METHODS:
            raise ConfigurationError("Gateway capability method inventory is invalid")
        if any(_ID_RE.fullmatch(item) is None for item in self.supported_methods):
            raise ConfigurationError("Gateway capability method ID is invalid")
        if len(set(self.supported_methods)) != len(self.supported_methods):
            raise ConfigurationError("Gateway capability method IDs must be unique")
        if self.authoritative_method not in self.supported_methods:
            raise ConfigurationError("Gateway capability authority is not supported")
        if self.authority_reason not in AUTHORITY_REASONS:
            raise ConfigurationError("Gateway capability authority reason is invalid")
        if self.fallback_policy != FALLBACK_NONE:
            raise ConfigurationError("Gateway automatic capability fallback is unsupported")

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.capability_id,
            "authoritative_method": self.authoritative_method,
            "supported_methods": list(self.supported_methods),
            "authority_reason": self.authority_reason,
            "fallback_policy": self.fallback_policy,
        }


@dataclass(frozen=True, slots=True)
class AcquisitionControl:
    """Validated provider acquisition methods plus capability-level authority."""

    active_method: str
    methods: tuple[AcquisitionMethod, ...]
    fallback_policy: str = FALLBACK_NONE
    previous_method: str | None = None
    last_method_change_at: datetime | None = None
    last_method_change_reason: str | None = None
    capabilities: tuple[AcquisitionCapability, ...] = ()

    def __post_init__(self) -> None:
        if _ID_RE.fullmatch(self.active_method) is None:
            raise ConfigurationError("Gateway active acquisition method is invalid")
        if not 1 <= len(self.methods) <= MAX_METHODS:
            raise ConfigurationError("Gateway acquisition method inventory is invalid")
        ids = [item.method_id for item in self.methods]
        if len(set(ids)) != len(ids):
            raise ConfigurationError("Gateway acquisition method IDs must be unique")
        active = [item for item in self.methods if item.active]
        if len(active) != 1 or active[0].method_id != self.active_method:
            raise ConfigurationError("Gateway acquisition active-method state is inconsistent")
        if active[0].state != METHOD_READY:
            raise ConfigurationError("Active Gateway acquisition method must be ready")
        if self.fallback_policy != FALLBACK_NONE:
            raise ConfigurationError("Gateway automatic acquisition fallback is unsupported")
        history = (
            self.previous_method,
            self.last_method_change_at,
            self.last_method_change_reason,
        )
        if any(value is not None for value in history):
            if any(value is None for value in history):
                raise ConfigurationError("Gateway acquisition method-change history is incomplete")
            assert self.previous_method is not None
            assert self.last_method_change_at is not None
            assert self.last_method_change_reason is not None
            if (
                _ID_RE.fullmatch(self.previous_method) is None
                or self.previous_method not in ids
                or self.previous_method == self.active_method
            ):
                raise ConfigurationError("Gateway previous acquisition method is invalid")
            if (
                self.last_method_change_at.tzinfo is None
                or self.last_method_change_at.utcoffset() is None
            ):
                raise ConfigurationError("Gateway acquisition method-change time must be timezone-aware")
            if self.last_method_change_reason != CHANGE_REASON_OPERATOR:
                raise ConfigurationError("Gateway acquisition method-change reason is invalid")

        if self.capabilities:
            if not 1 <= len(self.capabilities) <= MAX_CAPABILITIES:
                raise ConfigurationError("Gateway acquisition capability inventory is invalid")
            capability_ids = [item.capability_id for item in self.capabilities]
            if len(set(capability_ids)) != len(capability_ids):
                raise ConfigurationError("Gateway acquisition capability IDs must be unique")
            if CAPABILITY_HOLDINGS not in capability_ids:
                raise ConfigurationError("Gateway acquisition capabilities must include holdings")
            states = {item.method_id: item.state for item in self.methods}
            method_ids = set(ids)
            for capability_item in self.capabilities:
                if any(method not in method_ids for method in capability_item.supported_methods):
                    raise ConfigurationError("Gateway capability references an unknown method")
                if states[capability_item.authoritative_method] != METHOD_READY:
                    raise ConfigurationError("Gateway capability authority method must be ready")
                if (
                    capability_item.authority_reason == AUTHORITY_ACTIVE_METHOD
                    and capability_item.authoritative_method != self.active_method
                ):
                    raise ConfigurationError("Active-method capability authority is inconsistent")
                if (
                    capability_item.authority_reason == AUTHORITY_SUPPLEMENTAL
                    and capability_item.authoritative_method == self.active_method
                ):
                    raise ConfigurationError("Supplemental capability authority is inconsistent")

    def as_health_fields(self, *, include_capabilities: bool = False) -> dict[str, object]:
        """Return bounded additive health control-plane fields."""
        fields: dict[str, object] = {
            "active_acquisition_method": self.active_method,
            "acquisition_methods": [item.as_dict() for item in self.methods],
            "fallback_policy": self.fallback_policy,
            "previous_acquisition_method": self.previous_method,
            "last_acquisition_method_change_at": (
                self.last_method_change_at.astimezone(timezone.utc).isoformat(timespec="seconds")
                if self.last_method_change_at is not None
                else None
            ),
            "last_acquisition_method_change_reason": self.last_method_change_reason,
        }
        if include_capabilities:
            fields["acquisition_capabilities"] = [
                item.as_dict() for item in self.capabilities
            ]
        return fields


def capability(
    capability_id: str,
    authoritative_method: str,
    *supported_methods: str,
    authority_reason: str = AUTHORITY_ACTIVE_METHOD,
) -> AcquisitionCapability:
    """Build one deterministic no-fallback capability-authority declaration."""
    return AcquisitionCapability(
        capability_id=capability_id,
        authoritative_method=authoritative_method,
        supported_methods=tuple(supported_methods),
        authority_reason=authority_reason,
    )


def single_method_control(method_id: str, *, cash: bool = False) -> AcquisitionControl:
    """Return one production-ready fixed-method control-plane state."""
    method = AcquisitionMethod(method_id, METHOD_READY, True, True)
    capabilities = [
        capability(
            CAPABILITY_HOLDINGS,
            method_id,
            method_id,
            authority_reason=AUTHORITY_PROVIDER_FIXED,
        )
    ]
    if cash:
        capabilities.append(
            capability(
                CAPABILITY_CASH,
                method_id,
                method_id,
                authority_reason=AUTHORITY_PROVIDER_FIXED,
            )
        )
    return AcquisitionControl(
        active_method=method_id,
        methods=(method,),
        capabilities=tuple(capabilities),
    )


def control_from_provider(provider: object) -> AcquisitionControl:
    """Read a provider control plane, deriving a safe holdings-only fallback.

    Older test doubles and third-party provider implementations may expose only
    ``acquisition_mode`` or a schema-8 control without capabilities. Health schema
    9 remains backward-compatible by deriving explicit holdings authority for the
    active method; official provider Apps declare their full capability inventory.
    """
    control = getattr(provider, "acquisition_control", None)
    if callable(control):
        control = control()
    if isinstance(control, AcquisitionControl):
        if control.capabilities:
            return control
        return replace(
            control,
            capabilities=(
                capability(
                    CAPABILITY_HOLDINGS,
                    control.active_method,
                    control.active_method,
                    authority_reason=AUTHORITY_ACTIVE_METHOD,
                ),
            ),
        )
    method_id = getattr(provider, "acquisition_mode", "unknown")
    if not isinstance(method_id, str) or _ID_RE.fullmatch(method_id) is None:
        method_id = "unknown"
    return single_method_control(method_id)


def method_inventory(*items: AcquisitionMethod) -> tuple[AcquisitionMethod, ...]:
    """Return a deterministic provider-defined method tuple."""
    return tuple(items)
