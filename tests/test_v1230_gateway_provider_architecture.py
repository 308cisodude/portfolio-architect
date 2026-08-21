"""Regression contracts for v1.23.0 provider-aware Gateway architecture."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import types

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
GATEWAY = ROOT / "gateway" / "src" / "portfolio_architect_gateway"
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway"


def _load_rest_client():
    for name in tuple(sys.modules):
        if name == "custom_components" or name.startswith(
            "custom_components.portfolio_architect"
        ) or name == "homeassistant" or name.startswith("homeassistant."):
            sys.modules.pop(name, None)

    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]
    package = types.ModuleType("custom_components.portfolio_architect")
    package.__path__ = [str(COMPONENT)]
    sys.modules["custom_components"] = custom_components
    sys.modules["custom_components.portfolio_architect"] = package

    homeassistant = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")

    class HomeAssistant:  # pragma: no cover - type placeholder only
        pass

    core.HomeAssistant = HomeAssistant
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.core"] = core
    return importlib.import_module("custom_components.portfolio_architect.rest_client")


def _health_v6_payload() -> dict:
    return {
        "gateway_version": "1.41.0",
        "status": "ok",
        "snapshot_available": True,
        "snapshot_generated_at": "2026-08-13T12:00:00+00:00",
        "last_refresh_success": "2026-08-13T12:00:05+00:00",
        "reauthentication_required": False,
        "last_error": None,
        "health_schema_version": 6,
        "snapshot_sha256": "a" * 64,
        "snapshot_position_count": 13,
        "poll_interval_seconds": 900,
        "max_cached_snapshot_age_seconds": 604800,
        "operating_mode": "live",
        "last_refresh_attempt": "2026-08-13T12:00:04+00:00",
        "consecutive_refresh_failures": 0,
        "snapshot_age_seconds": 5,
        "snapshot_expires_in_seconds": 604795,
        "refresh_in_progress": False,
        "last_refresh_duration_ms": 1234,
        "last_refresh_trigger": "scheduled",
        "next_refresh_due_at": "2026-08-13T12:15:00+00:00",
        "manual_refresh_min_interval_seconds": 60,
        "last_refresh_failure_at": None,
        "last_refresh_failure_class": None,
        "recommended_action": "none",
        "retry_after_seconds": None,
        "provider_id": "comdirect",
    }


def test_common_gateway_server_depends_on_provider_protocol_not_comdirect() -> None:
    server = (GATEWAY / "server.py").read_text(encoding="utf-8")
    provider = (GATEWAY / "provider.py").read_text(encoding="utf-8")
    comdirect = (GATEWAY / "comdirect.py").read_text(encoding="utf-8")

    assert "from .comdirect import ComdirectClient" not in server
    assert "PortfolioProvider" in server
    assert "normalise_provider_id" in server
    assert "class PortfolioProvider(Protocol)" in provider
    assert "def fetch_snapshot(self) -> PortfolioSnapshot" in provider
    assert "def provider_id(self) -> str" in provider
    assert "def poll_interval_seconds(self) -> int" in provider
    assert 'return "comdirect"' in comdirect
    assert "return self._config.poll_interval_seconds" in comdirect


def test_health_v6_adds_only_bounded_provider_identity() -> None:
    rest_client = _load_rest_client()
    health = rest_client._parse_gateway_health(_health_v6_payload())
    assert health.health_schema_version == 6
    assert health.provider_id == "comdirect"

    invalid = _health_v6_payload()
    invalid["provider_id"] = "Comdirect Account 42"
    with pytest.raises(rest_client.PortfolioRestError, match="provider ID"):
        rest_client._parse_gateway_health(invalid)


def test_health_client_negotiates_v6_with_v5_to_v1_fallbacks() -> None:
    source = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    assert 'HEALTH_V6_MEDIA_TYPE: Final = "application/vnd.portfolio-architect.health+json;version=6"' in source
    assert '"requested_health_schema_version": 6' in source
    for version in range(2, 7):
        assert f"HEALTH_V{version}_MEDIA_TYPE" in source
    assert '"application/json"' in source


def test_comdirect_app_is_distinct_in_ui_without_slug_or_data_migration() -> None:
    config = yaml.safe_load((APP / "config.yaml").read_text(encoding="utf-8"))
    assert config["name"] == "Portfolio Architect Gateway — Comdirect"
    assert config["slug"] == "portfolio_architect_gateway"
    assert config["version"] == "1.41.0"
    assert config["stage"] == "stable"

    app = (APP / "src" / "portfolio_architect_gateway" / "app.py").read_text(
        encoding="utf-8"
    )
    assert 'APP_DATA_DIRECTORY: Final = Path("/data/gateway")' in app
    assert 'health_document(version=6)' in app


def test_gateway_status_and_diagnostics_expose_only_provider_id() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    diagnostics = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
    assert '"provider_id": health.provider_id if health else None' in sensor
    assert '"provider_id": coordinator.gateway_health.provider_id' in diagnostics
    for forbidden in ("provider_account_id", "account_id", "depot_id"):
        assert f'"{forbidden}": coordinator.gateway_health' not in diagnostics


def test_provider_roadmap_keeps_tr_import_after_distinct_gateway_apps() -> None:
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "GATEWAY-PROVIDERS.md").read_text(encoding="utf-8")
    assert roadmap.index("Gateway — Comdirect") < roadmap.index("Gateway — DKB")
    assert roadmap.index("Gateway — DKB") < roadmap.index("Gateway — Trade Republic")
    assert roadmap.index("Gateway — Trade Republic") < roadmap.index("Trade Republic statement import")
    assert "portfolio_architect_gateway" in architecture
    assert "portfolio_architect_gateway_dkb" in architecture
    assert "portfolio_architect_gateway_trade_republic" in architecture
    assert "No DKB or Trade Republic acquisition runtime is shipped by v1.24.0" in architecture


def test_wire_versions_are_intentional() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.41.0"
    assert "schema version 9" in (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    release_notes = (ROOT / "docs" / "RELEASE-NOTES.md").read_text(encoding="utf-8")
    assert "REST portfolio schema 1" in release_notes
    assert "Gateway health schema 6" in release_notes
    assert "No trading, order, transfer, payment, or transaction-history capability" in release_notes
