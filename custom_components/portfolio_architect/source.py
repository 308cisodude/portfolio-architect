"""Local source path handling for Portfolio Architect."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re

from homeassistant.core import HomeAssistant

from .engine.calculator import validate_configuration_source, validate_local_source

_MAX_RELATIVE_PATH_LENGTH = 255
_SAFE_PATH_RE = re.compile(r"^[^\x00-\x1f\x7f]+$")


class PortfolioSourcePathError(ValueError):
    """Raised when a configured source path is unsafe or unavailable."""




@dataclass(frozen=True, slots=True)
class LocalConfigurationPath:
    """Resolved, confined local YAML configuration directory."""

    config_relative: str
    config_directory: Path


@dataclass(frozen=True, slots=True)
class LocalSourcePaths:
    """Resolved, confined local source paths."""

    csv_relative: str
    config_relative: str
    csv_path: Path
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
        raise PortfolioSourcePathError(f"{field} is empty, too long, or contains control characters")

    path = PurePosixPath(cleaned)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PortfolioSourcePathError(f"{field} must remain inside the Home Assistant configuration directory")
    if path.parts[0] in {".storage", "custom_components"}:
        raise PortfolioSourcePathError(f"{field} cannot point into a protected Home Assistant directory")
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


def resolve_local_source_paths(
    hass: HomeAssistant,
    csv_relative: object,
    config_relative: object,
    *,
    require_exists: bool,
) -> LocalSourcePaths:
    """Resolve and confine configured paths under Home Assistant's config folder."""
    csv_clean = normalise_relative_path(csv_relative, field="CSV path")
    config_clean = normalise_relative_path(config_relative, field="configuration directory")

    root = Path(hass.config.path()).resolve()
    csv_path = (root / csv_clean).resolve(strict=False)
    config_directory = (root / config_clean).resolve(strict=False)
    if not csv_path.is_relative_to(root) or not config_directory.is_relative_to(root):
        raise PortfolioSourcePathError("Configured paths must remain inside the Home Assistant configuration directory")

    paths = LocalSourcePaths(
        csv_relative=csv_clean,
        config_relative=config_clean,
        csv_path=csv_path,
        config_directory=config_directory,
    )
    if require_exists:
        try:
            validate_local_source(csv_path, config_directory)
        except (OSError, ValueError) as err:
            raise PortfolioSourcePathError(str(err)) from err
    return paths



@dataclass(frozen=True, slots=True)
class SupplementalCsvPath:
    """One confined supplemental CSV source."""

    relative: str
    path: Path


def resolve_supplemental_csv_paths(
    hass: HomeAssistant,
    values: object,
    *,
    require_exists: bool,
    maximum: int = 8,
) -> tuple[SupplementalCsvPath, ...]:
    """Resolve a bounded list of distinct supplemental CSV paths under /config."""
    if values in (None, "", []):
        return ()
    if not isinstance(values, list) or len(values) > maximum:
        raise PortfolioSourcePathError("Supplemental CSV paths must be a bounded list")
    root = Path(hass.config.path()).resolve()
    result: list[SupplementalCsvPath] = []
    seen: set[str] = set()
    for value in values:
        relative = normalise_relative_path(value, field="supplemental CSV path")
        if relative in seen:
            raise PortfolioSourcePathError("Supplemental CSV paths must be unique")
        path = (root / relative).resolve(strict=False)
        if not path.is_relative_to(root):
            raise PortfolioSourcePathError("Supplemental CSV paths must remain inside /config")
        if require_exists and not path.is_file():
            raise PortfolioSourcePathError(f"Supplemental CSV does not exist: {Path(relative).name}")
        result.append(SupplementalCsvPath(relative=relative, path=path))
        seen.add(relative)
    return tuple(result)

def csv_source_config_from_data(data: dict[str, object]):
    """Return the strict provider adapter config stored in a config entry."""
    from .engine.importers import CsvSourceConfig

    return CsvSourceConfig.from_mapping(data)
