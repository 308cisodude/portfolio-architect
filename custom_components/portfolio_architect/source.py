"""Confined Home Assistant configuration-path handling for Portfolio Architect."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re

from homeassistant.core import HomeAssistant

from .engine.calculator import validate_configuration_source

_MAX_RELATIVE_PATH_LENGTH = 255
_SAFE_PATH_RE = re.compile(r"^[^\x00-\x1f\x7f]+$")


class PortfolioSourcePathError(ValueError):
    """Raised when a configured configuration path is unsafe or unavailable."""


@dataclass(frozen=True, slots=True)
class LocalConfigurationPath:
    """Resolved, confined local YAML configuration directory."""

    config_relative: str
    config_directory: Path


def normalise_relative_path(value: object, *, field: str) -> str:
    """Return a safe POSIX-style path relative to the HA configuration folder."""
    if not isinstance(value, str):
        raise PortfolioSourcePathError(f"{field} must be a relative path")
    cleaned = value.strip().replace("\\", "/")
    if (
        not cleaned
        or len(cleaned) > _MAX_RELATIVE_PATH_LENGTH
        or _SAFE_PATH_RE.fullmatch(cleaned) is None
    ):
        raise PortfolioSourcePathError(
            f"{field} is empty, too long, or contains control characters"
        )

    path = PurePosixPath(cleaned)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PortfolioSourcePathError(
            f"{field} must remain inside the Home Assistant configuration directory"
        )
    if path.parts[0] in {".storage", "custom_components"}:
        raise PortfolioSourcePathError(
            f"{field} cannot point into a protected Home Assistant directory"
        )
    return path.as_posix()


def resolve_configuration_directory(
    hass: HomeAssistant,
    config_relative: object,
    *,
    require_exists: bool,
) -> LocalConfigurationPath:
    """Resolve and confine the YAML configuration directory under /config."""
    config_clean = normalise_relative_path(
        config_relative, field="configuration directory"
    )
    root = Path(hass.config.path()).resolve()
    config_directory = (root / config_clean).resolve(strict=False)
    if not config_directory.is_relative_to(root):
        raise PortfolioSourcePathError(
            "Configured paths must remain inside the Home Assistant configuration directory"
        )
    result = LocalConfigurationPath(
        config_relative=config_clean,
        config_directory=config_directory,
    )
    if require_exists:
        try:
            validate_configuration_source(config_directory)
        except (OSError, ValueError) as err:
            raise PortfolioSourcePathError(str(err)) from err
    return result
