"""v1.46.0 retires the completed PA-side DKB CSV migration bridge."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
DKB_APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_pa_import_layer_no_longer_contains_dkb_specific_csv_acquisition() -> None:
    importers = COMPONENT / "engine" / "importers.py"
    source = _text(COMPONENT / "source.py")
    coordinator = _text(COMPONENT / "coordinator.py")
    # v1.46 removed DKB-specific CSV acquisition; v1.51 removes the
    # remaining provider-neutral importer module from PA entirely.
    assert not importers.exists()
    assert "SupplementalCsvPath" not in source
    assert "resolve_supplemental_csv_paths" not in source
    assert "supplemental_dkb_csv_paths" not in coordinator


def test_config_and_transport_bridge_surfaces_are_removed() -> None:
    flow = _text(COMPONENT / "config_flow.py")
    rest = _text(COMPONENT / "rest_client.py")
    server = _text(ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "server.py")
    dkb_app = _text(DKB_APP / "src" / "portfolio_architect_gateway" / "dkb_app.py")
    assert "async_step_dkb_sources" not in flow
    assert "async_step_hassio_migrate_dkb_csv_confirm" not in flow
    assert "gateway_provider_conflicts_with_dkb_csv" not in flow
    assert "migration-snapshot" not in rest
    assert "MIGRATION_SNAPSHOT_PATH" not in rest
    assert "migration-snapshot" not in server
    assert "migration_snapshot_enabled" not in server
    assert "ignore_max_age" not in server
    assert "migration_snapshot_enabled" not in dkb_app


def test_dkb_gateway_keeps_provider_specific_csv_acquisition() -> None:
    config = yaml.safe_load(_text(DKB_APP / "config.yaml"))
    dkb_csv = _text(DKB_APP / "src" / "portfolio_architect_gateway" / "dkb_csv.py")
    app = _text(DKB_APP / "src" / "portfolio_architect_gateway" / "dkb_app.py")
    assert config["environment"]["PA_PROVIDER_ID"] == "dkb"
    assert config["boot"] == "auto"
    assert "parse_dkb_csv_batch" in dkb_csv
    assert "parse_dkb_csv_batch" in app


def test_schema_10_fails_closed_if_legacy_dkb_acquisition_is_still_active() -> None:
    init = _text(COMPONENT / "__init__.py")
    flow = _text(COMPONENT / "config_flow.py")
    assert "VERSION = 13" in flow
    assert 'entry.data.get(CONF_SOURCE_PROVIDER) == "dkb_csv"' in init
    assert 'legacy_option_key = "supplemental_dkb_csv_paths"' in init
    assert "return False" in init.split('legacy_option_key = "supplemental_dkb_csv_paths"', 1)[1]
    assert "version=10" in init
    assert "Install v1.45.1" in init


def test_current_translations_have_no_legacy_dkb_csv_ui() -> None:
    for language in ("en", "de"):
        data = json.loads(_text(COMPONENT / "translations" / f"{language}.json"))
        encoded = json.dumps(data, ensure_ascii=False)
        for forbidden in (
            "hassio_migrate_dkb_csv_confirm",
            "dkb_gateway_migration_mismatch",
            "dkb_gateway_migration_snapshot_unavailable",
            "dkb_gateway_migrated",
            "supplemental_dkb_csv_paths",
            '"dkb_csv"',
        ):
            assert forbidden not in encoded
