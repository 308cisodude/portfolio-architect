"""Regression contract for v1.61.2 primary Gateway identity context."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

ROOT = Path(__file__).parents[1]
CONFIG_FLOW = ROOT / "custom_components" / "portfolio_architect" / "config_flow.py"


def _method_node(tree: ast.Module, name: str) -> ast.AsyncFunctionDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, ast.AsyncFunctionDef) and child.name == name:
                    return child
    raise AssertionError(f"method {name!r} not found")


def _compile_method(source: str, name: str, namespace: dict[str, object]):
    tree = ast.parse(source)
    node = _method_node(tree, name)
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            node,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    exec(compile(module, str(CONFIG_FLOW), "exec"), namespace)
    return namespace[name]


class PortfolioRestError(Exception):
    """Minimal compiled-method transport failure."""


class PortfolioRestAuthenticationError(PortfolioRestError):
    """Minimal compiled-method authentication failure."""


class PortfolioRestTlsError(PortfolioRestError):
    """Minimal compiled-method TLS failure."""


class FakeRestSourceConfig:
    def __init__(self, endpoint_url: str, api_token: str = "token", tls_ca_certificate: str | None = "ca"):
        self.endpoint_url = endpoint_url
        self.api_token = api_token
        self.tls_ca_certificate = tls_ca_certificate

    @classmethod
    def from_mapping(cls, mapping):
        return cls(
            mapping["rest_endpoint_url"],
            mapping.get("rest_api_token", "token"),
            mapping.get("rest_tls_ca_certificate", "ca"),
        )


def _namespace(fetch_health):
    return {
        "Any": object,
        "ConfigFlowResult": dict,
        "CONF_SOURCE_TYPE": "source_type",
        "SOURCE_TYPE_REST_API": "rest_api",
        "CONF_REST_ENDPOINT_URL": "rest_endpoint_url",
        "CONF_REST_API_TOKEN": "rest_api_token",
        "CONF_REST_TLS_CA_CERTIFICATE": "rest_tls_ca_certificate",
        "RestSourceConfig": FakeRestSourceConfig,
        "PortfolioRestError": PortfolioRestError,
        "PortfolioRestAuthenticationError": PortfolioRestAuthenticationError,
        "PortfolioRestTlsError": PortfolioRestTlsError,
        "async_fetch_gateway_health": fetch_health,
        "async_fetch_rest_snapshot": None,
        "urlsplit": urlsplit,
        "_rest_source_schema": lambda: object(),
    }


def test_runtime_identity_keeps_primary_form_self_identifying_when_fresh_health_call_fails() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")

    async def fetch_health(hass, config):
        raise PortfolioRestError("transient")

    method = _compile_method(source, "async_step_primary_rest_gateway", _namespace(fetch_health))
    entry = SimpleNamespace(
        data={
            "source_type": "rest_api",
            "rest_endpoint_url": "https://comdirect.invalid/api/v1/portfolio",
            "rest_api_token": "token",
            "rest_tls_ca_certificate": "ca",
        },
        options={},
        runtime_data=SimpleNamespace(
            gateway_health=SimpleNamespace(provider_id="comdirect")
        ),
    )

    class FakeSelf:
        config_entry = entry
        hass = SimpleNamespace()

        def _supplemental_rest_sources(self):
            return []

        def add_suggested_values_to_schema(self, schema, suggested):
            return (schema, suggested)

        def async_show_form(self, **kwargs):
            return kwargs

        def async_abort(self, *, reason):
            return {"type": "abort", "reason": reason}

    result = asyncio.run(method(FakeSelf(), None))
    assert result["step_id"] == "primary_rest_gateway"
    assert result["description_placeholders"]["provider"] == "Comdirect"
    assert result["description_placeholders"]["endpoint"] == entry.data["rest_endpoint_url"]


def test_changed_primary_endpoint_still_fails_closed_when_current_fresh_identity_is_unavailable() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    calls = 0

    async def fetch_health(hass, config):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PortfolioRestError("current primary health temporarily unavailable")
        return SimpleNamespace(
            health_schema_version=9,
            provider_id="comdirect",
            status="ok",
            reauthentication_required=False,
            snapshot_available=True,
        )

    namespace = _namespace(fetch_health)
    method = _compile_method(source, "async_step_primary_rest_gateway", namespace)
    entry = SimpleNamespace(
        data={
            "source_type": "rest_api",
            "rest_endpoint_url": "https://old-comdirect.invalid/api/v1/portfolio",
            "rest_api_token": "old-token",
            "rest_tls_ca_certificate": "old-ca",
        },
        options={},
        runtime_data=SimpleNamespace(
            gateway_health=SimpleNamespace(provider_id="comdirect")
        ),
    )

    class FakeConfigEntries:
        def async_update_entry(self, *args, **kwargs):
            raise AssertionError("changed endpoint must not be saved without fresh current identity")

    class FakeSelf:
        config_entry = entry
        hass = SimpleNamespace(config_entries=FakeConfigEntries())

        def _supplemental_rest_sources(self):
            return []

        def _rest_edit_candidate(self, user_input, existing):
            return FakeRestSourceConfig(
                user_input["rest_endpoint_url"],
                user_input["rest_api_token"],
                "new-ca",
            )

        def add_suggested_values_to_schema(self, schema, suggested):
            return (schema, suggested)

        def async_show_form(self, **kwargs):
            return kwargs

        def async_create_entry(self, *, data):
            raise AssertionError("changed endpoint must fail closed")

        def async_abort(self, *, reason):
            return {"type": "abort", "reason": reason}

    result = asyncio.run(
        method(
            FakeSelf(),
            {
                "rest_endpoint_url": "https://new-comdirect.invalid/api/v1/portfolio",
                "rest_api_token": "new-token",
            },
        )
    )
    assert calls == 2
    assert result["errors"] == {"base": "invalid_rest_gateway"}
    assert result["description_placeholders"]["provider"] == "Comdirect"


def test_display_identity_and_save_verification_are_deliberately_separate() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    block = source.split("async def async_step_primary_rest_gateway", 1)[1].split(
        "async def async_step_rest_gateways", 1
    )[0]
    assert 'coordinator = getattr(self.config_entry, "runtime_data", None)' in block
    assert 'runtime_health = getattr(coordinator, "gateway_health", None)' in block
    assert "runtime_provider_id or current_provider_id or \"unknown\"" in block
    assert "if current_provider_id is None or health.provider_id != current_provider_id" in block
    assert "runtime_provider_id" not in block.split("if user_input is not None:", 1)[1].split(
        "provider_label =", 1
    )[0]
