"""Bounded local YAML and CSV I/O helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .importers import (
    CsvSourceConfig,
    inspect_csv_headers,
    parse_number,
    read_generic_positions,
    read_positions,
)

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


# Backward-compatible alias used by earlier tests and external examples.
def parse_de_number(value: str):
    """Parse one German-formatted number."""
    return parse_number(value, "comma_decimal")


__all__ = [
    "CsvSourceConfig",
    "inspect_csv_headers",
    "load_yaml",
    "parse_de_number",
    "read_generic_positions",
    "read_positions",
]
