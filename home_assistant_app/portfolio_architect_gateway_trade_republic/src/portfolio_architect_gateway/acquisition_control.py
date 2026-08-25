"""Provider-neutral acquisition-method control-plane state.

The common Gateway server exposes this bounded, read-only model through health
schema 8. Provider Apps remain the only place where acquisition methods are
configured or activated; Portfolio Architect itself consumes the state only for
operator visibility and evidence provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Final, Iterable

from .errors import ConfigurationError

_METHOD_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
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


@dataclass(frozen=True, slots=True)
class AcquisitionMethod:
    """One bounded acquisition method advertised by a provider Gateway."""

    method_id: str
    state: str
    active: bool
    can_activate: bool

    def __post_init__(self) -> None:
        if _METHOD_ID_RE.fullmatch(self.method_id) is None:
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
class AcquisitionControl:
    """Validated provider-level acquisition arbitration state."""

    active_method: str
    methods: tuple[AcquisitionMethod, ...]
    fallback_policy: str = FALLBACK_NONE
    previous_method: str | None = None
    last_method_change_at: datetime | None = None
    last_method_change_reason: str | None = None

    def __post_init__(self) -> None:
        if _METHOD_ID_RE.fullmatch(self.active_method) is None:
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
        if all(value is None for value in history):
            return
        if any(value is None for value in history):
            raise ConfigurationError("Gateway acquisition method-change history is incomplete")
        assert self.previous_method is not None
        assert self.last_method_change_at is not None
        assert self.last_method_change_reason is not None
        if (
            _METHOD_ID_RE.fullmatch(self.previous_method) is None
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

    def as_health_fields(self) -> dict[str, object]:
        """Return the exact additive health-schema-8 fields."""
        return {
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


def single_method_control(method_id: str) -> AcquisitionControl:
    """Return one production-ready fixed-method control-plane state."""
    method = AcquisitionMethod(method_id, METHOD_READY, True, True)
    return AcquisitionControl(active_method=method_id, methods=(method,))


def control_from_provider(provider: object) -> AcquisitionControl:
    """Read a provider control plane, deriving a safe single-method fallback.

    Older test doubles and third-party provider implementations may expose only
    ``acquisition_mode``. Health schema 8 remains backward-compatible by deriving
    a one-method, no-fallback inventory for those providers.
    """
    control = getattr(provider, "acquisition_control", None)
    if callable(control):
        control = control()
    if isinstance(control, AcquisitionControl):
        return control
    method_id = getattr(provider, "acquisition_mode", "unknown")
    if not isinstance(method_id, str) or _METHOD_ID_RE.fullmatch(method_id) is None:
        method_id = "unknown"
    return single_method_control(method_id)


def method_inventory(*items: AcquisitionMethod) -> tuple[AcquisitionMethod, ...]:
    """Return a deterministic provider-defined method tuple."""
    return tuple(items)
