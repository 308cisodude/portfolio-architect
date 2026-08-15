"""Publication-test bootstrap for Home Assistant runtime dependencies.

The production integration uses aiohttp supplied by Home Assistant. The
publication-only CI lock intentionally contains only the tools needed to run
this repository's tests and release checks, so parser-only tests receive a
small import-compatible stub when aiohttp is absent.
"""

from __future__ import annotations

import sys
import types


def _install_aiohttp_stub_if_missing() -> None:
    try:
        __import__("aiohttp")
        return
    except ModuleNotFoundError:
        pass

    aiohttp = types.ModuleType("aiohttp")
    abc = types.ModuleType("aiohttp.abc")

    class AbstractResolver:
        pass

    class ResolveResult(dict):
        def __init__(self, **values):
            super().__init__(values)

    class ClientError(Exception):
        pass

    class ClientConnectorCertificateError(ClientError):
        pass

    class ClientConnectorSSLError(ClientError):
        pass

    class ClientSSLError(ClientError):
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
    aiohttp.ClientConnectorCertificateError = ClientConnectorCertificateError
    aiohttp.ClientConnectorSSLError = ClientConnectorSSLError
    aiohttp.ClientSSLError = ClientSSLError
    aiohttp.ClientResponse = ClientResponse
    aiohttp.ClientSession = ClientSession
    aiohttp.ClientTimeout = ClientTimeout
    aiohttp.DummyCookieJar = DummyCookieJar
    aiohttp.TCPConnector = TCPConnector
    aiohttp.abc = abc

    sys.modules["aiohttp"] = aiohttp
    sys.modules["aiohttp.abc"] = abc


_install_aiohttp_stub_if_missing()
