"""Regression coverage for v1.33.0 DKB Gateway discovery suppression."""

from __future__ import annotations

from pathlib import Path
import importlib.util
import re

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


def _csv_dkb_provider_id() -> str:
    source = (COMPONENT / "engine" / "importers.py").read_text(encoding="utf-8")
    match = re.search(r'^PROVIDER_DKB: Final = "([^"]+)"$', source, re.MULTILINE)
    assert match is not None
    return match.group(1)


def _step(source: str, name: str, next_name: str) -> str:
    return source.split(f"async def {name}", 1)[1].split(f"async def {next_name}", 1)[0]


def test_dkb_gateway_and_csv_use_intentionally_distinct_provider_ids() -> None:
    config = yaml.safe_load(
        (ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb" / "config.yaml").read_text(
            encoding="utf-8"
        )
    )
    provider_ids = _load_gateway_provider_ids()
    csv_provider_dkb = _csv_dkb_provider_id()
    assert provider_ids.GATEWAY_PROVIDER_DKB == "dkb"
    assert config["environment"]["PA_PROVIDER_ID"] == provider_ids.GATEWAY_PROVIDER_DKB
    assert csv_provider_dkb == "dkb_csv"
    assert provider_ids.GATEWAY_PROVIDER_DKB != csv_provider_dkb


def test_real_dkb_gateway_discovery_conflicts_with_existing_dkb_csv_scope() -> None:
    provider_ids = _load_gateway_provider_ids()
    configured_dkb_csv = ["portfolio/dkb/latest.csv"]
    assert provider_ids.gateway_provider_conflicts_with_dkb_csv("dkb", configured_dkb_csv) is True
    assert provider_ids.gateway_provider_conflicts_with_dkb_csv(
        provider_ids.GATEWAY_PROVIDER_DKB, configured_dkb_csv
    ) is True
    assert provider_ids.gateway_provider_conflicts_with_dkb_csv(
        _csv_dkb_provider_id(), configured_dkb_csv
    ) is False
    assert provider_ids.gateway_provider_conflicts_with_dkb_csv(
        provider_ids.GATEWAY_PROVIDER_DKB, []
    ) is False
    assert provider_ids.gateway_provider_conflicts_with_dkb_csv(
        "trade_republic", configured_dkb_csv
    ) is False


def test_hassio_discovery_aborts_dkb_gateway_before_offering_add_card() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    hassio = _step(source, "async_step_hassio", "async_step_hassio_confirm")
    conflict = "gateway_provider_conflicts_with_dkb_csv(\n            discovery.provider_id, raw_dkb_sources\n        )"
    assert conflict in hassio
    assert hassio.index(conflict) < hassio.index("async_step_hassio_add_supplemental_confirm")
    assert "discovery.provider_id == PROVIDER_DKB" not in hassio


def test_manual_and_discovered_supplemental_paths_share_same_dkb_collision_rule() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    discovered = _step(
        source,
        "async_step_hassio_add_supplemental_confirm",
        "_async_migrate_primary_tls",
    )
    manual = _step(source, "async_step_add_rest_gateway", "async_step_remove_rest_gateway")
    assert "gateway_provider_conflicts_with_dkb_csv(" in discovered
    assert "gateway_provider_conflicts_with_dkb_csv(" in manual
    assert "discovery.provider_id == PROVIDER_DKB" not in discovered
    assert "health.provider_id == PROVIDER_DKB" not in manual
