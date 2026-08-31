"""Regression coverage for DKB Gateway discovery after legacy CSV retirement."""

from __future__ import annotations

from pathlib import Path
import importlib.util

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def _load_gateway_provider_ids():
    path = COMPONENT / "gateway_provider_ids.py"
    spec = importlib.util.spec_from_file_location("pa_gateway_provider_ids_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _step(source: str, name: str, next_name: str) -> str:
    return source.split(f"async def {name}", 1)[1].split(f"async def {next_name}", 1)[0]


def test_dkb_gateway_is_the_only_active_dkb_provider_identity() -> None:
    config = yaml.safe_load(
        (ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb" / "config.yaml").read_text(
            encoding="utf-8"
        )
    )
    provider_ids = _load_gateway_provider_ids()
    importers = COMPONENT / "engine" / "importers.py"
    assert provider_ids.GATEWAY_PROVIDER_DKB == "dkb"
    assert config["environment"]["PA_PROVIDER_ID"] == provider_ids.GATEWAY_PROVIDER_DKB
    assert not importers.exists()


def test_dkb_discovery_is_internal_after_the_single_pa_entry_exists() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    hassio = _step(source, "async_step_hassio", "async_step_hassio_comdirect_slug_migration_confirm")
    assert "_remember_hassio_discovery_candidate(self.hass, discovery)" in hassio
    assert "async_step_hassio_add_supplemental_confirm" not in source
    assert "async_step_add_discovered_rest_gateway" in source
    assert "gateway_provider_conflicts_with_dkb_csv" not in hassio
    assert "async_step_hassio_migrate_dkb_csv_confirm" not in source


def test_manual_and_internal_discovered_gateway_paths_have_no_legacy_dkb_collision_rule() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    discovered = _step(
        source,
        "async_step_add_discovered_rest_gateway_details",
        "async_step_add_rest_gateway",
    )
    manual = _step(source, "async_step_add_rest_gateway", "async_step_remove_rest_gateway")
    assert "gateway_provider_conflicts_with_dkb_csv" not in discovered
    assert "gateway_provider_conflicts_with_dkb_csv" not in manual
    assert "supplemental_dkb_csv_paths" not in source
