"""v1.49.0 retires the completed PA-side Comdirect CSV migration bridge."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
COMDIRECT_APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_pa_runtime_no_longer_contains_comdirect_specific_csv_acquisition() -> None:
    importers = _text(COMPONENT / "engine" / "importers.py")
    io = _text(COMPONENT / "engine" / "io.py")
    coordinator = _text(COMPONENT / "coordinator.py")
    assert "PROVIDER_COMDIRECT" not in importers
    assert "read_comdirect_positions" not in importers
    assert "Comdirect securities table" not in importers
    assert "read_comdirect_positions" not in io
    assert "PROVIDER_COMDIRECT" not in coordinator
    assert 'PROVIDER_GENERIC_CSV: Final = "generic_csv"' in importers
    assert "SUPPORTED_PROVIDERS: Final = (PROVIDER_GENERIC_CSV,)" in importers


def test_config_flow_no_longer_contains_comdirect_csv_migration_or_selection() -> None:
    flow = _text(COMPONENT / "config_flow.py")
    assert "VERSION = 11" in flow
    assert "async_step_hassio_migrate_comdirect_csv_confirm" not in flow
    assert "comdirect_gateway_migration_mismatch" not in flow
    assert "legacy_positions != snapshot.positions" not in flow
    current_provider_block = flow.split("_SUPPORTED_SOURCE_PROVIDERS = (", 1)[1].split(")", 1)[0]
    assert "PROVIDER_GENERIC_CSV" in current_provider_block
    assert "PROVIDER_LOCAL_REST_JSON" in current_provider_block
    assert "PROVIDER_COMDIRECT" not in current_provider_block


def test_schema_11_fails_closed_if_legacy_comdirect_csv_is_still_active() -> None:
    init = _text(COMPONENT / "__init__.py")
    const = _text(COMPONENT / "const.py")
    assert 'LEGACY_COMDIRECT_CSV_PROVIDER: Final = "comdirect_csv"' in const
    schema11 = init.split("if entry.version < 11:", 1)[1].split("if migrated_entities:", 1)[0]
    assert "LEGACY_COMDIRECT_CSV_PROVIDER" in schema11
    assert "SOURCE_TYPE_LOCAL_FILES" in schema11
    assert "return False" in schema11
    assert "Install v1.48.2" in schema11
    assert "version=11" in schema11


def test_comdirect_gateway_keeps_complete_csv_acquisition_and_no_fallback() -> None:
    config = yaml.safe_load(_text(COMDIRECT_APP / "config.yaml"))
    app = _text(COMDIRECT_APP / "src" / "portfolio_architect_gateway" / "app.py")
    comdirect_csv = _text(COMDIRECT_APP / "src" / "portfolio_architect_gateway" / "comdirect_csv.py")
    assert config["slug"] == "portfolio_architect_gateway"
    acquisition = _text(COMDIRECT_APP / "src" / "portfolio_architect_gateway" / "acquisition.py")
    assert 'return "comdirect"' in acquisition
    assert "ComdirectAcquisitionProvider" in app
    assert 'return "csv"' in comdirect_csv or "parse_comdirect" in comdirect_csv
    assert "live_api" in app
    assert "csv" in app


def test_current_ui_and_enum_surfaces_have_no_legacy_comdirect_csv_provider() -> None:
    sensor = _text(COMPONENT / "sensor.py")
    assert "PROVIDER_COMDIRECT" not in sensor
    for language in ("en", "de"):
        data = json.loads(_text(COMPONENT / "translations" / f"{language}.json"))
        encoded = json.dumps(data, ensure_ascii=False)
        for forbidden in (
            "hassio_migrate_comdirect_csv_confirm",
            "comdirect_gateway_migration_mismatch",
            "comdirect_gateway_migrated",
            '"comdirect_csv"',
        ):
            assert forbidden not in encoded


def test_current_source_adapter_documentation_places_comdirect_csv_only_in_gateway() -> None:
    adapters = _text(ROOT / "docs" / "SOURCE-ADAPTERS.md")
    assert "Comdirect Gateway" in adapters
    assert "Static CSV" in adapters
    assert "Home Assistant-side Comdirect CSV adapter" not in adapters
