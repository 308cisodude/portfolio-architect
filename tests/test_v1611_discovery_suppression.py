"""Regression contract for v1.61.1 supplemental Supervisor discovery suppression."""

from __future__ import annotations

import ast
import asyncio

import pytest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
CONFIG_FLOW = COMPONENT / "config_flow.py"


def _function_node(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    return child
    raise AssertionError(f"function {name!r} not found")


def _compile_function(source: str, name: str, namespace: dict[str, object]):
    tree = ast.parse(source)
    node = _function_node(tree, name)
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), node],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    exec(compile(module, str(CONFIG_FLOW), "exec"), namespace)
    return namespace[name]



@pytest.mark.parametrize("provider_id", ["dkb", "trade_republic", "generic_csv"])
def test_fresh_gateway_discovery_waits_for_integration_owned_initialization(provider_id: str) -> None:
    """v1.62.5 supersedes discovery-owned bootstrap without losing candidates."""
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    remembered: list[object] = []
    discovery = SimpleNamespace(provider_id=provider_id, hostname=f"{provider_id}.invalid")

    class FakeDiscoveryParser:
        @staticmethod
        def from_mapping(mapping):
            assert mapping == {"provider_id": provider_id}
            return discovery

    class FakeConfigEntries:
        def async_entries(self, domain):
            assert domain == "portfolio_architect"
            return []

    class FakeSelf:
        hass = SimpleNamespace(config_entries=FakeConfigEntries())

        def async_abort(self, *, reason):
            return {"type": "abort", "reason": reason}

    async_step = _compile_function(
        source,
        "async_step_hassio",
        {
            "GatewayTlsDiscovery": FakeDiscoveryParser,
            "PortfolioRestError": RuntimeError,
            "DOMAIN": "portfolio_architect",
            "CONF_SOURCE_TYPE": "source_type",
            "SOURCE_TYPE_REST_API": "rest_api",
            "CONF_REST_ENDPOINT_URL": "rest_endpoint_url",
            "CONF_SUPPLEMENTAL_REST_SOURCES": "supplemental_rest_sources",
            "GATEWAY_PROVIDER_COMDIRECT": "comdirect",
            "RestSourceConfig": object,
            "SupplementalRestSourceConfig": object,
            "urlsplit": urlsplit,
            "_remember_hassio_discovery_candidate": lambda hass, item: remembered.append(item),
            "_forget_hassio_discovery_candidate": lambda hass, provider_id: None,
        },
    )
    result = asyncio.run(
        async_step(FakeSelf(), SimpleNamespace(config={"provider_id": provider_id}))
    )
    assert result == {"type": "abort", "reason": "pa_not_initialized"}
    assert remembered == [discovery]
    assert "async_set_unique_id" not in ast.get_source_segment(
        source, _function_node(ast.parse(source), "async_step_hassio")
    )


def test_multiple_preinitialization_discoveries_remain_candidates_without_creating_pa() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    candidates: dict[str, object] = {}

    class FakeDiscoveryParser:
        @staticmethod
        def from_mapping(mapping):
            provider_id = str(mapping["provider_id"])
            return SimpleNamespace(provider_id=provider_id, hostname=f"{provider_id}.invalid")

    class FakeConfigEntries:
        def async_entries(self, domain):
            assert domain == "portfolio_architect"
            return []

    class FakeSelf:
        hass = SimpleNamespace(config_entries=FakeConfigEntries())

        def async_abort(self, *, reason):
            return {"type": "abort", "reason": reason}

    def remember(hass, discovery):
        candidates[discovery.provider_id] = discovery

    async_step = _compile_function(
        source,
        "async_step_hassio",
        {
            "GatewayTlsDiscovery": FakeDiscoveryParser,
            "PortfolioRestError": RuntimeError,
            "DOMAIN": "portfolio_architect",
            "CONF_SOURCE_TYPE": "source_type",
            "SOURCE_TYPE_REST_API": "rest_api",
            "CONF_REST_ENDPOINT_URL": "rest_endpoint_url",
            "CONF_SUPPLEMENTAL_REST_SOURCES": "supplemental_rest_sources",
            "GATEWAY_PROVIDER_COMDIRECT": "comdirect",
            "RestSourceConfig": object,
            "SupplementalRestSourceConfig": object,
            "urlsplit": urlsplit,
            "_remember_hassio_discovery_candidate": remember,
            "_forget_hassio_discovery_candidate": lambda hass, provider_id: None,
        },
    )

    for provider_id in ("dkb", "trade_republic"):
        result = asyncio.run(
            async_step(FakeSelf(), SimpleNamespace(config={"provider_id": provider_id}))
        )
        assert result == {"type": "abort", "reason": "pa_not_initialized"}
    assert set(candidates) == {"dkb", "trade_republic"}


def test_comdirect_can_be_remembered_as_supplemental_when_another_provider_is_primary() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    remembered: list[object] = []
    discovery = SimpleNamespace(
        provider_id="comdirect",
        matches_comdirect_slug_successor=lambda endpoint: False,
        matches_legacy_endpoint=lambda endpoint: False,
    )

    class FakeDiscoveryParser:
        @staticmethod
        def from_mapping(mapping):
            assert mapping == {"provider_id": "comdirect"}
            return discovery

    entry = SimpleNamespace(
        data={"source_type": "rest_api", "rest_endpoint_url": "https://dkb.invalid/api/v1/portfolio"},
        options={"supplemental_rest_sources": []},
    )

    class FakeConfigEntries:
        def async_entries(self, domain):
            assert domain == "portfolio_architect"
            return [entry]

    class FakeSelf:
        hass = SimpleNamespace(config_entries=FakeConfigEntries())

        def async_abort(self, *, reason):
            return {"type": "abort", "reason": reason}

    async_step = _compile_function(
        source,
        "async_step_hassio",
        {
            "GatewayTlsDiscovery": FakeDiscoveryParser,
            "PortfolioRestError": RuntimeError,
            "DOMAIN": "portfolio_architect",
            "CONF_SOURCE_TYPE": "source_type",
            "SOURCE_TYPE_REST_API": "rest_api",
            "CONF_REST_ENDPOINT_URL": "rest_endpoint_url",
            "CONF_SUPPLEMENTAL_REST_SOURCES": "supplemental_rest_sources",
            "GATEWAY_PROVIDER_COMDIRECT": "comdirect",
            "RestSourceConfig": object,
            "SupplementalRestSourceConfig": object,
            "urlsplit": urlsplit,
            "_remember_hassio_discovery_candidate": lambda hass, item: remembered.append(item),
            "_forget_hassio_discovery_candidate": lambda hass, provider_id: None,
        },
    )
    result = asyncio.run(
        async_step(FakeSelf(), SimpleNamespace(config={"provider_id": "comdirect"}))
    )
    assert result == {"type": "abort", "reason": "tls_discovery_not_applicable"}
    assert remembered == [discovery]


def test_bootstrap_confirmation_and_supplemental_filter_are_provider_neutral() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    confirm = source.split("async def async_step_hassio_confirm", 1)[1].split(
        "async def _async_migrate_primary_tls", 1
    )[0]
    first_source = source.split("async def _async_commit_first_source", 1)[1].split(
        "async def async_step_add_discovered_primary_rest_gateway", 1
    )[0]
    helper = source.split("def _discovered_supplemental_gateways", 1)[1].split(
        "async def _async_validate_primary_candidate", 1
    )[0]
    assert "GATEWAY_PROVIDER_COMDIRECT" not in confirm
    assert "tls_discovery_not_primary" not in source
    assert 'async_abort(reason="pa_not_initialized")' in confirm
    assert "_forget_hassio_discovery_candidate(self.hass, health.provider_id)" in first_source
    assert "GATEWAY_PROVIDER_COMDIRECT" not in helper
    assert "provider_id not in configured" in helper

def test_existing_pa_entry_suppresses_top_level_supplemental_discovery_flow() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    assert "async def async_step_hassio_add_supplemental_confirm" not in source
    assert "return await self.async_step_hassio_add_supplemental_confirm()" not in source

    remembered: list[object] = []
    discovery = SimpleNamespace(
        provider_id="dkb",
        matches_comdirect_slug_successor=lambda endpoint: False,
        matches_legacy_endpoint=lambda endpoint: False,
    )

    class FakeDiscoveryParser:
        @staticmethod
        def from_mapping(mapping):
            assert mapping == {"provider_id": "dkb"}
            return discovery

    entry = SimpleNamespace(
        data={"source_type": "rest_api", "rest_endpoint_url": "https://comdirect.invalid/api/v1/portfolio"},
        options={"supplemental_rest_sources": []},
    )

    class FakeConfigEntries:
        def async_entries(self, domain):
            assert domain == "portfolio_architect"
            return [entry]

    class FakeSelf:
        hass = SimpleNamespace(config_entries=FakeConfigEntries())

        def async_abort(self, *, reason):
            return {"type": "abort", "reason": reason}

    async_step = _compile_function(
        source,
        "async_step_hassio",
        {
            "GatewayTlsDiscovery": FakeDiscoveryParser,
            "PortfolioRestError": RuntimeError,
            "DOMAIN": "portfolio_architect",
            "CONF_SOURCE_TYPE": "source_type",
            "SOURCE_TYPE_REST_API": "rest_api",
            "CONF_REST_ENDPOINT_URL": "rest_endpoint_url",
            "CONF_SUPPLEMENTAL_REST_SOURCES": "supplemental_rest_sources",
            "GATEWAY_PROVIDER_COMDIRECT": "comdirect",
            "RestSourceConfig": object,
            "SupplementalRestSourceConfig": object,
            "urlsplit": urlsplit,
            "_remember_hassio_discovery_candidate": lambda hass, item: remembered.append(item),
            "_forget_hassio_discovery_candidate": lambda hass, provider_id: None,
        },
    )
    result = asyncio.run(
        async_step(FakeSelf(), SimpleNamespace(config={"provider_id": "dkb"}))
    )
    assert result == {"type": "abort", "reason": "tls_discovery_not_applicable"}
    assert remembered == [discovery]


def test_discovery_candidates_are_deduplicated_by_immutable_provider_id() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    namespace: dict[str, object] = {
        "Any": object,
        "GatewayTlsDiscovery": object,
        "_HASSIO_DISCOVERY_CANDIDATES_DATA_KEY": "portfolio_architect_hassio_discovery_candidates",
    }
    get_candidates = _compile_function(source, "_hassio_discovery_candidates", namespace)
    namespace["_hassio_discovery_candidates"] = get_candidates
    remember = _compile_function(source, "_remember_hassio_discovery_candidate", namespace)

    hass = SimpleNamespace(data={})
    first = SimpleNamespace(provider_id="dkb", ca_sha256="first")
    second = SimpleNamespace(provider_id="dkb", ca_sha256="second")
    other = SimpleNamespace(provider_id="trade_republic", ca_sha256="third")
    remember(hass, first)
    remember(hass, second)
    remember(hass, other)

    candidates = get_candidates(hass)
    assert set(candidates) == {"dkb", "trade_republic"}
    assert candidates["dkb"] is second
    assert candidates["trade_republic"] is other


def test_discovered_gateway_adoption_lives_only_under_existing_options_flow() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    menu = source.split("async def async_step_rest_gateways", 1)[1].split(
        "async def async_step_edit_rest_gateway", 1
    )[0]
    details = source.split("async def async_step_add_discovered_rest_gateway_details", 1)[1].split(
        "async def async_step_add_rest_gateway", 1
    )[0]

    assert 'menu.insert(0, "add_discovered_rest_gateway")' in menu
    assert 'menu = ["add_rest_gateway"]' in menu
    assert "CONF_REST_API_TOKEN" in details
    assert "discovery.endpoint_url" in details
    assert "discovery.ca_certificate" in details
    assert "health.provider_id != discovery.provider_id" in details
    assert "health.snapshot_sha256 != result.snapshot_sha256" in details
    assert "self.async_create_entry(data=options)" in details
    assert "async_update_entry" not in details
    assert "async_reload" not in details


def test_bilingual_copy_has_no_obsolete_top_level_supplemental_add_step() -> None:
    import json

    for language in ("en", "de"):
        payload = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        assert "hassio_add_supplemental_confirm" not in payload["config"]["step"]
        assert "tls_supplemental_added" not in payload["config"]["abort"]
        assert "tls_discovery_not_primary" not in payload["config"]["abort"]
        assert "{provider_id}" in payload["config"]["step"]["hassio_confirm"]["description"]
        assert (
            payload["options"]["step"]["rest_gateways"]["menu_options"][
                "add_discovered_rest_gateway"
            ]
        )
        details = payload["options"]["step"]["add_discovered_rest_gateway_details"]
        assert "provider_id" in details["description"]
        assert "endpoint" in details["description"]
        assert "ca_sha256" in details["description"]
        assert "no_discovered_rest_gateways" in payload["options"]["abort"]
