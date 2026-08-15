"""Admin-only Trade Republic statement import UI and static provider runtime."""

from __future__ import annotations

from collections.abc import Callable

from email import policy
from email.parser import BytesHeaderParser
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import logging
from pathlib import Path
import secrets
import threading
from typing import Final
from urllib.parse import urlsplit

from . import __version__
from .pending_app import (
    APP_DATA_DIRECTORY,
    INGRESS_BIND,
    INGRESS_PORT,
    MAX_HEADER_BYTES,
    PendingAppOptions,
    ProviderShellIngressHandler,
    ProviderShellIngressServer,
    build_server_config,
)
from .runtime_config import ensure_api_token
from .server import GatewayState, create_server
from .trade_republic_statement import (
    MAX_PDF_BYTES,
    StatementImportError,
    TradeRepublicStatementProvider,
    import_summary,
    parse_statement_pdf,
)

_LOGGER = logging.getLogger(__name__)
MAX_MULTIPART_BYTES: Final = MAX_PDF_BYTES + 64 * 1024
MAX_BOUNDARY_BYTES: Final = 70


class TradeRepublicIngressServer(ProviderShellIngressServer):
    """Ingress server carrying the private statement provider and CSRF state."""

    def __init__(
        self,
        address: tuple[str, int],
        *,
        state: GatewayState,
        provider: TradeRepublicStatementProvider,
        provider_name: str,
        api_token: str,
        allowed_sources: frozenset[str],
        require_user_header: bool,
    ) -> None:
        self.statement_provider = provider
        self.import_nonce = secrets.token_urlsafe(32)
        self.last_notice: str | None = None
        super().__init__(
            address,
            state=state,
            provider_name=provider_name,
            api_token=api_token,
            allowed_sources=allowed_sources,
            require_user_header=require_user_header,
            handler_class=TradeRepublicIngressHandler,
        )


class TradeRepublicIngressHandler(ProviderShellIngressHandler):
    """Protected upload form for one supported Trade Republic statement family."""

    server_version = "PortfolioArchitectTradeRepublicImport"

    @property
    def tr_server(self) -> TradeRepublicIngressServer:
        return self.server  # type: ignore[return-value]

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorised_ingress():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        path = urlsplit(self.path).path
        if path in {"", "/"}:
            self._html_status(self._render_import_page(), HTTPStatus.OK)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorised_ingress():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        if urlsplit(self.path).path != "/import":
            self._empty(HTTPStatus.NOT_FOUND)
            return
        try:
            nonce, document = self._read_import_form()
            if not secrets.compare_digest(nonce, self.tr_server.import_nonce):
                raise StatementImportError("Import form session is invalid; reload the page and try again")
            snapshot = parse_statement_pdf(document)
            previous = self.tr_server.statement_provider.snapshot
            self.tr_server.statement_provider.replace_snapshot(snapshot)
            if not self.tr_server.gateway_state.refresh(trigger="manual"):
                self.tr_server.statement_provider.replace_snapshot(previous)
                raise StatementImportError("Imported statement could not be activated")
            summary = import_summary(snapshot)
            self.tr_server.last_notice = (
                f"Statement accepted: {summary.position_count} positions; "
                f"snapshot timestamp {summary.generated_at.isoformat(timespec='seconds')}."
            )
        except StatementImportError as err:
            _LOGGER.warning("Trade Republic statement import rejected")
            self.tr_server.last_notice = f"Statement rejected: {err}"
            self._html_status(self._render_import_page(), HTTPStatus.BAD_REQUEST)
            return
        except Exception:
            _LOGGER.exception("Trade Republic statement import failed internally")
            self.tr_server.last_notice = "Statement import failed internally; no new snapshot was activated."
            self._html_status(self._render_import_page(), HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        _LOGGER.info("Trade Republic statement import activated a validated snapshot")
        self._html_status(self._render_import_page(), HTTPStatus.OK)

    do_PUT = ProviderShellIngressHandler.do_POST
    do_PATCH = ProviderShellIngressHandler.do_POST
    do_DELETE = ProviderShellIngressHandler.do_POST
    do_HEAD = ProviderShellIngressHandler.do_POST
    do_OPTIONS = ProviderShellIngressHandler.do_POST

    def _read_import_form(self) -> tuple[str, bytes]:
        if sum(len(key) + len(value) for key, value in self.headers.items()) > MAX_HEADER_BYTES:
            raise StatementImportError("Import request headers are too large")
        if self.headers.get_content_type() != "multipart/form-data":
            raise StatementImportError("Import request must use multipart/form-data")
        boundary = self.headers.get_boundary()
        if not boundary:
            raise StatementImportError("Import form boundary is missing")
        try:
            boundary_bytes = boundary.encode("ascii")
        except UnicodeEncodeError as err:
            raise StatementImportError("Import form boundary is invalid") from err
        if not 1 <= len(boundary_bytes) <= MAX_BOUNDARY_BYTES or any(
            byte < 33 or byte > 126 for byte in boundary_bytes
        ):
            raise StatementImportError("Import form boundary is invalid")

        length_token = self.headers.get("Content-Length")
        try:
            length = int(length_token) if length_token is not None else -1
        except ValueError as err:
            raise StatementImportError("Import request length is invalid") from err
        if not 1 <= length <= MAX_MULTIPART_BYTES:
            raise StatementImportError("Import request is empty or too large")
        body = self.rfile.read(length)
        if len(body) != length:
            raise StatementImportError("Import request body is incomplete")
        return _parse_multipart_body(body, boundary_bytes)

    def _render_import_page(self) -> bytes:
        health = self.tr_server.gateway_state.health_document(version=6)
        name = escape(self.tr_server.provider_name)
        provider_id = escape(str(health.get("provider_id", "unknown")))
        status = escape(str(health.get("status", "degraded")))
        token = escape(self.tr_server.api_token)
        nonce = escape(self.tr_server.import_nonce)
        snapshot = self.tr_server.statement_provider.snapshot
        notice = ""
        if self.tr_server.last_notice:
            css_class = "ok" if self.tr_server.last_notice.startswith("Statement accepted") else "warn"
            notice = f'<p class="{css_class}">{escape(self.tr_server.last_notice)}</p>'
        if snapshot is None:
            snapshot_text = "No supported statement has been imported yet."
        else:
            summary = import_summary(snapshot)
            snapshot_text = (
                f"Active private snapshot: {summary.position_count} positions; "
                f"timestamp {escape(summary.generated_at.isoformat(timespec='seconds'))}."
            )
        body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portfolio Architect Gateway — {name}</title><style>body{{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}}section{{border:1px solid #444;border-radius:12px;padding:1rem;margin:1rem 0}}code{{word-break:break-all}}.warn{{color:#ffca28}}.ok{{color:#7ddc7a}}input[type=file]{{display:block;margin:.8rem 0 1rem}}button{{padding:.6rem 1rem}}</style></head><body><main><h1>Portfolio Architect Gateway — {name}</h1><section><h2>Trade Republic depot statement import</h2><p>Portfolio Architect {escape(__version__)} supports the German text-PDF <strong>DEPOTAUSZUG</strong> statement family. The uploaded PDF is parsed in memory and is not stored. Only the validated provider-neutral holdings snapshot is persisted in this App's private data volume.</p>{notice}<p>{escape(snapshot_text)}</p><form method="post" action="./import" enctype="multipart/form-data"><input type="hidden" name="nonce" value="{nonce}"><label for="statement">Trade Republic DEPOTAUSZUG PDF</label><input id="statement" type="file" name="statement" accept="application/pdf,.pdf" required><button type="submit">Import statement</button></form><p class="warn">Unsupported, encrypted, scanned/image-only, ambiguous, or internally inconsistent documents are rejected without replacing the last accepted snapshot.</p></section><section><h2>Runtime</h2><p>Provider ID: <code>{provider_id}</code></p><p>Gateway status: <strong>{status}</strong></p><p>Bearer token: <code>{token}</code></p><p>The token and normalized snapshot are App-private state and survive in-place upgrades. Do not publish screenshots containing the token.</p></section></main></body></html>"""
        return body.encode("utf-8")

    def _html_status(self, body: bytes, status: HTTPStatus) -> None:
        self.send_response(status)
        self._security_headers("text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _parse_multipart_body(body: bytes, boundary: bytes) -> tuple[str, bytes]:
    delimiter = b"--" + boundary
    closing = delimiter + b"--"
    if not body.startswith(delimiter + b"\r\n") or closing not in body:
        raise StatementImportError("Import form body is malformed")

    fields: dict[str, bytes] = {}
    for raw_part in body.split(delimiter)[1:]:
        if raw_part.startswith(b"--"):
            break
        if not raw_part.startswith(b"\r\n"):
            raise StatementImportError("Import form part is malformed")
        part = raw_part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        try:
            header_blob, payload = part.split(b"\r\n\r\n", 1)
        except ValueError as err:
            raise StatementImportError("Import form part headers are malformed") from err
        if len(header_blob) > 8192:
            raise StatementImportError("Import form part headers are too large")
        headers = BytesHeaderParser(policy=policy.default).parsebytes(header_blob + b"\r\n")
        if headers.get_content_disposition() != "form-data":
            raise StatementImportError("Import form part disposition is invalid")
        field = headers.get_param("name", header="content-disposition")
        if field not in {"nonce", "statement"} or field in fields:
            raise StatementImportError("Import form contains unexpected or duplicate fields")
        if field == "statement":
            content_type = headers.get_content_type()
            if content_type not in {"application/pdf", "application/octet-stream"}:
                raise StatementImportError("Uploaded statement must be a PDF document")
            if not payload or len(payload) > MAX_PDF_BYTES:
                raise StatementImportError("PDF is empty or exceeds the 5 MiB import limit")
        else:
            if len(payload) > 256:
                raise StatementImportError("Import form session field is invalid")
        fields[field] = payload

    if set(fields) != {"nonce", "statement"}:
        raise StatementImportError("Import form is incomplete")
    try:
        nonce = fields["nonce"].decode("ascii")
    except UnicodeDecodeError as err:
        raise StatementImportError("Import form session field is invalid") from err
    return nonce, fields["statement"]


def serve_trade_republic_app(
    *,
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
    """Run the isolated Trade Republic statement provider App."""
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
    provider = TradeRepublicStatementProvider(server_config.snapshot_file)
    state = GatewayState(server_config, provider)
    state.refresh(trigger="startup")

    gateway_server = create_server(server_config, state)
    ingress_server = TradeRepublicIngressServer(
        ingress_address,
        state=state,
        provider=provider,
        provider_name=provider_name,
        api_token=api_token,
        allowed_sources=allowed_ingress_sources,
        require_user_header=require_user_header,
    )
    gateway_thread = threading.Thread(
        target=gateway_server.serve_forever,
        kwargs={"poll_interval": 0.5},
        name="portfolio-trade-republic-api",
        daemon=True,
    )
    gateway_thread.start()
    _LOGGER.info("Trade Republic statement Gateway initialized")
    if ready_callback:
        ready_callback()
    try:
        ingress_server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _LOGGER.info("Trade Republic statement Gateway shutdown requested")
    finally:
        ingress_server.shutdown()
        ingress_server.server_close()
        gateway_server.shutdown()
        gateway_server.server_close()
        gateway_thread.join(timeout=5)
