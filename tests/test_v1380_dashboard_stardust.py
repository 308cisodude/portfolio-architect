"""v1.51.1 native dashboard usability contracts."""

from __future__ import annotations

from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import re
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
DASHBOARD = ROOT / "dashboard" / "bilingual-dashboard.yaml"


def _load_presentation():
    path = COMPONENT / "presentation.py"
    spec = importlib.util.spec_from_file_location("pa_v138_presentation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _cards(view: dict, *, key: str, value: str) -> list[dict]:
    return [item for item in _walk(view) if item.get(key) == value]


def test_cash_context_aggregates_complete_provider_evidence_and_fails_closed() -> None:
    presentation = _load_presentation()
    providers = (
        SimpleNamespace(eligible_eur=Decimal("3000.00"), authorized_eur=Decimal("2000.00")),
        SimpleNamespace(eligible_eur=Decimal("500.00"), authorized_eur=Decimal("500.00")),
    )
    assert presentation.investment_cash_totals(
        providers, fallback_eligible=None, fallback_authorized=None
    ) == (3500.0, 1000.0)

    incomplete = (
        SimpleNamespace(eligible_eur=Decimal("3000"), authorized_eur=Decimal("2000")),
        SimpleNamespace(eligible_eur=Decimal("500"), authorized_eur=None),
    )
    assert (
        presentation.investment_cash_totals(
            incomplete, fallback_eligible=9999, fallback_authorized=9999
        )
        is None
    )

    assert presentation.investment_cash_totals(
        (), fallback_eligible=3598.97, fallback_authorized=2574.97
    ) == (3598.97, 1024.0)


def test_cash_context_formats_en_de_and_planned_outlay_without_policy_mislabeling() -> None:
    presentation = _load_presentation()
    assert presentation.display_investment_cash_context(
        3598.97, 1024, german=False
    ) == "of €3,598.97 available cash · €1,024.00 excluded by policy"
    assert presentation.display_investment_cash_context(
        3598.97, 1024, planned_outlay=350, german=False
    ) == (
        "of €3,598.97 available cash · €1,024.00 excluded by policy · €350.00 planned"
    )
    assert presentation.display_investment_cash_context(
        3598.97, 1024, german=True
    ) == "von 3.598,97 € verfügbarem Bargeld · 1.024,00 € per Richtlinie ausgeschlossen"
    assert presentation.display_investment_cash_context(
        3598.97, 1024, planned_outlay=350, german=True
    ) == (
        "von 3.598,97 € verfügbarem Bargeld · 1.024,00 € per Richtlinie ausgeschlossen · 350,00 € geplant"
    )


def test_recommended_purchase_rows_open_copy_friendly_isin_and_hold_explanation() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    for view, title in zip(doc["views"], ("Recommended purchases", "Empfohlene Käufe"), strict=True):
        filters = [
            item
            for item in _cards(view, key="type", value="entity-filter")
            if isinstance(item.get("card"), dict) and item["card"].get("title") == title
        ]
        assert len(filters) == 1
        wrapper = filters[0]
        assert wrapper["conditions"] == [{"condition": "numeric_state", "above": 0}]
        assert wrapper["show_empty"] is False
        assert wrapper["card"]["type"] == "entities"
        rows = wrapper["entities"]
        assert len(rows) == 32
        for slot, row in enumerate(rows, start=1):
            prefix = f"sensor.portfolio_architect_presentation_target_{slot:02d}"
            assert row["entity"] == f"{prefix}_proposed_buy"
            assert row["name"] == {"type": "entity"}
            assert row["tap_action"] == {
                "action": "more-info",
                "entity": f"{prefix}_instrument_isin",
            }
            assert row["hold_action"] == {
                "action": "more-info",
                "entity": f"{prefix}_purchase_explanation",
            }


def test_cash_tiles_show_bounded_context_in_both_dashboard_locales() -> None:
    doc = yaml.safe_load(DASHBOARD.read_text(encoding="utf-8"))
    expected = (
        (
            "Authorized investment cash",
            "Cash after recommended purchases",
            ["state", "cash_context"],
        ),
        (
            "Freigegebenes Anlageguthaben",
            "Guthaben nach empfohlenen Käufen",
            ["display_state_de", "cash_context_de"],
        ),
    )
    for view, (authorized_name, remaining_name, state_content) in zip(
        doc["views"], expected, strict=True
    ):
        authorized = _cards(view, key="name", value=authorized_name)
        remaining = _cards(view, key="name", value=remaining_name)
        assert len(authorized) == 1
        assert len(remaining) == 1
        assert authorized[0]["type"] == "tile"
        assert authorized[0]["state_content"] == state_content
        assert remaining[0]["type"] == "tile"
        assert remaining[0]["state_content"] == state_content


def test_cash_sensors_expose_context_attributes_without_changing_wire_contracts() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    presentation = (COMPONENT / "presentation.py").read_text(encoding="utf-8")
    assert "investment_cash_totals(" in sensor
    assert '"total_available_cash_eur"' in sensor
    assert '"policy_excluded_cash_eur"' in sensor
    assert '"planned_cash_outlay_eur"' in sensor
    assert '"cash_context"' in sensor
    assert '"cash_context_de"' in sensor
    assert "provider_cash" in presentation
    assert "eligible_eur" in presentation
    assert "authorized_eur" in presentation

    release_notes = (ROOT / "docs" / "RELEASE-NOTES.md").read_text(encoding="utf-8")
    for contract in (
        "payload schema 8: unchanged",
        "REST portfolio schema 1: unchanged",
        "Gateway health schema 7 current; schemas 1–6 remain supported",
        "presentation schema 2",
    ):
        assert contract in release_notes


def test_v1380_metadata_dashboard_and_translation_contracts_are_aligned() -> None:
    assert 'version = "1.51.1"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.51.1"
    assert 'VERSION: Final = "1.51.1"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert '__version__ = "1.51.1"' in (COMPONENT / "engine" / "__init__.py").read_text(encoding="utf-8")
    assert (ROOT / "docs" / "UPGRADE-1.51.1.md").is_file()

    source = DASHBOARD.read_text(encoding="utf-8")
    lowered = source.casefold()
    for forbidden in ("auto-entities", "card-mod", "custom:", "javascript"):
        assert forbidden not in lowered
    assert re.search(r"portfolio_architect_target_[0-9a-f]{32}_", source) is None
    assert "portfolio_architect_holding_" not in source

    for locale in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{locale}.json").read_text(encoding="utf-8")
        )
        sensors = translations["entity"]["sensor"]
        for key in ("available_investment_reserve", "remaining_investment_reserve"):
            attrs = sensors[key]["state_attributes"]
            assert "total_available_cash_eur" in attrs
            assert "policy_excluded_cash_eur" in attrs
            assert "cash_context" in attrs
            assert "cash_context_de" in attrs
