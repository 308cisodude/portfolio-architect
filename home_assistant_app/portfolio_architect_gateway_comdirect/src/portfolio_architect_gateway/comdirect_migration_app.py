"""Admin-only setup shell for the provider-qualified Comdirect App identity.

A pristine ``portfolio_architect_gateway_comdirect`` installation intentionally does
not create a second Portfolio Architect discovery source.  It first receives and
stages the historical App's long-lived private state over one-time pinned TLS, then
requires explicit commit and cut-over approval.  OAuth session state is never
transferred.
"""

from __future__ import annotations

from dataclasses import asdict
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import secrets
import socketserver
import threading
from typing import Any, Final
from urllib.parse import parse_qs, urlsplit

from . import __version__
from .comdirect_slug_migration import (
    CUTOVER_MARKER_NAME,
    FRESH_SETUP_MARKER_NAME,
    IMPORT_MARKER_NAME,
    STAGING_DIRECTORY_NAME,
    MigrationReceiverServer,
    MigrationSummary,
    approve_cutover,
    commit_staged_payload,
    ensure_self_options,
    expected_legacy_hostname,
    import_options_applied,
    mark_import_options_applied,
    prepare_migration_transport,
    read_staged_summary,
)

_LOGGER = logging.getLogger(__name__)
DATA_ROOT: Final = Path("/data")
GATEWAY_DATA: Final = DATA_ROOT / "gateway"
MIGRATION_WORKSPACE: Final = DATA_ROOT / "comdirect-slug-migration-work"
INGRESS_BIND: Final = "0.0.0.0"
INGRESS_PORT: Final = 8099
MIGRATION_PORT: Final = 8788
WATCHDOG_PORT: Final = 8787
MAX_HEADER_BYTES: Final = 32 * 1024
MAX_FORM_BYTES: Final = 4 * 1024


class _WatchdogHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        # Supervisor's watchdog only needs the pending App process to accept a TCP
        # connection.  No protocol or migration material is exposed on this port.
        return


class PendingWatchdogServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class ComdirectMigrationSetupController:
    """Coordinate one staged import and explicit canonical-runtime approval."""

    def __init__(
        self,
        *,
        hostname: str,
        supervisor_token: str,
        data_root: Path = DATA_ROOT,
        workspace_directory: Path | None = None,
    ) -> None:
        self.hostname = hostname
        self.expected_source_hostname = expected_legacy_hostname(hostname)
        self.supervisor_token = supervisor_token
        self.data_root = Path(data_root)
        self.gateway_data = self.data_root / "gateway"
        self.workspace_directory = (
            Path(workspace_directory)
            if workspace_directory is not None
            else self.data_root / "comdirect-slug-migration-work"
        )
        self.staging_directory = self.workspace_directory / STAGING_DIRECTORY_NAME
        self.import_marker = self.gateway_data / IMPORT_MARKER_NAME
        self.cutover_marker = self.gateway_data / CUTOVER_MARKER_NAME
        self.fresh_marker = self.gateway_data / FRESH_SETUP_MARKER_NAME
        self.csrf_token = secrets.token_urlsafe(32)
        self._lock = threading.RLock()
        self.transport = prepare_migration_transport(self.workspace_directory, hostname)

    @property
    def staged_summary(self) -> MigrationSummary | None:
        return read_staged_summary(self.staging_directory)

    @property
    def imported(self) -> bool:
        return self.import_marker.is_file()

    @property
    def options_applied(self) -> bool:
        return import_options_applied(self.import_marker)

    @property
    def cutover_approved(self) -> bool:
        return self.cutover_marker.is_file()

    def status_document(self) -> dict[str, Any]:
        summary = self.staged_summary
        return {
            "version": __version__,
            "hostname": self.hostname,
            "expected_source_hostname": self.expected_source_hostname,
            "state": (
                "cutover_approved"
                if self.cutover_approved
                else "imported"
                if self.imported and self.options_applied
                else "import_pending_options"
                if self.imported
                else "staged"
                if summary
                else "waiting"
            ),
            "staged_summary": asdict(summary) if summary else None,
            "oauth_session_transferred": False,
        }

    def reconcile_options(self) -> None:
        """Finish an interrupted Supervisor-options commit idempotently."""
        if not self.imported or self.options_applied:
            return
        options_path = self.staging_directory / "migration-options.json"
        if not options_path.is_file():
            raise RuntimeError("Migrated Comdirect options are unavailable")
        options = json.loads(options_path.read_text(encoding="utf-8"))
        ensure_self_options(options, supervisor_token=self.supervisor_token)
        mark_import_options_applied(self.import_marker)

    def commit(self) -> MigrationSummary:
        with self._lock:
            summary, options = commit_staged_payload(
                staging_directory=self.staging_directory,
                data_directory=self.gateway_data,
                import_marker=self.import_marker,
            )
            ensure_self_options(options, supervisor_token=self.supervisor_token)
            mark_import_options_applied(self.import_marker)
            return summary

    def approve(self) -> None:
        with self._lock:
            if not self.imported or not self.options_applied:
                raise ValueError("Migrated state and App options must be committed first")
            summary = self.staged_summary
            if summary is None:
                raise ValueError("Validated migration summary is unavailable")
            approve_cutover(
                self.cutover_marker,
                source_hostname=summary.source_hostname,
                ca_sha256=summary.source_ca_sha256,
            )

    def approve_fresh_setup(self) -> None:
        """Allow a genuinely new installation when there is no legacy state."""
        with self._lock:
            if self.staged_summary is not None or self.imported:
                raise ValueError("Cannot select fresh setup after migration state exists")
            self.gateway_data.mkdir(mode=0o700, parents=True, exist_ok=False)
            document = {
                "schema_version": 1,
                "created_at": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(timespec="seconds"),
            }
            self.fresh_marker.write_text(
                json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            os.chmod(self.fresh_marker, 0o600)
            self.cutover_marker.write_text(
                json.dumps(
                    {"schema_version": 1, "fresh_setup": True},
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            os.chmod(self.cutover_marker, 0o600)


class ComdirectMigrationIngressServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        controller: ComdirectMigrationSetupController,
        receiver: MigrationReceiverServer,
        allowed_sources: frozenset[str],
        require_user_header: bool,
    ) -> None:
        self.controller = controller
        self.receiver = receiver
        self.allowed_sources = allowed_sources
        self.require_user_header = require_user_header
        super().__init__(address, ComdirectMigrationIngressHandler)


class ComdirectMigrationIngressHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PortfolioArchitectComdirectMigrationSetup"
    sys_version = ""

    @property
    def app_server(self) -> ComdirectMigrationIngressServer:
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
            self._json(self.app_server.controller.status_document())
            return
        if path == "/health":
            self._json({"status": "ok"})
            return
        self._empty(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorised_ingress():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        path = urlsplit(self.path).path
        if path not in {"/commit", "/approve-cutover", "/fresh-setup"}:
            self._empty(HTTPStatus.NOT_FOUND)
            return
        try:
            values = self._read_form()
            if set(values) != {"csrf"}:
                raise ValueError("Unexpected migration form field")
            csrf = values["csrf"][0] if len(values["csrf"]) == 1 else ""
            if not secrets.compare_digest(csrf, self.app_server.controller.csrf_token):
                self._empty(HTTPStatus.FORBIDDEN)
                return
            if path == "/commit":
                self.app_server.controller.commit()
                self.app_server.receiver.committed = True
            elif path == "/approve-cutover":
                self.app_server.controller.approve()
            else:
                self.app_server.controller.approve_fresh_setup()
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
            _LOGGER.warning("Comdirect App-identity migration action was rejected")
            self._empty(HTTPStatus.CONFLICT)
            return
        self._see_other("./")

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST
    do_HEAD = do_POST
    do_OPTIONS = do_POST

    def _read_form(self) -> dict[str, list[str]]:
        if self.headers.get_content_type() != "application/x-www-form-urlencoded":
            raise ValueError("Migration form content type is invalid")
        token = self.headers.get("Content-Length")
        if token is None or not token.isdecimal():
            raise ValueError("Migration form length is invalid")
        length = int(token)
        if not 1 <= length <= MAX_FORM_BYTES:
            raise ValueError("Migration form is too large")
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValueError("Migration form is incomplete")
        return parse_qs(
            body.decode("utf-8"),
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=2,
        )

    def _render_page(self) -> bytes:
        controller = self.app_server.controller
        summary = controller.staged_summary
        csrf = escape(controller.csrf_token)
        code = escape(controller.transport.code)
        state = controller.status_document()["state"]
        if state == "waiting":
            action = f"""
<section><h2>1 · Receive legacy Comdirect state</h2>
<p>Install/update the historical <code>portfolio_architect_gateway</code> App to the same release, open its Ingress page and paste this one-time migration code:</p>
<p class="secret"><code>{code}</code></p>
<p>The code combines a one-time bearer secret with this receiver's ephemeral TLS certificate fingerprint. The legacy App derives the successor hostname itself; no destination URL is accepted.</p></section>
<section><h2>Fresh installation</h2><p>Use this only when no historical Comdirect Gateway exists.</p><form method="post" action="./fresh-setup"><input type="hidden" name="csrf" value="{csrf}"><button class="secondary">Start as a fresh Comdirect Gateway</button></form></section>"""
        elif state == "staged" and summary is not None:
            action = f"""
<section><h2>2 · Review staged state</h2>{_summary_html(summary)}
<p><strong>OAuth session transferred: no.</strong> A fresh PhotoTAN bootstrap will be required if Live API is authoritative.</p>
<form method="post" action="./commit"><input type="hidden" name="csrf" value="{csrf}"><button>Commit long-lived private state</button></form></section>"""
        elif state == "import_pending_options":
            action = "<section><h2>Migration commit interrupted</h2><p>Private state was installed atomically, but Supervisor options are not yet confirmed. Restart this App; it will retry the bounded options reconciliation without publishing discovery.</p></section>"
        elif state == "imported":
            action = f"""
<section><h2>3 · Freeze the legacy App</h2>{_summary_html(summary) if summary else ''}
<p>Return to the historical Comdirect Gateway and choose <strong>Freeze legacy for cut-over</strong>. That stops provider refresh/OAuth maintenance while the old verified-HTTPS snapshot remains served.</p>
<p>After the legacy App reports FROZEN, confirm below. The canonical App will still not publish discovery until its provider path is healthy.</p>
<form method="post" action="./approve-cutover"><input type="hidden" name="csrf" value="{csrf}"><button>I have frozen the legacy App — approve canonical runtime</button></form></section>"""
        else:
            action = "<section><h2>4 · Restart this App</h2><p>Canonical runtime is approved. Restart <strong>Portfolio Architect Gateway — Comdirect</strong>. If Live API is active, perform a fresh PhotoTAN bootstrap. The App will publish its new provider-qualified endpoint only after a healthy snapshot is available.</p><p>Keep the legacy App installed and frozen until Portfolio Architect explicitly confirms the endpoint migration and remains healthy.</p></section>"
        body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portfolio Architect Gateway — Comdirect</title><style>body{{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}}section{{border:1px solid #444;border-radius:12px;padding:1rem;margin:1rem 0}}code{{word-break:break-all}}button{{background:#2e7d32;color:white;border:0;border-radius:7px;padding:.7rem 1rem;font-weight:700}}button.secondary{{background:#315f8c}}.warn{{color:#ffca28}}.secret{{padding:.75rem;border:1px dashed #777;border-radius:8px}}dt{{font-weight:700}}dd{{margin-bottom:.5rem}}</style></head><body><main><h1>Portfolio Architect Gateway — Comdirect</h1><section><h2>App identity migration</h2><p>This provider-qualified App replaces the historical internal slug without silently replacing Portfolio Architect trust or provider authority.</p><p class="warn">The private CA and Gateway bearer token are preserved. The Comdirect OAuth session is deliberately not migrated.</p><p>Expected historical App host: <code>{escape(controller.expected_source_hostname)}</code></p></section>{action}</main></body></html>"""
        return body.encode("utf-8")

    def _authorised_ingress(self) -> bool:
        total = sum(len(key) + len(value) for key, value in self.headers.items())
        if total > MAX_HEADER_BYTES:
            return False
        if self.client_address[0] not in self.app_server.allowed_sources:
            return False
        if self.app_server.require_user_header and not self.headers.get("X-Remote-User-Id"):
            return False
        return True

    def _html(self, body: bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self._security_headers("text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, document: dict[str, Any]) -> None:
        body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
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

    def _see_other(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
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
        _LOGGER.info("Comdirect migration setup Ingress request completed")


def _summary_html(summary: MigrationSummary) -> str:
    return (
        "<dl>"
        f"<dt>Source host</dt><dd><code>{escape(summary.source_hostname)}</code></dd>"
        f"<dt>Private CA SHA-256</dt><dd><code>{escape(summary.source_ca_sha256)}</code></dd>"
        f"<dt>Snapshot generated</dt><dd><code>{escape(summary.snapshot_generated_at)}</code></dd>"
        f"<dt>Snapshot SHA-256</dt><dd><code>{escape(summary.snapshot_sha256)}</code></dd>"
        f"<dt>Acquisition mode</dt><dd><code>{escape(summary.acquisition_mode)}</code></dd>"
        f"<dt>Private files</dt><dd>{summary.file_count}</dd>"
        "</dl>"
    )


def serve_comdirect_migration_setup(
    *,
    hostname: str,
    supervisor_token: str,
    data_root: Path = DATA_ROOT,
    workspace_directory: Path = MIGRATION_WORKSPACE,
    ingress_address: tuple[str, int] = (INGRESS_BIND, INGRESS_PORT),
    allowed_ingress_sources: frozenset[str] = frozenset({"172.30.32.2"}),
    require_user_header: bool = True,
) -> None:
    """Serve pending migration UI + pinned receiver without Supervisor discovery."""
    data_root = Path(data_root)
    workspace_directory = Path(workspace_directory)
    workspace_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    controller = ComdirectMigrationSetupController(
        hostname=hostname,
        supervisor_token=supervisor_token,
        data_root=data_root,
        workspace_directory=workspace_directory,
    )
    try:
        controller.reconcile_options()
    except RuntimeError:
        _LOGGER.warning("Comdirect migrated Supervisor options are not yet reconciled")
    receiver = MigrationReceiverServer(
        ("0.0.0.0", MIGRATION_PORT),
        transport=controller.transport,
        staging_directory=controller.staging_directory,
        expected_source_hostname=controller.expected_source_hostname,
    )
    receiver.committed = controller.imported
    ingress = ComdirectMigrationIngressServer(
        ingress_address,
        controller=controller,
        receiver=receiver,
        allowed_sources=allowed_ingress_sources,
        require_user_header=require_user_header,
    )
    watchdog = PendingWatchdogServer(("0.0.0.0", WATCHDOG_PORT), _WatchdogHandler)
    threads = [
        threading.Thread(target=receiver.serve_forever, kwargs={"poll_interval": 0.5}, name="comdirect-migration-receiver", daemon=True),
        threading.Thread(target=watchdog.serve_forever, kwargs={"poll_interval": 0.5}, name="comdirect-migration-watchdog", daemon=True),
    ]
    for thread in threads:
        thread.start()
    _LOGGER.info("Provider-qualified Comdirect App waiting for explicit migration/setup")
    try:
        ingress.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _LOGGER.info("Comdirect migration setup shutdown requested")
    finally:
        ingress.shutdown()
        ingress.server_close()
        receiver.shutdown()
        receiver.server_close()
        watchdog.shutdown()
        watchdog.server_close()
        for thread in threads:
            thread.join(timeout=5)
