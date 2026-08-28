"""Admin-only Generic Import CSV UI and static provider runtime."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from email import policy
from email.parser import BytesHeaderParser
from html import escape
from http import HTTPStatus
import logging
from pathlib import Path
import secrets
import threading
from typing import Any, Final
from urllib.parse import urlsplit

from . import __version__
from .errors import ProtocolError
from .generic_csv import (
    CSV_DELIMITERS,
    CSV_ENCODINGS,
    DECIMAL_FORMATS,
    MAX_CSV_FILE_BYTES,
    GenericCsvConfig,
    GenericCsvImportError,
    GenericCsvProvider,
    parse_generic_csv,
)
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
from .store import load_json_state, save_json_state

_LOGGER = logging.getLogger(__name__)
MAX_MULTIPART_BYTES: Final = MAX_CSV_FILE_BYTES + 64 * 1024
MAX_BOUNDARY_BYTES: Final = 70
MAPPING_FILE_NAME: Final = "generic-csv-mapping.json"
IMPORT_DIAGNOSTIC_FILE_NAME: Final = "generic-import-diagnostic.json"
_TEXT_FIELDS: Final = frozenset(
    {
        "nonce",
        "encoding",
        "delimiter",
        "header_row",
        "decimal_format",
        "identifier_column",
        "name_column",
        "value_column",
        "isin_column",
        "type_column",
        "currency_column",
    }
)
_ALL_FIELDS: Final = _TEXT_FIELDS | {"csv"}


class GenericImportIngressServer(ProviderShellIngressServer):
    """Ingress server carrying the static provider and private import state."""

    def __init__(
        self,
        address: tuple[str, int],
        *,
        state: GatewayState,
        provider: GenericCsvProvider,
        provider_name: str,
        api_token: str,
        allowed_sources: frozenset[str],
        require_user_header: bool,
    ) -> None:
        self.generic_provider = provider
        self.import_nonce = secrets.token_urlsafe(32)
        self.mapping_file = provider.snapshot_file.parent / MAPPING_FILE_NAME
        self.import_diagnostic_file = (
            provider.snapshot_file.parent / IMPORT_DIAGNOSTIC_FILE_NAME
        )
        super().__init__(
            address,
            state=state,
            provider_name=provider_name,
            api_token=api_token,
            allowed_sources=allowed_sources,
            require_user_header=require_user_header,
            handler_class=GenericImportIngressHandler,
        )

    def load_mapping(self) -> GenericCsvConfig:
        """Return the private persisted mapping or conservative example defaults."""
        try:
            raw = load_json_state(self.mapping_file)
        except ProtocolError as err:
            raise GenericCsvImportError("Stored CSV mapping is invalid") from err
        if raw is None:
            return GenericCsvConfig()
        if raw.get("schema_version") != 1 or set(raw) != {"schema_version", "mapping"}:
            raise GenericCsvImportError("Stored CSV mapping is invalid")
        mapping = raw.get("mapping")
        if not isinstance(mapping, dict):
            raise GenericCsvImportError("Stored CSV mapping is invalid")
        return GenericCsvConfig.from_mapping(mapping)

    def save_mapping(self, config: GenericCsvConfig) -> None:
        save_json_state(
            self.mapping_file,
            {"schema_version": 1, "mapping": config.as_dict()},
        )

    def record_import_diagnostic(self, outcome: str, message: str) -> None:
        if outcome not in {"accepted", "rejected", "internal_error"}:
            raise ValueError("Unsupported Generic Import diagnostic outcome")
        safe = _bounded_notice(message)
        save_json_state(
            self.import_diagnostic_file,
            {
                "schema_version": 1,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "outcome": outcome,
                "message": safe,
            },
        )

    def import_diagnostic(self) -> dict[str, str] | None:
        try:
            raw = load_json_state(self.import_diagnostic_file)
        except ProtocolError:
            return {
                "outcome": "internal_error",
                "message": "Stored import diagnostic is invalid.",
                "recorded_at": "unknown",
            }
        if raw is None:
            return None
        if set(raw) != {"schema_version", "recorded_at", "outcome", "message"}:
            return None
        if raw.get("schema_version") != 1:
            return None
        outcome = raw.get("outcome")
        recorded_at = raw.get("recorded_at")
        message = raw.get("message")
        if (
            outcome not in {"accepted", "rejected", "internal_error"}
            or not isinstance(recorded_at, str)
            or not isinstance(message, str)
            or _bounded_notice(message) != message
        ):
            return None
        return {
            "outcome": str(outcome),
            "message": message,
            "recorded_at": recorded_at,
        }


class GenericImportIngressHandler(ProviderShellIngressHandler):
    """Protected form for one provider-neutral mapped CSV import."""

    server_version = "PortfolioArchitectGenericImport"

    @property
    def import_server(self) -> GenericImportIngressServer:
        return self.server  # type: ignore[return-value]

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorised_ingress():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        path = urlsplit(self.path).path
        if path in {"", "/"}:
            self._html_status(self._render_page(), HTTPStatus.OK)
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
            fields, document = self._read_import_form()
            if not secrets.compare_digest(fields.pop("nonce"), self.import_server.import_nonce):
                raise GenericCsvImportError(
                    "Import form session is invalid; reload the page and try again"
                )
            mapping = GenericCsvConfig.from_mapping(fields)
            snapshot, summary = parse_generic_csv(
                document,
                mapping,
                generated_at=datetime.now(timezone.utc),
            )
            previous = self.import_server.generic_provider.snapshot
            self.import_server.generic_provider.replace_snapshot(snapshot)
            if not self.import_server.gateway_state.refresh(trigger="manual"):
                self.import_server.generic_provider.replace_snapshot(previous)
                raise GenericCsvImportError("Imported CSV could not be activated")
            self.import_server.save_mapping(mapping)
            self.import_server.record_import_diagnostic(
                "accepted",
                f"CSV accepted: {summary.position_count} positions; evidence timestamp "
                f"{summary.generated_at.isoformat(timespec='seconds')}.",
            )
        except GenericCsvImportError as err:
            _LOGGER.warning("Generic mapped CSV import rejected")
            self.import_server.record_import_diagnostic(
                "rejected", f"CSV rejected: {_public_import_error(err)}"
            )
            self._html_status(self._render_page(), HTTPStatus.BAD_REQUEST)
            return
        except Exception:
            _LOGGER.exception("Generic mapped CSV import failed internally")
            self.import_server.record_import_diagnostic(
                "internal_error",
                "CSV import failed internally; no new snapshot was activated.",
            )
            self._html_status(
                self._render_page(), HTTPStatus.INTERNAL_SERVER_ERROR
            )
            return

        _LOGGER.info("Generic mapped CSV import activated a validated snapshot")
        self._html_status(self._render_page(), HTTPStatus.OK)

    do_PUT = ProviderShellIngressHandler.do_POST
    do_PATCH = ProviderShellIngressHandler.do_POST
    do_DELETE = ProviderShellIngressHandler.do_POST
    do_HEAD = ProviderShellIngressHandler.do_POST
    do_OPTIONS = ProviderShellIngressHandler.do_POST

    def _read_import_form(self) -> tuple[dict[str, str], bytes]:
        if sum(len(key) + len(value) for key, value in self.headers.items()) > MAX_HEADER_BYTES:
            raise GenericCsvImportError("Import request headers are too large")
        if self.headers.get_content_type() != "multipart/form-data":
            raise GenericCsvImportError("Import request must use multipart/form-data")
        boundary = self.headers.get_boundary()
        if not boundary:
            raise GenericCsvImportError("Import form boundary is missing")
        try:
            boundary_bytes = boundary.encode("ascii")
        except UnicodeEncodeError as err:
            raise GenericCsvImportError("Import form boundary is invalid") from err
        if not 1 <= len(boundary_bytes) <= MAX_BOUNDARY_BYTES or any(
            byte < 33 or byte > 126 for byte in boundary_bytes
        ):
            raise GenericCsvImportError("Import form boundary is invalid")
        length_token = self.headers.get("Content-Length")
        try:
            length = int(length_token) if length_token is not None else -1
        except ValueError as err:
            raise GenericCsvImportError("Import request length is invalid") from err
        if not 1 <= length <= MAX_MULTIPART_BYTES:
            raise GenericCsvImportError("Import request is empty or too large")
        body = self.rfile.read(length)
        if len(body) != length:
            raise GenericCsvImportError("Import request body is incomplete")
        return _parse_multipart_body(body, boundary_bytes)

    def _render_page(self) -> bytes:
        health = self.import_server.gateway_state.health_document(version=8)
        try:
            mapping = self.import_server.load_mapping()
            mapping_error = ""
        except GenericCsvImportError:
            mapping = GenericCsvConfig()
            mapping_error = (
                '<p class="bad">Stored mapping is invalid; defaults are shown and a valid '
                "import will replace it.</p>"
            )
        diagnostic = self.import_server.import_diagnostic()
        snapshot = self.import_server.generic_provider.snapshot
        status = escape(str(health.get("status", "degraded")))
        status_class = "good" if status == "ok" else "warn"
        snapshot_text = (
            f"{len(snapshot.positions)} positions · {escape(snapshot.generated_at.isoformat(timespec='seconds'))}"
            if snapshot is not None
            else "No CSV imported yet"
        )
        diagnostic_html = "<p>No import diagnostic recorded yet.</p>"
        if diagnostic is not None:
            diagnostic_html = (
                f"<p><strong>{escape(diagnostic['outcome'])}</strong> · "
                f"{escape(diagnostic['recorded_at'])}</p><p>{escape(diagnostic['message'])}</p>"
            )
        body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio Architect Gateway — Generic Import</title>
<style>
:root{{color-scheme:dark}}body{{font-family:system-ui,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}}section{{border:1px solid #444;border-radius:12px;padding:1rem;margin:1rem 0}}.mode-card.active{{border:2px solid #22c55eaa;background:#22c55e12}}.mode-head{{display:flex;justify-content:space-between;align-items:center;gap:12px}}.badge{{font-size:.78rem;font-weight:800;padding:4px 9px;border-radius:999px;border:1px solid currentColor;color:#4ade80}}.good{{color:#7bd88f}}.warn{{color:#ffca28}}.bad{{color:#ff7b7b}}code{{word-break:break-all}}label{{display:block;margin:.7rem 0 .2rem}}input,select{{box-sizing:border-box;width:100%;max-width:680px;padding:.55rem;background:#1b1b1b;color:#eee;border:1px solid #555;border-radius:6px}}button{{margin-top:1rem;padding:.65rem 1rem;border-radius:7px;border:1px solid #6b9db7;background:#173b4d;color:#fff;font-weight:600}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.75rem}}small{{color:#bbb}}
</style></head><body><main>
<h1>Portfolio Architect Gateway — Generic Import</h1>
<section class="mode-card active"><div class="mode-head"><h2>Static acquisition · mapped CSV</h2><span class="badge">ACTIVE</span></div><p>This Gateway is an explicit provider-neutral escape hatch. Raw CSV bytes are parsed transiently and are never persisted.</p><p>Provider ID: <code>generic_csv</code> · Acquisition mode: <code>csv</code></p><p>Current snapshot: <strong>{snapshot_text}</strong></p></section>
<section><h2>Runtime</h2><p>Gateway status: <strong class="{status_class}">{status}</strong></p></section>
<section><h2>Import mapped CSV</h2>{mapping_error}
<form method="post" action="import" enctype="multipart/form-data">
<input type="hidden" name="nonce" value="{escape(self.import_server.import_nonce)}">
<label for="csv">CSV file</label><input id="csv" name="csv" type="file" accept=".csv,text/csv,text/plain" required>
<div class="grid">
<div><label for="encoding">Encoding</label><select id="encoding" name="encoding">{_options(CSV_ENCODINGS, mapping.encoding)}</select></div>
<div><label for="delimiter">Delimiter</label><select id="delimiter" name="delimiter">{_options(CSV_DELIMITERS, mapping.delimiter)}</select></div>
<div><label for="header_row">Header row</label><input id="header_row" name="header_row" type="number" min="1" max="50" value="{mapping.header_row}" required></div>
<div><label for="decimal_format">Number format</label><select id="decimal_format" name="decimal_format">{_options(DECIMAL_FORMATS, mapping.decimal_format)}</select></div>
</div>
<div class="grid">
<div><label for="identifier_column">Identifier column</label><input id="identifier_column" name="identifier_column" value="{escape(mapping.identifier_column)}" maxlength="160" required></div>
<div><label for="name_column">Name column</label><input id="name_column" name="name_column" value="{escape(mapping.name_column)}" maxlength="160" required></div>
<div><label for="value_column">EUR market-value column</label><input id="value_column" name="value_column" value="{escape(mapping.value_column)}" maxlength="160" required></div>
<div><label for="isin_column">ISIN column (optional)</label><input id="isin_column" name="isin_column" value="{escape(mapping.isin_column or '')}" maxlength="160"></div>
<div><label for="type_column">Instrument-type column (optional)</label><input id="type_column" name="type_column" value="{escape(mapping.type_column or '')}" maxlength="160"></div>
<div><label for="currency_column">Currency column (optional)</label><input id="currency_column" name="currency_column" value="{escape(mapping.currency_column or '')}" maxlength="160"></div>
</div>
<p><small>If Currency is mapped, every imported position must explicitly contain EUR or €. No currency conversion is performed. The successful import time becomes the generic holdings evidence timestamp.</small></p>
<button type="submit">Validate and activate CSV</button></form></section>
<section><h2>Last import result</h2>{diagnostic_html}</section>
<section><h2>Boundary</h2><p>Portfolio Architect consumes only the canonical read-only snapshot over verified private-PKI HTTPS. This App has no live-provider credentials and no order, transfer, payment, transaction-history, sell, or withdrawal capability.</p></section>
<section><h2>Sensitive connection material</h2><p><small>The bearer token is needed only for an explicit Portfolio Architect source setup and is intentionally kept away from the screenshot-prone top of this page.</small></p><details><summary>Show bearer token</summary><p>Bearer token: <code>{escape(self.import_server.api_token)}</code></p><p><small>The token is App-private state and is shown only in this admin-only Ingress page.</small></p></details></section>
</main></body></html>"""
        return body.encode("utf-8")

    def _html_status(self, body: bytes, status: HTTPStatus) -> None:
        self.send_response(status)
        self._security_headers("text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _options(values: tuple[str, ...], selected: str) -> str:
    return "".join(
        f'<option value="{escape(value)}"{" selected" if value == selected else ""}>{escape(value)}</option>'
        for value in values
    )


def _parse_multipart_body(body: bytes, boundary: bytes) -> tuple[dict[str, str], bytes]:
    delimiter = b"--" + boundary
    closing = delimiter + b"--"
    if not body.startswith(delimiter + b"\r\n") or closing not in body:
        raise GenericCsvImportError("Import form body is malformed")
    fields: dict[str, bytes] = {}
    for raw_part in body.split(delimiter)[1:]:
        if raw_part.startswith(b"--"):
            break
        if not raw_part.startswith(b"\r\n"):
            raise GenericCsvImportError("Import form part is malformed")
        part = raw_part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        try:
            header_blob, payload = part.split(b"\r\n\r\n", 1)
        except ValueError as err:
            raise GenericCsvImportError("Import form part headers are malformed") from err
        if len(header_blob) > 8192:
            raise GenericCsvImportError("Import form part headers are too large")
        headers = BytesHeaderParser(policy=policy.default).parsebytes(header_blob + b"\r\n")
        if headers.get_content_disposition() != "form-data":
            raise GenericCsvImportError("Import form part disposition is invalid")
        field = headers.get_param("name", header="content-disposition")
        if field not in _ALL_FIELDS or field in fields:
            raise GenericCsvImportError("Import form contains unexpected or duplicate fields")
        if field == "csv":
            if headers.get_content_type() not in {
                "text/csv",
                "text/plain",
                "application/csv",
                "application/vnd.ms-excel",
                "application/octet-stream",
            }:
                raise GenericCsvImportError("Uploaded document must be a CSV file")
            if not payload or len(payload) > MAX_CSV_FILE_BYTES:
                raise GenericCsvImportError("CSV is empty or exceeds the 10 MiB import limit")
        elif len(payload) > 512:
            raise GenericCsvImportError("Import form field is too large")
        fields[str(field)] = payload
    if set(fields) != _ALL_FIELDS:
        raise GenericCsvImportError("Import form is incomplete")
    text: dict[str, str] = {}
    for field in _TEXT_FIELDS:
        try:
            text[field] = fields[field].decode("utf-8").strip()
        except UnicodeDecodeError as err:
            raise GenericCsvImportError("Import form text field is invalid") from err
    return text, fields["csv"]


def _public_import_error(err: GenericCsvImportError) -> str:
    message = str(err).strip()
    if not message or len(message) > 240 or any(ord(char) < 32 for char in message):
        return "CSV could not be validated safely."
    # Parser errors are deliberately written without filenames, raw values, or column contents.
    return message


def _bounded_notice(message: str) -> str:
    cleaned = str(message or "").strip()
    if not cleaned or len(cleaned) > 320 or any(ord(char) < 32 for char in cleaned):
        raise ValueError("Import diagnostic is invalid")
    return cleaned


def serve_generic_import_app(
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
    """Run the isolated provider-neutral Generic Import Gateway."""
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
    provider = GenericCsvProvider(server_config.snapshot_file)
    state = GatewayState(server_config, provider)
    state.refresh(trigger="startup")
    gateway_server = create_server(server_config, state)
    ingress_server = GenericImportIngressServer(
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
        name="portfolio-generic-import-api",
        daemon=True,
    )
    gateway_thread.start()
    _LOGGER.info("Generic Import Gateway initialized")
    if ready_callback:
        ready_callback()
    try:
        ingress_server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _LOGGER.info("Generic Import Gateway shutdown requested")
    finally:
        ingress_server.shutdown()
        ingress_server.server_close()
        gateway_server.shutdown()
        gateway_server.server_close()
        gateway_thread.join(timeout=5)
