"""v1.63.0 modular static dashboard source and localization contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
DASHBOARD_BUILD = DASHBOARD / "dashboard-build.json"
MANIFEST = json.loads(DASHBOARD_BUILD.read_text(encoding="utf-8"))


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _i18n_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        if set(value) == {"$i18n"}:
            found.add(str(value["$i18n"]))
        else:
            for child in value.values():
                found.update(_i18n_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_i18n_keys(child))
    return found


def _generated(locale: str) -> Path:
    return DASHBOARD / MANIFEST["outputs"][locale]


def test_dashboard_source_is_shared_and_catalogs_are_bounded() -> None:
    assert MANIFEST["schema_version"] == 1
    assert MANIFEST["default_locale"] == "en"
    assert MANIFEST["locales"] == ["en", "de"]
    assert len(MANIFEST["sections"]) == 9

    catalogs = {
        locale: _load(DASHBOARD / MANIFEST["catalog_pattern"].format(locale=locale))
        for locale in MANIFEST["locales"]
    }
    keys = {locale: set(catalog["strings"]) for locale, catalog in catalogs.items()}
    assert len(keys["en"]) == 100
    assert keys["en"] == keys["de"]
    assert not any(
        str(value).startswith("__TODO__")
        for catalog in catalogs.values()
        for value in catalog["strings"].values()
    )

    shared = _load(DASHBOARD / MANIFEST["shared_view"])
    shared["sections"] = [_load(DASHBOARD / path) for path in MANIFEST["sections"]]
    assert _i18n_keys(shared) == keys["en"]

    overlays = {
        locale: _load(DASHBOARD / MANIFEST["overlay_pattern"].format(locale=locale))
        for locale in MANIFEST["locales"]
    }
    assert overlays["en"] == {"locale": "en", "operations": []}
    assert len(overlays["de"]["operations"]) == 40
    assert {op["op"] for op in overlays["de"]["operations"]} <= {"add", "replace", "remove"}
    assert all(str(op["path"]).startswith("/") for op in overlays["de"]["operations"])


def test_generated_dashboards_are_deterministic_current_and_semantically_locked(tmp_path: Path) -> None:
    selectors = ("en", "de", "all")
    for selector in selectors:
        first = tmp_path / f"{selector}-1.yaml"
        second = tmp_path / f"{selector}-2.yaml"
        for output in (first, second):
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/build_dashboard.py"),
                    "--locale",
                    selector,
                    "--output",
                    str(output),
                ],
                check=True,
                cwd=ROOT,
            )
        assert first.read_bytes() == second.read_bytes()
        assert first.read_bytes() == _generated(selector).read_bytes()
        assert _canonical_hash(_load(first)) == MANIFEST["semantic_reference"][selector]

    assert (DASHBOARD / "bilingual-dashboard.yaml").read_bytes() == _generated("all").read_bytes()


def test_generated_language_artifacts_are_single_view_and_combined_is_optional() -> None:
    en = _load(_generated("en"))
    de = _load(_generated("de"))
    combined = _load(_generated("all"))

    assert [(view["title"], view["path"]) for view in en["views"]] == [
        ("EN", "portfolio-architect")
    ]
    assert [(view["title"], view["path"]) for view in de["views"]] == [
        ("DE", "portfolio-architekt")
    ]
    assert combined == {"views": [en["views"][0], de["views"][0]]}
    assert all(len(document["views"][0]["sections"]) == 9 for document in (en, de))


def test_zero_exception_review_state_is_explicit_and_review_cards_are_bounded() -> None:
    expected_names = {
        "en": "Exception review not required",
        "de": "Ausnahmeprüfung nicht erforderlich",
    }
    count = "sensor.portfolio_architect_accepted_exception_count"
    review_entities = {
        "date.portfolio_architect_oldest_overdue_exception_review",
        "date.portfolio_architect_next_exception_review",
    }

    for locale in ("en", "de"):
        cards = _load(_generated(locale))["views"][0]["sections"][1]["cards"]
        zero_cards = [
            card
            for card in cards
            if card.get("type") == "conditional"
            and card.get("conditions") == [
                {"condition": "numeric_state", "entity": count, "below": 1}
            ]
        ]
        assert any(
            card["card"].get("name") == expected_names[locale]
            and card["card"].get("color") == "green"
            for card in zero_cards
        )

        review_cards = [
            card
            for card in cards
            if card.get("type") == "conditional"
            and card.get("card", {}).get("entity") in review_entities
        ]
        assert len(review_cards) == 2
        for card in review_cards:
            assert {"condition": "numeric_state", "entity": count, "above": 0} in card["conditions"]


def test_legacy_duplicated_dashboard_authoring_surfaces_are_retired() -> None:
    # Keep repository dashboard metadata away from Home Assistant's reserved
    # manifest.json filename so hassfest cannot mistake it for an integration.
    assert DASHBOARD_BUILD.is_file()
    assert not (DASHBOARD / "manifest.json").exists()
    manifests = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("manifest.json"))
    assert manifests == ["custom_components/portfolio_architect/manifest.json"]

    assert not (DASHBOARD / "en").exists()
    assert not (DASHBOARD / "de").exists()
    for name in (
        ".tmp_en.yaml",
        ".tmp_de.yaml",
        "allocation-stack.yaml",
        "monthly-investment-plan.yaml",
        "policy-compliance.yaml",
        "runtime-health.yaml",
        "target-architecture.yaml",
    ):
        assert not (DASHBOARD / name).exists()

    # Home Assistant receives ordinary static Lovelace YAML only.
    for selector in ("en", "de", "all"):
        text = _generated(selector).read_text(encoding="utf-8")
        assert "$i18n" not in text
        assert "__TODO__" not in text
        assert "!include" not in text
        assert "custom:" not in text
