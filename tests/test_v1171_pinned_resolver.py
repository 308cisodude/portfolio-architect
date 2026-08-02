"""Dependency-free DNS-pinning regression tests for v1.17.1."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import socket
import sys
import types

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def _aiohttp_stub() -> tuple[types.ModuleType, types.ModuleType]:
    """Return the smallest aiohttp contract used by rest_client.

    Home Assistant supplies aiohttp at runtime. These unit tests deliberately
    avoid pulling a second web stack into the publication-only CI environment;
    they verify the resolver and connector configuration at the API boundary.
    """
    aiohttp = types.ModuleType("aiohttp")
    abc = types.ModuleType("aiohttp.abc")

    class AbstractResolver:
        pass

    class ResolveResult(dict):
        def __init__(self, **values):
            super().__init__(values)

    class ClientError(Exception):
        pass

    class ClientResponse:
        pass

    class ClientTimeout:
        def __init__(self, *, total):
            self.total = total

    class DummyCookieJar:
        pass

    class TCPConnector:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class ClientSession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return False

    abc.AbstractResolver = AbstractResolver
    abc.ResolveResult = ResolveResult
    aiohttp.ClientError = ClientError
    aiohttp.ClientResponse = ClientResponse
    aiohttp.ClientSession = ClientSession
    aiohttp.ClientTimeout = ClientTimeout
    aiohttp.DummyCookieJar = DummyCookieJar
    aiohttp.TCPConnector = TCPConnector
    aiohttp.abc = abc
    return aiohttp, abc


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

    previous_aiohttp = {
        name: module
        for name, module in sys.modules.items()
        if name == "aiohttp" or name.startswith("aiohttp.")
    }
    for name in tuple(previous_aiohttp):
        sys.modules.pop(name, None)
    aiohttp, abc = _aiohttp_stub()
    sys.modules["aiohttp"] = aiohttp
    sys.modules["aiohttp.abc"] = abc
    try:
        return importlib.import_module("custom_components.portfolio_architect.rest_client")
    finally:
        sys.modules.pop("aiohttp", None)
        sys.modules.pop("aiohttp.abc", None)
        sys.modules.update(previous_aiohttp)


class _FakeHass:
    def __init__(self, result):
        self._result = result

    async def async_add_executor_job(self, _function, *_args):
        return self._result


def test_validation_returns_the_exact_prevalidated_dns_answer() -> None:
    rest = _load_rest_client()
    addresses = (
        rest.ResolvedLocalAddress(socket.AF_INET, "192.168.109.178"),
        rest.ResolvedLocalAddress(socket.AF_INET6, "fd00::178"),
    )
    endpoint = asyncio.run(
        rest.async_validate_local_rest_endpoint(
            _FakeHass(addresses), "https://Gateway.Internal.:8123/api/v1/portfolio"
        )
    )
    assert endpoint.hostname == "gateway.internal"
    assert endpoint.port == 8123
    assert endpoint.addresses == addresses


def test_validation_rejects_mixed_private_and_public_dns_answers() -> None:
    rest = _load_rest_client()
    addresses = (
        rest.ResolvedLocalAddress(socket.AF_INET, "192.168.109.178"),
        rest.ResolvedLocalAddress(socket.AF_INET, "203.0.113.7"),
    )
    with pytest.raises(rest.PortfolioRestError, match="resolve exclusively"):
        asyncio.run(
            rest.async_validate_local_rest_endpoint(
                _FakeHass(addresses), "http://gateway.internal:8080/api"
            )
        )


def test_pinned_resolver_never_performs_or_accepts_a_second_resolution() -> None:
    rest = _load_rest_client()
    endpoint = rest.ResolvedLocalEndpoint(
        hostname="gateway.internal",
        port=8123,
        addresses=(
            rest.ResolvedLocalAddress(socket.AF_INET, "192.168.109.178"),
        ),
    )
    resolver = rest._PinnedLocalResolver(endpoint)
    results = asyncio.run(
        resolver.resolve("Gateway.Internal.", 8123, socket.AF_UNSPEC)
    )
    assert [result["host"] for result in results] == ["192.168.109.178"]

    with pytest.raises(OSError, match="unexpected host or port"):
        asyncio.run(resolver.resolve("attacker.example", 8123, socket.AF_UNSPEC))
    with pytest.raises(OSError, match="unexpected host or port"):
        asyncio.run(resolver.resolve("gateway.internal", 443, socket.AF_UNSPEC))


def test_pinned_session_uses_only_the_validated_resolver_and_hardened_options() -> None:
    rest = _load_rest_client()
    endpoint = rest.ResolvedLocalEndpoint(
        hostname="gateway.test",
        port=8123,
        addresses=(
            rest.ResolvedLocalAddress(socket.AF_INET, "127.0.0.1"),
        ),
    )

    async def scenario():
        async with rest._async_pinned_local_session(endpoint) as session:
            return session

    session = asyncio.run(scenario())
    connector = session.kwargs["connector"]
    resolver = connector.kwargs["resolver"]

    assert isinstance(resolver, rest._PinnedLocalResolver)
    assert resolver._endpoint == endpoint
    assert connector.kwargs == {
        "family": socket.AF_UNSPEC,
        "resolver": resolver,
        "use_dns_cache": False,
        "force_close": True,
        "limit": 1,
    }
    assert session.kwargs["connector_owner"] is True
    assert session.kwargs["trust_env"] is False
    assert session.kwargs["cookie_jar"].__class__.__name__ == "DummyCookieJar"


def test_hostname_comparison_uses_one_idna_canonical_form() -> None:
    rest = _load_rest_client()
    assert rest._canonical_hostname("Täst.Local.") == "xn--tst-qla.local"
