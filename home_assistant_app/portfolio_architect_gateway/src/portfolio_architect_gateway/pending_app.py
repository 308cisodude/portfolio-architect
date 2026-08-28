"""Minimal isolated provider-App shell used before acquisition support exists."""

from __future__ import annotations

from collections.abc import Callable

from dataclasses import dataclass
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import threading
from typing import Any, Final
from urllib.parse import urlsplit

from . import __version__
from .errors import ConfigurationError
from .models import PortfolioSnapshot
from .provider import normalise_provider_id
from .runtime_config import ServerConfig, ensure_api_token
from .server import GatewayState, create_server

_LOGGER = logging.getLogger(__name__)
OPTIONS_FILE: Final = Path("/data/options.json")
APP_DATA_DIRECTORY: Final = Path("/data/gateway")
INGRESS_BIND: Final = "0.0.0.0"
INGRESS_PORT: Final = 8099
GATEWAY_PORT: Final = 8787
MAX_HEADER_BYTES: Final = 32 * 1024


@dataclass(frozen=True, slots=True)
class PendingAppOptions:
    """Strict non-secret options for a provider shell."""

    max_cached_snapshot_age_seconds: int = 0
    health_endpoint_enabled: bool = True

    @classmethod
    def load(cls, path: Path = OPTIONS_FILE) -> "PendingAppOptions":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = {}
        except (OSError, UnicodeError, json.JSONDecodeError) as err:
            raise RuntimeError("Home Assistant App options are unreadable") from err
        if not isinstance(raw, dict):
            raise RuntimeError("Home Assistant App options must be an object")
        allowed = {"max_cached_snapshot_age_seconds", "health_endpoint_enabled"}
        if set(raw) - allowed:
            raise RuntimeError("Home Assistant App options contain unsupported keys")
        age = raw.get("max_cached_snapshot_age_seconds", 0)
        enabled = raw.get("health_endpoint_enabled", True)
        if isinstance(age, bool) or not isinstance(age, int) or not 0 <= age <= 2592000:
            raise RuntimeError("maximum cached snapshot age is outside the supported range")
        if not isinstance(enabled, bool):
            raise RuntimeError("health endpoint must be true or false")
        return cls(age, enabled)


class PendingProvider:
    """Fail-closed provider identity for an installable but not-yet-live App."""

    def __init__(self, provider_id: str) -> None:
        self._provider_id = normalise_provider_id(provider_id)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def poll_interval_seconds(self) -> int:
        return 86400

    def fetch_snapshot(self) -> PortfolioSnapshot:
        raise ConfigurationError("Provider acquisition is not implemented in this release")


def build_server_config(
    options: PendingAppOptions,
    data_directory: Path,
    *,
    tls_cert_file: Path | None = None,
    tls_key_file: Path | None = None,
) -> ServerConfig:
    return ServerConfig(
        bind="0.0.0.0",
        port=GATEWAY_PORT,
        api_token_file=data_directory / "gateway-api-token",
        snapshot_file=data_directory / "portfolio.json",
        max_cached_snapshot_age_seconds=options.max_cached_snapshot_age_seconds,
        tls_cert_file=tls_cert_file,
        tls_key_file=tls_key_file,
        health_endpoint_enabled=options.health_endpoint_enabled,
    )


class ProviderShellIngressServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        state: GatewayState,
        provider_name: str,
        api_token: str,
        allowed_sources: frozenset[str],
        require_user_header: bool,
        handler_class: type[BaseHTTPRequestHandler] | None = None,
    ) -> None:
        self.gateway_state = state
        self.provider_name = provider_name
        self.api_token = api_token
        self.allowed_sources = allowed_sources
        self.require_user_header = require_user_header
        super().__init__(address, handler_class or ProviderShellIngressHandler)


class ProviderShellIngressHandler(BaseHTTPRequestHandler):
    """Read-only admin Ingress page for a reserved provider package."""

    protocol_version = "HTTP/1.1"
    server_version = "PortfolioArchitectProviderShell"
    sys_version = ""

    @property
    def shell_server(self) -> ProviderShellIngressServer:
        return self.server  # type: ignore[return-value]

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorised_ingress():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        path = urlsplit(self.path).path
        if path in {"", "/"}:
            self._html(self._render_page())
            return
        if path == "/status":
            self._json(self.shell_server.gateway_state.health_document(version=6))
            return
        if path == "/health":
            self._json({"status": "ok"})
            return
        self._empty(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        self._method_not_allowed()

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST
    do_HEAD = do_POST
    do_OPTIONS = do_POST

    def _authorised_ingress(self) -> bool:
        total = sum(len(key) + len(value) for key, value in self.headers.items())
        if total > MAX_HEADER_BYTES:
            return False
        if self.client_address[0] not in self.shell_server.allowed_sources:
            return False
        if self.shell_server.require_user_header and not self.headers.get("X-Remote-User-Id"):
            return False
        return True

    def _render_page(self) -> bytes:
        health = self.shell_server.gateway_state.health_document(version=6)
        name = escape(self.shell_server.provider_name)
        provider_id = escape(str(health.get("provider_id", "unknown")))
        token = escape(self.shell_server.api_token)
        status = escape(str(health.get("status", "degraded")))
        body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portfolio Architect Gateway — {name}</title><style>body{{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}}section{{border:1px solid #444;border-radius:12px;padding:1rem;margin:1rem 0}}code{{word-break:break-all}}.warn{{color:#ffca28}}</style></head><body><main><h1>Portfolio Architect Gateway — {name}</h1><section><h2>Provider package installed</h2><p class="warn">Live acquisition is intentionally not implemented in Portfolio Architect {escape(__version__)}.</p><p>This App establishes an isolated provider identity, private data volume, authenticated read-only Gateway boundary, and future upgrade path. Do not configure Portfolio Architect to use this endpoint yet.</p></section><section><h2>Runtime</h2><p>Provider ID: <code>{provider_id}</code></p><p>Gateway status: <strong>{status}</strong></p><p>Bearer token: <code>{token}</code></p><p>The token is App-private state and will survive in-place upgrades. It is shown only in this admin-only Ingress page.</p></section></main></body></html>"""
        return body.encode("utf-8")

    def _html(self, body: bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self._security_headers("text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, document: dict[str, Any]) -> None:
        body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        self.send_response(HTTPStatus.OK)
        self._security_headers("application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _empty(self, status: HTTPStatus) -> None:
        self.send_response(status)
        self._security_headers("text/plain; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _method_not_allowed(self) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", "GET")
        self._security_headers("text/plain; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _security_headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'self'; base-uri 'none'")

    def log_message(self, format: str, *args: Any) -> None:
        _LOGGER.debug("Provider shell Ingress request completed")


def serve_pending_app(
    *,
    provider_id: str,
    provider_name: str,
    options: PendingAppOptions | None = None,
    data_directory: Path = APP_DATA_DIRECTORY,
    ingress_address: tuple[str, int] = (INGRESS_BIND, INGRESS_PORT),
    allowed_ingress_sources: frozenset[str] = frozenset({"172.30.32.2"}),
    require_user_header: bool = True,
    ready_callback: Callable[[], None] | None = None,
    tls_cert_file: Path | None = None,
    tls_key_file: Path | None = None,
) -> None:
    """Run one isolated provider shell with authenticated health and no portfolio data."""
    data_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if options is None:
        options = PendingAppOptions.load()
    server_config = build_server_config(
        options,
        data_directory,
        tls_cert_file=tls_cert_file,
        tls_key_file=tls_key_file,
    )
    api_token = ensure_api_token(server_config.api_token_file)
    provider = PendingProvider(provider_id)
    state = GatewayState(server_config, provider)
    state.refresh(trigger="startup")

    gateway_server = create_server(server_config, state)
    ingress_server = ProviderShellIngressServer(
        ingress_address,
        state=state,
        provider_name=provider_name,
        api_token=api_token,
        allowed_sources=allowed_ingress_sources,
        require_user_header=require_user_header,
    )
    gateway_thread = threading.Thread(
        target=gateway_server.serve_forever,
        kwargs={"poll_interval": 0.5},
        name="portfolio-provider-shell-api",
        daemon=True,
    )
    gateway_thread.start()
    _LOGGER.info("Provider shell initialized for %s", provider.provider_id)
    if ready_callback:
        ready_callback()
    try:
        ingress_server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _LOGGER.info("Provider shell shutdown requested")
    finally:
        ingress_server.shutdown()
        ingress_server.server_close()
        gateway_server.shutdown()
        gateway_server.server_close()
        gateway_thread.join(timeout=5)
