"""Translation completeness and language-neutral implementation tests."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def flatten(value, prefix="") -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            keys.add(path)
            keys.update(flatten(child, path))
    return keys


def test_english_and_german_translation_keys_match() -> None:
    english = json.loads((COMPONENT / "translations" / "en.json").read_text())
    german = json.loads((COMPONENT / "translations" / "de.json").read_text())
    assert flatten(english) == flatten(german)


def test_custom_integration_uses_runtime_translation_files_only() -> None:
    assert not (COMPONENT / "strings.json").exists()
    assert (COMPONENT / "translations" / "en.json").is_file()
    assert (COMPONENT / "translations" / "de.json").is_file()


def test_entity_names_are_translation_key_based() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    assert '_attr_translation_key = "target_position_coverage"' in sensor
    assert '_attr_translation_key = "target_architecture_complete"' in binary
    assert '_attr_translation_key = "target_position_held"' in binary


def test_state_attribute_translations_are_present() -> None:
    english = json.loads((COMPONENT / "translations" / "en.json").read_text())
    german = json.loads((COMPONENT / "translations" / "de.json").read_text())
    for data in (english, german):
        current = data["entity"]["sensor"]["current_allocation"]
        coverage = data["entity"]["sensor"]["target_position_coverage"]
        architecture = data["entity"]["binary_sensor"]["target_architecture_complete"]
        held = data["entity"]["binary_sensor"]["target_position_held"]
        assert "state_attributes" in current
        assert "state_attributes" in coverage
        assert "state_attributes" in architecture
        assert "state_attributes" in held
        overview = data["entity"]["sensor"]["allocation_overview"]
        assert overview["state"]["on_target"]
        assert overview["state"]["drift_detected"]
        assert "state_attributes" in overview


def test_native_icon_translations_replace_python_icon_logic() -> None:
    icons = json.loads((COMPONENT / "icons.json").read_text())
    binary_icons = icons["entity"]["binary_sensor"]
    assert binary_icons["target_architecture_complete"]["state"]["on"] == "mdi:check-decagram"
    assert binary_icons["target_position_held"]["state"]["off"] == "mdi:circle-outline"

    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    assert "_attr_icon" not in sensor
    assert "def icon(" not in binary


def test_v070_translation_keys_are_present() -> None:
    for locale in ("en", "de"):
        data = json.loads((COMPONENT / "translations" / f"{locale}.json").read_text())
        sensors = data["entity"]["sensor"]
        binary = data["entity"]["binary_sensor"]
        for key in (
            "monthly_contribution", "recommended_total", "unallocated_contribution",
            "purchase_count", "proposed_buy", "last_successful_refresh",
            "payload_schema_version", "version",
        ):
            assert key in sensors
        for key in (
            "monthly_plan_ready", "mandatory_controls_compliant",
            "source_healthy", "data_fresh",
        ):
            assert key in binary
        for key in (
            "policy_status", "policy_checks_evaluated", "policy_error_findings",
            "policy_warning_findings", "accepted_exception_count",
            "optimisation_opportunity_count", "next_exception_review",
            "policy_exception_detail",
        ):
            assert key in sensors
        for rule in (
            "metadata", "ucits_required", "accumulating_preferred",
            "ireland_preferred", "max_ter_pct", "minimum_fund_size_eur",
            "savings_plan_required", "free_savings_plan_preferred",
        ):
            assert f"policy_finding_{rule}" in sensors
        assert "options" in data
