"""Bounded provider-neutral YAML I/O helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_MAX_YAML_FILE_SIZE = 1024 * 1024


def load_yaml(path: Path) -> dict[str, Any]:
    """Read one bounded YAML mapping using safe loading only."""
    if path.stat().st_size > _MAX_YAML_FILE_SIZE:
        raise ValueError(f"YAML file is too large: {path.name}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


__all__ = ["load_yaml"]
