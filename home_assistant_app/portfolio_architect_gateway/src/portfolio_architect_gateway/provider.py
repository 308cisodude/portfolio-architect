"""Provider-neutral runtime contract for Portfolio Architect Gateways."""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from .errors import ConfigurationError
from .models import PortfolioSnapshot

_PROVIDER_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
_MIN_POLL_INTERVAL_SECONDS = 300
_MAX_POLL_INTERVAL_SECONDS = 86400


def normalise_provider_id(value: str) -> str:
    """Return one bounded machine-readable provider identifier."""
    if not isinstance(value, str) or _PROVIDER_ID_RE.fullmatch(value) is None:
        raise ConfigurationError("Gateway provider ID is invalid")
    return value


def normalise_poll_interval_seconds(value: int) -> int:
    """Return one bounded provider refresh cadence."""
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not _MIN_POLL_INTERVAL_SECONDS <= value <= _MAX_POLL_INTERVAL_SECONDS
    ):
        raise ConfigurationError("Gateway provider poll interval is invalid")
    return value


@runtime_checkable
class PortfolioProvider(Protocol):
    """Minimal provider contract consumed by the hardened Gateway server."""

    @property
    def provider_id(self) -> str:
        """Return a stable non-secret provider identifier."""
        ...

    @property
    def poll_interval_seconds(self) -> int:
        """Return the validated provider refresh cadence."""
        ...

    def fetch_snapshot(self) -> PortfolioSnapshot:
        """Return one validated provider-neutral snapshot."""
        ...
