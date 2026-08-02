"""Executable parser tests for Gateway health schema 3."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


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
    helpers = types.ModuleType("homeassistant.helpers")
    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")

    class HomeAssistant:  # pragma: no cover - type placeholder only
        pass

    core.HomeAssistant = HomeAssistant
    aiohttp_client.async_get_clientsession = lambda _hass: None
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client

    return importlib.import_module("custom_components.portfolio_architect.rest_client")


def _health_payload(*, mode: str = "live", failures: int = 0) -> dict:
    snapshot_available = mode != "unavailable"
    return {
        "gateway_version": "1.8.0",
        "status": "ok" if mode == "live" else "degraded",
        "snapshot_available": snapshot_available,
        "snapshot_generated_at": (
            "2026-07-30T23:00:00+00:00" if snapshot_available else None
        ),
        "last_refresh_success": "2026-07-30T23:00:05+00:00",
        "reauthentication_required": mode == "reauthentication_required",
        "last_error": None if mode == "live" else "GatewayError",
        "health_schema_version": 3,
        "snapshot_sha256": "a" * 64 if snapshot_available else None,
        "snapshot_position_count": 13 if snapshot_available else None,
        "poll_interval_seconds": 900,
        "max_cached_snapshot_age_seconds": 604800,
        "operating_mode": mode,
        "last_refresh_attempt": "2026-07-30T23:00:05+00:00",
        "consecutive_refresh_failures": failures,
        "snapshot_age_seconds": 5 if snapshot_available else None,
        "snapshot_expires_in_seconds": 604795 if snapshot_available else None,
    }


def test_health_v3_parser_accepts_live_and_last_known_good() -> None:
    rest_client = _load_rest_client()
    live = rest_client._parse_gateway_health(_health_payload())
    assert live.health_schema_version == 3
    assert live.operating_mode == "live"
    assert live.consecutive_refresh_failures == 0
    assert live.snapshot_age_seconds == 5

    cached = rest_client._parse_gateway_health(
        _health_payload(mode="last_known_good", failures=2)
    )
    assert cached.status == "degraded"
    assert cached.operating_mode == "last_known_good"
    assert cached.consecutive_refresh_failures == 2


def test_health_v3_parser_rejects_inconsistent_live_state() -> None:
    rest_client = _load_rest_client()
    with pytest.raises(rest_client.PortfolioRestError, match="Live gateway"):
        rest_client._parse_gateway_health(_health_payload(failures=1))


def test_health_v3_parser_rejects_missing_failure_count() -> None:
    rest_client = _load_rest_client()
    payload = _health_payload(mode="last_known_good", failures=2)
    payload["consecutive_refresh_failures"] = None
    with pytest.raises(rest_client.PortfolioRestError, match="failure count"):
        rest_client._parse_gateway_health(payload)


def test_health_v3_parser_rejects_age_for_unavailable_snapshot() -> None:
    rest_client = _load_rest_client()
    payload = _health_payload(mode="unavailable", failures=2)
    payload["snapshot_age_seconds"] = 5
    with pytest.raises(rest_client.PortfolioRestError, match="age metadata"):
        rest_client._parse_gateway_health(payload)
