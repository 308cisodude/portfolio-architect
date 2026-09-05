#!/usr/bin/env python3
"""Build deterministic static Portfolio Architect Lovelace dashboards."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_ROOT = PROJECT_ROOT / "dashboard"
MANIFEST_PATH = DASHBOARD_ROOT / "dashboard-build.json"


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def decode_pointer(path: str) -> list[str]:
    if not path.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {path}")
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def apply_overlay_operation(root: Any, operation: dict[str, Any]) -> None:
    parts = decode_pointer(str(operation["path"]))
    if not parts:
        raise ValueError("Overlay operations may not replace the dashboard root")

    current = root
    for raw in parts[:-1]:
        key = int(raw) if isinstance(current, list) else raw
        current = current[key]

    raw = parts[-1]
    key = int(raw) if isinstance(current, list) else raw
    kind = operation["op"]

    if kind in {"add", "replace"}:
        value = copy.deepcopy(operation["value"])
        if isinstance(current, list):
            if kind == "add":
                if key < 0 or key > len(current):
                    raise IndexError(f"add target outside list: {operation['path']}")
                current.insert(key, value)
            else:
                _ = current[key]
                current[key] = value
        else:
            if kind == "replace" and key not in current:
                raise KeyError(f"replace target missing: {operation['path']}")
            current[key] = value
        return

    if kind == "remove":
        if isinstance(current, list):
            del current[key]
        else:
            del current[key]
        return

    raise ValueError(f"unsupported overlay op: {kind}")


def resolve_i18n(value: Any, strings: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$i18n"}:
            key = value["$i18n"]
            if key not in strings:
                raise KeyError(f"missing i18n key: {key}")
            return copy.deepcopy(strings[key])
        return {key: resolve_i18n(child, strings) for key, child in value.items()}
    if isinstance(value, list):
        return [resolve_i18n(child, strings) for child in value]
    return value


def build_view(locale: str, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = manifest or load_manifest()
    if locale not in manifest["locales"]:
        raise ValueError(f"unsupported locale: {locale}")

    view = load_yaml(DASHBOARD_ROOT / manifest["shared_view"])
    view["sections"] = [load_yaml(DASHBOARD_ROOT / path) for path in manifest["sections"]]

    catalog = load_yaml(DASHBOARD_ROOT / manifest["catalog_pattern"].format(locale=locale))
    if catalog.get("locale") != locale:
        raise ValueError(f"catalog locale mismatch: {locale}")
    strings = catalog.get("strings", {})
    unfinished = [
        key
        for key, text in strings.items()
        if isinstance(text, str) and text.startswith("__TODO__")
    ]
    if unfinished:
        raise ValueError(
            f"locale {locale} has TODO translations: {', '.join(unfinished[:5])}"
        )

    view = resolve_i18n(view, strings)
    overlay = load_yaml(DASHBOARD_ROOT / manifest["overlay_pattern"].format(locale=locale)) or {}
    if overlay.get("locale") != locale:
        raise ValueError(f"overlay locale mismatch: {locale}")
    for operation in overlay.get("operations", []):
        apply_overlay_operation(view, operation)
    return view


def build_dashboard(locales: list[str]) -> dict[str, Any]:
    manifest = load_manifest()
    return {"views": [build_view(locale, manifest) for locale in locales]}


def dump_dashboard(data: dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        width=1_000_000,
        default_flow_style=False,
    )


def parse_locale_argument(value: str, manifest: dict[str, Any]) -> list[str]:
    if value == "all":
        return list(manifest["locales"])
    locales = [part.strip() for part in value.split(",") if part.strip()]
    if not locales:
        raise ValueError("at least one locale is required")
    unsupported = [locale for locale in locales if locale not in manifest["locales"]]
    if unsupported:
        raise ValueError(f"unsupported locale(s): {', '.join(unsupported)}")
    return locales


def write_dashboard(locale_selector: str, output: Path) -> None:
    manifest = load_manifest()
    locales = parse_locale_argument(locale_selector, manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dump_dashboard(build_dashboard(locales)), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--locale", default="all", help="en, de, comma-separated locales, or all")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_dashboard(args.locale, args.output)


if __name__ == "__main__":
    main()
