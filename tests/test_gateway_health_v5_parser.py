"""Executable parser tests for Gateway health schema 5."""

from __future__ import annotations

from datetime import datetime
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


def _health_payload() -> dict:
    return {
        "gateway_version": "1.10.0",
        "status": "ok",
        "snapshot_available": True,
        "snapshot_generated_at": "2026-07-31T01:00:00+00:00",
        "last_refresh_success": "2026-07-31T01:00:05+00:00",
        "reauthentication_required": False,
        "last_error": None,
        "health_schema_version": 5,
        "snapshot_sha256": "a" * 64,
        "snapshot_position_count": 13,
        "poll_interval_seconds": 900,
        "max_cached_snapshot_age_seconds": 604800,
        "operating_mode": "live",
        "last_refresh_attempt": "2026-07-31T01:00:04+00:00",
        "consecutive_refresh_failures": 0,
        "snapshot_age_seconds": 5,
        "snapshot_expires_in_seconds": 604795,
        "refresh_in_progress": False,
        "last_refresh_duration_ms": 1234,
        "last_refresh_trigger": "scheduled",
        "next_refresh_due_at": "2026-07-31T01:15:00+00:00",
        "manual_refresh_min_interval_seconds": 60,
        "last_refresh_failure_at": None,
        "last_refresh_failure_class": None,
        "recommended_action": "none",
        "retry_after_seconds": None,
    }


def test_health_v5_parser_accepts_success_state() -> None:
    rest_client = _load_rest_client()
    health = rest_client._parse_gateway_health(_health_payload())
    assert health.health_schema_version == 5
    assert health.last_refresh_failure_at is None
    assert health.last_refresh_failure_class is None
    assert health.recommended_action == "none"
    assert health.retry_after_seconds is None


def test_health_v5_parser_accepts_classified_failure() -> None:
    rest_client = _load_rest_client()
    payload = _health_payload()
    payload.update(
        {
            "status": "degraded",
            "operating_mode": "last_known_good",
            "last_error": "RemoteApiError",
            "consecutive_refresh_failures": 3,
            "last_refresh_failure_at": "2026-07-31T01:14:00+00:00",
            "last_refresh_failure_class": "rate_limited",
            "recommended_action": "wait",
            "retry_after_seconds": 120,
        }
    )
    health = rest_client._parse_gateway_health(payload)
    assert health.last_refresh_failure_at == datetime.fromisoformat(
        "2026-07-31T01:14:00+00:00"
    )
    assert health.last_refresh_failure_class == "rate_limited"
    assert health.recommended_action == "wait"
    assert health.retry_after_seconds == 120


def test_health_v5_parser_rejects_stale_failure_fields_after_success() -> None:
    rest_client = _load_rest_client()
    payload = _health_payload()
    payload["last_refresh_failure_class"] = "transport_error"
    payload["recommended_action"] = "check_connectivity"
    payload["last_refresh_failure_at"] = "2026-07-31T01:14:00+00:00"
    with pytest.raises(rest_client.PortfolioRestError, match="retains failure"):
        rest_client._parse_gateway_health(payload)


def test_health_v5_parser_rejects_failure_without_guidance() -> None:
    rest_client = _load_rest_client()
    payload = _health_payload()
    payload.update(
        {
            "status": "degraded",
            "operating_mode": "last_known_good",
            "last_error": "GatewayError",
            "consecutive_refresh_failures": 1,
        }
    )
    with pytest.raises(rest_client.PortfolioRestError, match="lacks recovery"):
        rest_client._parse_gateway_health(payload)
