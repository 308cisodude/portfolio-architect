"""Executable DNS-pinning regression tests for v1.17.1."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import socket
import sys
import types

from aiohttp import web
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

    class HomeAssistant:  # pragma: no cover - type placeholder only
        pass

    core.HomeAssistant = HomeAssistant
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.core"] = core
    return importlib.import_module("custom_components.portfolio_architect.rest_client")


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


def test_pinned_session_connects_to_validated_ip_and_preserves_host_header() -> None:
    rest = _load_rest_client()

    async def scenario() -> tuple[int, str]:
        seen: dict[str, str] = {}

        async def handler(request: web.Request) -> web.Response:
            seen["host"] = request.host
            return web.Response(text="ok")

        app = web.Application()
        app.router.add_get("/healthz", handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        try:
            server = site._server
            assert server is not None
            port = server.sockets[0].getsockname()[1]
            endpoint = rest.ResolvedLocalEndpoint(
                hostname="gateway.test",
                port=port,
                addresses=(
                    rest.ResolvedLocalAddress(socket.AF_INET, "127.0.0.1"),
                ),
            )
            async with rest._async_pinned_local_session(endpoint) as session:
                async with session.get(
                    f"http://gateway.test:{port}/healthz",
                    allow_redirects=False,
                ) as response:
                    await response.text()
                    return response.status, seen["host"]
        finally:
            await runner.cleanup()

    status, host = asyncio.run(scenario())
    assert status == 200
    assert host.startswith("gateway.test:")


def test_hostname_comparison_uses_one_idna_canonical_form() -> None:
    rest = _load_rest_client()
    assert rest._canonical_hostname("Täst.Local.") == "xn--tst-qla.local"
