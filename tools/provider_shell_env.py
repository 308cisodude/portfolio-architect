#!/usr/bin/env python3
"""Print the Supervisor-provided environment required by a provider shell smoke test."""
from __future__ import annotations

from pathlib import Path
import sys

import yaml

REQUIRED_ENV = ("PA_PROVIDER_ID", "PA_PROVIDER_NAME")


def load_environment(config_path: Path) -> tuple[str, str]:
    """Return validated provider shell environment values from App config metadata."""
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as err:
        raise SystemExit(f"Unable to read provider App config: {config_path}") from err
    if not isinstance(raw, dict):
        raise SystemExit(f"Provider App config must be an object: {config_path}")
    environment = raw.get("environment")
    if not isinstance(environment, dict):
        raise SystemExit(f"Provider App config is missing environment metadata: {config_path}")

    values: list[str] = []
    for key in REQUIRED_ENV:
        value = environment.get(key)
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or any(character in value for character in "\r\n\0")
        ):
            raise SystemExit(f"Provider App config has invalid {key}: {config_path}")
        values.append(value)
    return values[0], values[1]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("Usage: provider_shell_env.py <config.yaml>")
    provider_id, provider_name = load_environment(Path(argv[1]))
    print(provider_id)
    print(provider_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
