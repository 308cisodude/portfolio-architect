#!/usr/bin/env python3
"""Scaffold a new dashboard locale without duplicating card logic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_ROOT = PROJECT_ROOT / "dashboard"
MANIFEST_PATH = DASHBOARD_ROOT / "manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("locale", help="short locale id, for example es or fr")
    parser.add_argument("--from-locale", default="en")
    args = parser.parse_args()

    locale = args.locale.strip().lower()
    if not locale or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in locale):
        raise SystemExit(f"invalid locale id: {args.locale!r}")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    source_locale = args.from_locale.strip().lower()
    if source_locale not in manifest["locales"]:
        raise SystemExit(f"unsupported source locale: {source_locale}")

    source_catalog_path = DASHBOARD_ROOT / manifest["catalog_pattern"].format(locale=source_locale)
    source_catalog = yaml.safe_load(source_catalog_path.read_text(encoding="utf-8"))
    catalog_path = DASHBOARD_ROOT / manifest["catalog_pattern"].format(locale=locale)
    overlay_path = DASHBOARD_ROOT / manifest["overlay_pattern"].format(locale=locale)
    if catalog_path.exists() or overlay_path.exists():
        raise SystemExit(f"locale already exists: {locale}")

    catalog = {
        "locale": locale,
        "strings": {
            key: "__TODO__ " + str(value) for key, value in source_catalog["strings"].items()
        },
    }
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True, width=1_000_000),
        encoding="utf-8",
    )
    overlay_path.write_text(
        yaml.safe_dump({"locale": locale, "operations": []}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Created {catalog_path.relative_to(PROJECT_ROOT)}")
    print(f"Created {overlay_path.relative_to(PROJECT_ROOT)}")
    print("Add the locale to dashboard/manifest.json only after translation is complete.")


if __name__ == "__main__":
    main()
