"""Regression contracts for v1.63.0 first-run reload and CA async hygiene."""

from __future__ import annotations

import ast
import asyncio
import importlib
from pathlib import Path
import ssl
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
INIT = COMPONENT / "__init__.py"
REST = COMPONENT / "rest_client.py"
CONFIG_FLOW = COMPONENT / "config_flow.py"


def _isolated_unload_function():
    """Compile the exact async_unload_entry implementation without HA imports."""
    tree = ast.parse(INIT.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_unload_entry"
    )
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            function,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace = {"PLATFORMS": ("sensor", "binary_sensor", "date")}
    exec(compile(module, str(INIT), "exec"), namespace)
    return namespace["async_unload_entry"], namespace["PLATFORMS"]


class _Entry:
    def __init__(self, runtime_data):
        self.runtime_data = runtime_data


class _ConfigEntries:
    def __init__(self):
        self.calls: list[tuple[object, tuple[str, ...]]] = []

    async def async_unload_platforms(self, entry, platforms):
        self.calls.append((entry, platforms))
        return True


class _Hass:
    def __init__(self):
        self.config_entries = _ConfigEntries()


def test_setup_required_to_configured_reload_unloads_trivially_without_runtime() -> None:
    unload, _platforms = _isolated_unload_function()
    hass = _Hass()
    entry = _Entry(None)
    assert asyncio.run(unload(hass, entry)) is True
    assert hass.config_entries.calls == []


def test_configured_runtime_still_unloads_forwarded_platforms() -> None:
    unload, platforms = _isolated_unload_function()
    hass = _Hass()
    entry = _Entry(object())
    assert asyncio.run(unload(hass, entry)) is True
    assert hass.config_entries.calls == [(entry, platforms)]


def _load_rest_client():
    """Load rest_client with only the Home Assistant type boundary stubbed."""
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


def test_ca_normalization_never_builds_or_loads_an_ssl_context(monkeypatch) -> None:
    rest = _load_rest_client()
    syntactically_valid_pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "QUJD\n"
        "-----END CERTIFICATE-----\n"
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("SSL context creation must not occur during normalization")

    monkeypatch.setattr(ssl, "create_default_context", forbidden)
    assert rest.normalise_rest_ca_certificate(syntactically_valid_pem) == syntactically_valid_pem


def test_semantic_private_ca_validation_remains_fail_closed_in_ssl_context() -> None:
    rest = _load_rest_client()
    syntactically_valid_but_not_x509 = (
        "-----BEGIN CERTIFICATE-----\n"
        "QUJD\n"
        "-----END CERTIFICATE-----\n"
    )
    normalized = rest.normalise_rest_ca_certificate(syntactically_valid_but_not_x509)
    config = rest.RestSourceConfig(
        "https://local-portfolio-architect-gateway:8787/api/v1/portfolio",
        "x" * 32,
        normalized,
    )
    with pytest.raises(rest.PortfolioRestTlsError, match="trust configuration is invalid"):
        rest._rest_ssl_context(config)


def test_ssl_context_construction_remains_executor_bound_for_health_and_snapshot() -> None:
    source = REST.read_text(encoding="utf-8")
    normalizer = source.split("def normalise_rest_ca_certificate", 1)[1].split(
        "def _certificate_sha256", 1
    )[0]
    assert "create_default_context" not in normalizer
    assert "load_verify_locations" not in normalizer
    assert "ssl.PEM_cert_to_DER_cert" in normalizer
    assert source.count("await hass.async_add_executor_job(_rest_ssl_context, config)") == 2


def test_initial_setup_still_reloads_immediately_after_marking_configured() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    policy = source.split("async def async_step_initial_setup_policy", 1)[1].split(
        "@staticmethod", 1
    )[0]
    assert "data[CONF_SETUP_STATE] = SETUP_STATE_CONFIGURED" in policy
    assert "async_update_entry(self.config_entry, data=data)" in policy
    assert "await self.hass.config_entries.async_reload(self.config_entry.entry_id)" in policy
