"""DKB Gateway registration-gated FinTS capability-probe App."""

from __future__ import annotations

from collections.abc import Callable
from email import policy
from email.parser import BytesHeaderParser
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import re
from pathlib import Path
import secrets
import threading
from typing import Any, Final
from urllib.parse import parse_qs, urlsplit

from . import __version__
from .dkb_cash_csv import DkbCashCsvImportError, MAX_CASH_CSV_BYTES, parse_dkb_cash_csv
from .dkb_csv import (
    DkbCsvImportError,
    DkbCsvProvider,
    MAX_CSV_BATCH_BYTES,
    MAX_CSV_FILE_BYTES,
    MAX_CSV_FILES,
    parse_dkb_csv_batch,
)
from .dkb_fints import (
    CapabilityProbeResult,
    DKB_BANK_CODE,
    DKB_FINTS_ENDPOINT,
    FINTS_PRODUCT_VERSION,
    HOLDINGS_PARAMETER_SEGMENT,
    MAX_BASE64_RESPONSE_BYTES,
    MAX_RESPONSE_BYTES,
    MAX_RETURN_MESSAGE_CHARS,
    MAX_RETURN_MESSAGES,
    ReturnMessage,
    normalise_product_id,
    probe_dkb_bpd,
)
from .errors import GatewayError, ProtocolError, RemoteApiError
from .pending_app import PendingAppOptions, build_server_config
from .runtime_config import ensure_api_token
from .server import GatewayState, create_server
from .store import atomic_write, load_json_state, save_json_state

_LOGGER = logging.getLogger(__name__)
APP_DATA_DIRECTORY: Final = Path("/data/gateway")
INGRESS_BIND: Final = "0.0.0.0"
INGRESS_PORT: Final = 8099
MAX_FORM_BYTES: Final = 8 * 1024
MAX_MULTIPART_BYTES: Final = MAX_CSV_BATCH_BYTES + 256 * 1024
MAX_CASH_MULTIPART_BYTES: Final = MAX_CASH_CSV_BYTES + 256 * 1024
MAX_BOUNDARY_BYTES: Final = 70
MAX_HEADER_BYTES: Final = 32 * 1024
PRODUCT_ID_FILE_NAME: Final = "dkb-fints-product-id"
PROBE_STATE_FILE_NAME: Final = "dkb-fints-probe.json"
PROBE_SENT_AT_FILE_NAME: Final = "dkb-fints-probe-sent-at"
_PARAMETER_SEGMENT_RE: Final = re.compile(r"^HI[A-Z0-9]{3}S$")
_PROBE_TIME_SCRIPT: Final = b"""(() => {
  const element = document.getElementById('probe-sent-local');
  if (!element) return;
  const value = element.dataset.utc || '';
  if (!value) return;
  const instant = new Date(value);
  if (Number.isNaN(instant.getTime())) return;
  try {
    element.textContent = new Intl.DateTimeFormat(undefined, {
      year: 'numeric', month: 'short', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      timeZoneName: 'short'
    }).format(instant);
  } catch (_error) {
    element.textContent = value;
  }
})();
"""


@dataclass(frozen=True, slots=True)
class ProbeView:
    state: str
    message: str
    result: CapabilityProbeResult | None


class DKBProbeController:
    """Own App-private FinTS product registration and one bounded anonymous probe."""

    def __init__(self, data_directory: Path) -> None:
        self.data_directory = data_directory
        self.product_id_file = data_directory / PRODUCT_ID_FILE_NAME
        self.probe_state_file = data_directory / PROBE_STATE_FILE_NAME
        self.probe_sent_at_file = data_directory / PROBE_SENT_AT_FILE_NAME
        self.csrf_token = secrets.token_urlsafe(32)
        self._lock = threading.RLock()
        self._probe_in_progress = False

    def product_id(self) -> str | None:
        try:
            value = self.product_id_file.read_text(encoding="ascii")
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError) as err:
            raise RuntimeError("Cannot read the FinTS product registration state") from err
        try:
            return normalise_product_id(value)
        except ValueError as err:
            raise RuntimeError("Stored FinTS product registration state is invalid") from err

    def configure_product_id(self, value: str) -> None:
        product_id = normalise_product_id(value)
        # Capability evidence belongs to the registration identity that produced it.
        # Remove any previous result before changing that identity so stale BPD data
        # can never be presented as evidence for a newly configured product.
        self.probe_state_file.unlink(missing_ok=True)
        self.probe_sent_at_file.unlink(missing_ok=True)
        atomic_write(self.product_id_file, (product_id + "\n").encode("ascii"))

    def last_probe_sent_at(self) -> str | None:
        """Return the persisted UTC dispatch timestamp for the latest probe attempt."""
        try:
            value = self.probe_sent_at_file.read_text(encoding="ascii").strip()
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError) as err:
            raise RuntimeError("Cannot read the FinTS probe dispatch timestamp") from err
        if not value or len(value) > 40:
            raise RuntimeError("Stored FinTS probe dispatch timestamp is invalid")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as err:
            raise RuntimeError("Stored FinTS probe dispatch timestamp is invalid") from err
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise RuntimeError("Stored FinTS probe dispatch timestamp is invalid")
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")

    def probe_view(self) -> ProbeView:
        with self._lock:
            if self._probe_in_progress:
                return ProbeView("running", "Anonymous DKB FinTS capability probe is running.", None)
        raw = load_json_state(self.probe_state_file)
        if raw is None:
            if self.product_id() is None:
                return ProbeView("registration_required", "Configure the project's own FinTS product registration number before probing DKB.", None)
            return ProbeView("ready", "Registration configured. No DKB capability probe has been run yet.", None)
        try:
            result = _parse_persisted_probe(raw)
        except (TypeError, ValueError) as err:
            raise RuntimeError("Stored DKB capability-probe state is invalid") from err
        if result.outcome == "complete":
            if result.holdings_advertised:
                message = f"DKB BPD advertises {HOLDINGS_PARAMETER_SEGMENT}; authenticated user-capability validation is still required before any holdings implementation."
            else:
                message = f"DKB BPD did not advertise {HOLDINGS_PARAMETER_SEGMENT}; no live holdings capability is assumed."
            return ProbeView("complete", message, result)
        if result.outcome == "bank_rejected":
            return ProbeView(
                "bank_rejected",
                "DKB returned a valid bounded FinTS response without bank parameters. Review the sanitized bank return messages and codes; a newly issued product registration that has not propagated yet is one possible cause, but no capability conclusion is drawn.",
                result,
            )
        if result.outcome == "remote_http_error":
            status = result.http_status if result.http_status is not None else "unknown"
            return ProbeView(
                "remote_http_error",
                f"The DKB FinTS endpoint returned HTTP {status}; no capability conclusion is drawn.",
                result,
            )
        if result.outcome == "transport_error":
            return ProbeView(
                "transport_error",
                "The DKB FinTS transport failed before a usable FinTS response was obtained; no capability conclusion is drawn.",
                result,
            )
        if result.outcome == "protocol_error":
            return ProbeView(
                "protocol_error",
                "The DKB response did not satisfy the bounded FinTS probe parser; no capability conclusion is drawn.",
                result,
            )
        if result.outcome in {"gateway_error", "unexpected_error"}:
            return ProbeView(
                result.outcome,
                "The DKB capability probe failed without usable capability evidence; inspect the App log and do not infer bank capability from this attempt.",
                result,
            )
        return ProbeView("error", "The stored DKB FinTS probe outcome is not recognized.", result)

    def run_probe(self) -> ProbeView:
        product_id = self.product_id()
        if product_id is None:
            return ProbeView("registration_required", "Configure a FinTS product registration number first.", None)
        with self._lock:
            if self._probe_in_progress:
                return ProbeView("running", "A capability probe is already running.", None)
            self._probe_in_progress = True
        try:
            sent_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            atomic_write(self.probe_sent_at_file, (sent_at + "\n").encode("ascii"))
            result = probe_dkb_bpd(product_id)
            save_json_state(self.probe_state_file, result.as_dict())
            if result.outcome == "complete":
                _LOGGER.info(
                    "DKB anonymous FinTS capability probe completed: bpd_version=%s holdings_parameter_advertised=%s",
                    result.bpd_version if result.bpd_version is not None else "unknown",
                    result.holdings_advertised,
                )
            else:
                _LOGGER.warning(
                    "DKB anonymous FinTS capability probe completed without BPD: outcome=%s return_code_count=%s",
                    result.outcome,
                    len(result.return_codes),
                )
        except RemoteApiError as err:
            outcome = "remote_http_error" if err.status else "transport_error"
            failure = CapabilityProbeResult(
                probed_at=datetime.now(timezone.utc).isoformat(),
                bpd_version=None,
                parameter_segments=(),
                return_codes=(),
                holdings_advertised=None,
                outcome=outcome,
                failure_category=outcome,
                http_status=err.status if err.status else None,
            )
            save_json_state(self.probe_state_file, failure.as_dict())
            _LOGGER.warning(
                "DKB anonymous FinTS capability probe failed: %s status=%s",
                type(err).__name__,
                err.status,
            )
        except ProtocolError as err:
            response_sha256 = getattr(err, "response_sha256", None)
            response_bytes = getattr(err, "response_bytes", None)
            raw_response_sha256 = getattr(err, "raw_response_sha256", None)
            raw_response_bytes = getattr(err, "raw_response_bytes", None)
            failure = CapabilityProbeResult(
                probed_at=datetime.now(timezone.utc).isoformat(),
                bpd_version=None,
                parameter_segments=(),
                return_codes=(),
                holdings_advertised=None,
                outcome="protocol_error",
                failure_category="protocol_error",
                response_sha256=response_sha256 if isinstance(response_sha256, str) else None,
                response_bytes=response_bytes if isinstance(response_bytes, int) else None,
                raw_response_sha256=raw_response_sha256 if isinstance(raw_response_sha256, str) else None,
                raw_response_bytes=raw_response_bytes if isinstance(raw_response_bytes, int) else None,
            )
            save_json_state(self.probe_state_file, failure.as_dict())
            _LOGGER.warning("DKB anonymous FinTS capability probe failed: %s", type(err).__name__)
        except GatewayError as err:
            failure = CapabilityProbeResult(
                probed_at=datetime.now(timezone.utc).isoformat(),
                bpd_version=None,
                parameter_segments=(),
                return_codes=(),
                holdings_advertised=None,
                outcome="gateway_error",
                failure_category="gateway_error",
            )
            save_json_state(self.probe_state_file, failure.as_dict())
            _LOGGER.warning("DKB anonymous FinTS capability probe failed: %s", type(err).__name__)
        except Exception:
            failure = CapabilityProbeResult(
                probed_at=datetime.now(timezone.utc).isoformat(),
                bpd_version=None,
                parameter_segments=(),
                return_codes=(),
                holdings_advertised=None,
                outcome="unexpected_error",
                failure_category="unexpected_error",
            )
            save_json_state(self.probe_state_file, failure.as_dict())
            _LOGGER.exception("Unexpected DKB FinTS capability-probe failure")
        finally:
            with self._lock:
                self._probe_in_progress = False
        return self.probe_view()

    def status_document(self, gateway_state: GatewayState) -> dict[str, Any]:
        view = self.probe_view()
        return {
            "gateway": gateway_state.health_document(version=8),
            "fints": {
                "endpoint": DKB_FINTS_ENDPOINT,
                "bank_code": DKB_BANK_CODE,
                "product_version": FINTS_PRODUCT_VERSION,
                "product_registration_configured": self.product_id() is not None,
                "probe_state": view.state,
                "probe_outcome": view.result.outcome if view.result else None,
                "failure_category": view.result.failure_category if view.result else None,
                "http_status": view.result.http_status if view.result else None,
                "bpd_version": view.result.bpd_version if view.result else None,
                "holdings_parameter_segment": HOLDINGS_PARAMETER_SEGMENT,
                "holdings_parameter_advertised": view.result.holdings_advertised if view.result else None,
                "parameter_segments": list(view.result.parameter_segments) if view.result else [],
                "return_codes": list(view.result.return_codes) if view.result else [],
                "return_messages": [message.as_dict() for message in view.result.return_messages] if view.result else [],
                "response_sha256": view.result.response_sha256 if view.result else None,
                "response_bytes": view.result.response_bytes if view.result else None,
                "raw_response_sha256": view.result.raw_response_sha256 if view.result else None,
                "raw_response_bytes": view.result.raw_response_bytes if view.result else None,
                "probed_at": view.result.probed_at if view.result else None,
                "probe_sent_at": self.last_probe_sent_at(),
            },
        }


class DKBIngressServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        state: GatewayState,
        controller: DKBProbeController,
        provider: DkbCsvProvider,
        api_token: str,
        allowed_sources: frozenset[str],
        require_user_header: bool,
    ) -> None:
        self.gateway_state = state
        self.controller = controller
        self.csv_provider = provider
        self.api_token = api_token
        self.allowed_sources = allowed_sources
        self.require_user_header = require_user_header
        self.last_import_notice: tuple[str, str] | None = None
        super().__init__(address, DKBIngressHandler)


class DKBIngressHandler(BaseHTTPRequestHandler):
    """Admin-only Ingress UI for registration and anonymous capability probing."""

    protocol_version = "HTTP/1.1"
    server_version = "PortfolioArchitectDKB"
    sys_version = ""

    @property
    def app_server(self) -> DKBIngressServer:
        return self.server  # type: ignore[return-value]

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorised_ingress():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        path = urlsplit(self.path).path
        if path in {"", "/"}:
            self._html(self._render_page())
            return
        if path == "/probe-time.js":
            self._javascript_status(_PROBE_TIME_SCRIPT, HTTPStatus.OK)
            return
        if path == "/status":
            self._json(self.app_server.controller.status_document(self.app_server.gateway_state))
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

        if path == "/import-csv":
            try:
                nonce, documents = self._read_csv_import_form()
                if not secrets.compare_digest(nonce, self.app_server.controller.csrf_token):
                    raise DkbCsvImportError("Import form session is invalid; reload the page and try again")
                snapshot, summary = parse_dkb_csv_batch(documents)
                previous = self.app_server.csv_provider.snapshot
                self.app_server.csv_provider.replace_snapshot(snapshot)
                if not self.app_server.gateway_state.refresh(trigger="manual"):
                    self.app_server.csv_provider.replace_snapshot(previous)
                    raise DkbCsvImportError("Imported DKB CSV batch could not be activated")
                self.app_server.last_import_notice = (
                    "accepted",
                    f"DKB CSV batch accepted: {summary.position_count} positions from "
                    f"{summary.selected_depot_count} selected depot export(s); snapshot timestamp "
                    f"{summary.generated_at.isoformat(timespec='seconds')}.",
                )
                _LOGGER.info(
                    "DKB CSV import activated a canonical snapshot: input_files=%s selected_exports=%s positions=%s",
                    summary.input_file_count,
                    summary.selected_depot_count,
                    summary.position_count,
                )
            except DkbCsvImportError as err:
                _LOGGER.warning("DKB CSV import rejected")
                self.app_server.last_import_notice = ("rejected", _public_csv_error(err))
                self._html_status(self._render_page(), HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.exception("DKB CSV import failed internally")
                self.app_server.last_import_notice = (
                    "internal_error",
                    "DKB CSV import failed internally; no new snapshot was activated.",
                )
                self._html_status(self._render_page(), HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._html_status(self._render_page(), HTTPStatus.OK)
            return

        if path == "/import-cash":
            try:
                nonce, documents = self._read_csv_import_form(maximum_bytes=MAX_CASH_MULTIPART_BYTES)
                if not secrets.compare_digest(nonce, self.app_server.controller.csrf_token):
                    raise DkbCashCsvImportError("Import form session is invalid; reload the page and try again")
                if len(documents) != 1:
                    raise DkbCashCsvImportError("Import exactly one DKB Girokonto cash CSV")
                cash = parse_dkb_cash_csv(documents[0])
                previous_cash = self.app_server.csv_provider.cash_snapshot
                self.app_server.csv_provider.replace_cash_snapshot(cash)
                self.app_server.csv_provider.persist_cash_snapshot(cash)
                if not self.app_server.gateway_state.refresh(trigger="manual"):
                    self.app_server.csv_provider.replace_cash_snapshot(previous_cash)
                    self.app_server.csv_provider.persist_cash_snapshot(previous_cash)
                    raise DkbCashCsvImportError("Imported DKB cash CSV could not be activated")
                self.app_server.last_import_notice = (
                    "accepted",
                    f"DKB cash CSV accepted: EUR {cash.eligible_eur}; cash timestamp "
                    f"{cash.as_of.isoformat(timespec='seconds')}.",
                )
                _LOGGER.info("DKB cash CSV import activated normalized provider-scoped cash evidence")
            except (DkbCashCsvImportError, DkbCsvImportError) as err:
                _LOGGER.warning("DKB cash CSV import rejected")
                self.app_server.last_import_notice = ("rejected", _public_cash_csv_error(err))
                self._html_status(self._render_page(), HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.exception("DKB cash CSV import failed internally")
                self.app_server.last_import_notice = (
                    "internal_error",
                    "DKB cash CSV import failed internally; no new cash evidence was activated.",
                )
                self._html_status(self._render_page(), HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._html_status(self._render_page(), HTTPStatus.OK)
            return

        try:
            form = self._read_form()
        except ValueError:
            self._empty(HTTPStatus.BAD_REQUEST)
            return
        if not secrets.compare_digest(form.get("csrf", ""), self.app_server.controller.csrf_token):
            self._empty(HTTPStatus.FORBIDDEN)
            return
        if path == "/configure-product":
            if set(form) != {"csrf", "product_id"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                self.app_server.controller.configure_product_id(form.get("product_id", ""))
            except ValueError:
                self._redirect("./?error=invalid_product_id")
                return
            self._redirect("./")
            return
        if path == "/probe":
            if set(form) != {"csrf"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            self.app_server.controller.run_probe()
            self._redirect("./")
            return
        self._empty(HTTPStatus.NOT_FOUND)

    def _read_csv_import_form(self, *, maximum_bytes: int = MAX_MULTIPART_BYTES) -> tuple[str, tuple[bytes, ...]]:
        if sum(len(key) + len(value) for key, value in self.headers.items()) > MAX_HEADER_BYTES:
            raise DkbCsvImportError("Import request headers are too large")
        if self.headers.get_content_type() != "multipart/form-data":
            raise DkbCsvImportError("Import request must use multipart/form-data")
        boundary = self.headers.get_boundary()
        if not boundary:
            raise DkbCsvImportError("Import form boundary is missing")
        try:
            boundary_bytes = boundary.encode("ascii")
        except UnicodeEncodeError as err:
            raise DkbCsvImportError("Import form boundary is invalid") from err
        if not 1 <= len(boundary_bytes) <= MAX_BOUNDARY_BYTES or any(
            byte < 33 or byte > 126 for byte in boundary_bytes
        ):
            raise DkbCsvImportError("Import form boundary is invalid")
        length_token = self.headers.get("Content-Length")
        try:
            length = int(length_token) if length_token is not None else -1
        except ValueError as err:
            raise DkbCsvImportError("Import request length is invalid") from err
        if not 1 <= length <= maximum_bytes:
            raise DkbCsvImportError("Import request is empty or too large")
        body = self.rfile.read(length)
        if len(body) != length:
            raise DkbCsvImportError("Import request body is incomplete")
        return _parse_csv_multipart_body(body, boundary_bytes)

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    do_PATCH = do_PUT
    do_DELETE = do_PUT
    do_HEAD = do_PUT
    do_OPTIONS = do_PUT

    def _read_form(self) -> dict[str, str]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold()
        if content_type != "application/x-www-form-urlencoded":
            raise ValueError("invalid form content type")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as err:
            raise ValueError("invalid content length") from err
        if not 0 < length <= MAX_FORM_BYTES:
            raise ValueError("invalid form length")
        body = self.rfile.read(length)
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True)
        if any(len(values) != 1 for values in parsed.values()):
            raise ValueError("duplicate form key")
        return {key: values[0] for key, values in parsed.items()}

    def _authorised_ingress(self) -> bool:
        total = sum(len(key) + len(value) for key, value in self.headers.items())
        return total <= MAX_HEADER_BYTES and self.client_address[0] in self.app_server.allowed_sources and (not self.app_server.require_user_header or bool(self.headers.get("X-Remote-User-Id")))

    def _render_page(self) -> bytes:
        controller = self.app_server.controller
        view = controller.probe_view()
        product = controller.product_id()
        result = view.result
        probe_sent_at = controller.last_probe_sent_at()
        if probe_sent_at is None:
            probe_sent_display = "not recorded yet"
            probe_sent_utc = "not recorded yet"
            probe_sent_data = ""
        else:
            parsed_sent_at = datetime.fromisoformat(probe_sent_at)
            probe_sent_utc = parsed_sent_at.astimezone(timezone.utc).isoformat(timespec="seconds")
            probe_sent_display = probe_sent_utc
            probe_sent_data = probe_sent_utc
        param = ", ".join(result.parameter_segments) if result and result.parameter_segments else "none recorded"
        codes = ", ".join(result.return_codes) if result and result.return_codes else "none recorded"
        if result and result.return_messages:
            bank_messages = "<ul>" + "".join(
                f"<li><code>{escape(message.code)}</code>: {escape(message.text)}</li>"
                for message in result.return_messages
            ) + "</ul>"
        else:
            bank_messages = "<code>none recorded</code>"
        response_fingerprint = result.response_sha256 if result and result.response_sha256 else "not available"
        response_bytes = str(result.response_bytes) if result and result.response_bytes is not None else "not available"
        raw_response_fingerprint = result.raw_response_sha256 if result and result.raw_response_sha256 else "not available"
        raw_response_bytes = str(result.raw_response_bytes) if result and result.raw_response_bytes is not None else "not available"
        if result is None:
            holdings = "not probed"
        elif result.holdings_advertised is None:
            holdings = "not available"
        else:
            holdings = "yes" if result.holdings_advertised else "no"
        bpd = str(result.bpd_version) if result and result.bpd_version is not None else "unknown"
        suffix = f"…{product[-6:]}" if product and len(product) > 6 else (product or "not configured")
        csrf = escape(controller.csrf_token, quote=True)
        snapshot = self.app_server.csv_provider.holdings_snapshot
        if snapshot is None:
            snapshot_text = "No DKB depot CSV batch has been imported yet."
        else:
            snapshot_text = (
                f"Active private holdings: {len(snapshot.positions)} positions; "
                f"timestamp {snapshot.generated_at.isoformat(timespec='seconds')}."
            )
        cash_snapshot = self.app_server.csv_provider.cash_snapshot
        if cash_snapshot is None:
            cash_text = "No DKB Girokonto cash CSV has been imported yet."
        else:
            cash_text = (
                f"Active private cash: EUR {cash_snapshot.eligible_eur}; "
                f"timestamp {cash_snapshot.as_of.isoformat(timespec='seconds')}."
            )
        notice = ""
        if self.app_server.last_import_notice is not None:
            outcome, message = self.app_server.last_import_notice
            css_class = "ok" if outcome == "accepted" else "warn"
            notice = f'<p class="{css_class}">{escape(message)}</p>'
        body = f"""<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Portfolio Architect Gateway — DKB</title><style>body{{font-family:system-ui,sans-serif;max-width:850px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}}section{{border:1px solid #444;border-radius:12px;padding:1rem;margin:1rem 0}}.static-card{{border:2px solid #14b8a6aa;background:#14b8a612}}.live-card{{border:2px solid #3b82f6aa;background:#3b82f612}}.mode-head{{display:flex;justify-content:space-between;align-items:center;gap:12px}}.badge{{font-size:.78rem;font-weight:800;padding:4px 9px;border-radius:999px;border:1px solid currentColor}}.static-card .badge{{color:#2dd4bf}}.live-card .badge{{color:#60a5fa}}code{{word-break:break-all}}input{{width:min(34rem,95%);padding:.55rem}}button{{padding:.55rem .8rem;margin-top:.5rem}}.warn{{color:#ffca28}}.ok{{color:#66bb6a}}.small{{font-size:.9rem;color:#bbb}}</style></head><body><main><h1>Portfolio Architect Gateway — DKB</h1><section class="static-card"><div class="mode-head"><h2>Static acquisition · DKB CSV</h2><span class="badge">ACTIVE</span></div><p>Portfolio Architect v{escape(__version__)} keeps DKB depot holdings and Girokonto cash are independent evidence families. Uploaded CSVs are parsed only in memory; depot/account identifiers, transaction rows, and raw CSV content are never persisted. Only bounded normalized provider state survives.</p>{notice}<h3>Depot holdings</h3><p>{escape(snapshot_text)}</p><form method=\"post\" action=\"import-csv\" enctype=\"multipart/form-data\"><input type=\"hidden\" name=\"nonce\" value=\"{csrf}\"><label for=\"statement\">Current DKB depot CSV export(s)</label><input id=\"statement\" type=\"file\" name=\"statement\" accept=\"text/csv,.csv\" multiple required><br><button type=\"submit\">Import DKB depot CSV batch</button></form><p class=\"small\">Upload all current DKB depot exports together. Up to {MAX_CSV_FILES} files are accepted. If several dated exports of one depot are included, only the newest is counted. The batch replaces only the DKB holdings evidence.</p><h3>Investment cash</h3><p>{escape(cash_text)}</p><form method=\"post\" action=\"import-cash\" enctype=\"multipart/form-data\"><input type=\"hidden\" name=\"nonce\" value=\"{csrf}\"><label for=\"cash-statement\">DKB Girokonto Umsatzliste CSV</label><input id=\"cash-statement\" type=\"file\" name=\"statement\" accept=\"text/csv,.csv\" required><br><button type=\"submit\">Import DKB cash CSV</button></form><p class=\"small\">The importer uses only the explicit dated EUR Kontostand as cash evidence. Transaction rows and account identifiers are discarded. A negative balance authorizes EUR 0; no overdraft or credit facility is inferred. Importing cash does not refresh holdings evidence, and importing holdings does not refresh cash evidence.</p></section><section class="live-card"><div class="mode-head"><h2>Live acquisition · DKB FinTS</h2><span class="badge">UNAVAILABLE · RESEARCH ONLY</span></div><p>Authenticated FinTS acquisition is not enabled. The controls below are isolated bank-level capability research and cannot replace or fall back from CSV evidence.</p><h3>FinTS registration and research probe</h3><p>Fixed endpoint: <code>{escape(DKB_FINTS_ENDPOINT)}</code><br>Bank code: <code>{escape(DKB_BANK_CODE)}</code><br>Configured registration: <code>{escape(suffix)}</code></p><form method=\"post\" action=\"configure-product\"><input type=\"hidden\" name=\"csrf\" value=\"{csrf}\"><label for=\"product_id\">FinTS product registration number</label><br><input id=\"product_id\" name=\"product_id\" minlength=\"25\" maxlength=\"25\" pattern=\"[A-Za-z0-9]{{25}}\" autocomplete=\"off\" required><br><button type=\"submit\">Store registration number</button></form><p class=\"small\">Use the complete 25-character registration number issued for Portfolio Architect itself. It is transmitted only as the HKVVB product designation; a library/kernel registration must not be reused for production access.</p></section><section class="live-card"><div class="mode-head"><h2>Anonymous BPD capability probe</h2><span class="badge">EXPERIMENTAL · RESEARCH ONLY</span></div><p>State: <strong>{escape(view.state)}</strong><br>Last probe sent: <strong id="probe-sent-local" data-utc="{escape(probe_sent_data, quote=True)}">{escape(probe_sent_display)}</strong><br><span class="small">Displayed in the viewing browser's local timezone when available; authoritative server-side dispatch timestamp · UTC: <code>{escape(probe_sent_utc)}</code></span></p><p>{escape(view.message)}</p><form method=\"post\" action=\"probe\"><input type=\"hidden\" name=\"csrf\" value=\"{csrf}\"><button type=\"submit\" {'disabled' if product is None else ''}>Probe DKB FinTS capabilities</button></form><p>BPD version: <code>{escape(bpd)}</code><br>{HOLDINGS_PARAMETER_SEGMENT} advertised: <strong>{holdings}</strong><br>Observed parameter segments: <code>{escape(param)}</code><br>Bounded return codes: <code>{escape(codes)}</code></p><p>Sanitized bank return messages:</p>{bank_messages}<p>Raw response body SHA-256: <code>{escape(raw_response_fingerprint)}</code><br>Raw response body bytes: <code>{escape(raw_response_bytes)}</code><br>Decoded response SHA-256: <code>{escape(response_fingerprint)}</code><br>Decoded response bytes: <code>{escape(response_bytes)}</code></p><p class=\"small\">Only bounded HIRMG/HIRMS return-message text plus cryptographic response fingerprints and byte counts are retained for diagnostics. The configured product registration is redacted if echoed; arbitrary segment payload and the raw FinTS response are discarded after fingerprinting; exact raw/decoded response bytes never persist. A positive bank-level BPD result is only evidence to continue research; authenticated user-parameter validation is still required before holdings acquisition may be implemented.</p></section><section><h2>Gateway boundary</h2><p>Acquisition mode: <strong>csv</strong></p><p>Bearer token: <code>{escape(self.app_server.api_token)}</code></p><p class=\"small\">The token, normalized DKB holdings/cash state, and FinTS registration state are App-private and survive in-place upgrades. FinTS cannot replace or silently fall back to CSV evidence; authenticated DKB FinTS acquisition remains disabled.</p></section></main><script src="probe-time.js" defer></script></body></html>"""
        return body.encode("utf-8")

    def _security_headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; "
            "form-action 'self'; frame-ancestors 'self'; base-uri 'none'",
        )

    def _javascript_status(self, body: bytes, status: HTTPStatus) -> None:
        self.send_response(status)
        self._security_headers("text/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self._security_headers("text/plain; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _html_status(self, body: bytes, status: HTTPStatus) -> None:
        self.send_response(status)
        self._security_headers("text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
        self.send_header("Allow", "GET, POST")
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
        _LOGGER.info("DKB Gateway Ingress request completed")



def _public_cash_csv_error(err: DkbCashCsvImportError) -> str:
    """Return only bounded static cash-parser errors without uploaded private data."""
    text = " ".join(str(err).split())
    safe = {
        "DKB cash CSV is empty or exceeds the 2 MiB safety limit",
        "DKB cash CSV must use UTF-8 encoding",
        "DKB cash CSV could not be parsed safely",
        "DKB cash CSV is empty or contains too many rows",
        "DKB cash CSV does not contain the required account, balance, and transaction-header rows",
        "DKB cash CSV contains an ambiguous Girokonto account row",
        "DKB cash CSV account row is invalid",
        "DKB cash CSV contains an ambiguous current-balance row",
        "DKB cash CSV current-balance row is invalid",
        "DKB cash CSV does not contain exactly one supported transaction header",
        "DKB cash CSV structural row order is invalid",
        "DKB cash CSV contains a malformed transaction row",
        "DKB cash CSV contains an invalid balance date",
        "DKB cash CSV balance date is in the future",
        "DKB cash CSV balance timestamp is in the future",
        "DKB cash CSV current balance must be denominated in EUR",
        "DKB cash CSV current balance is invalid",
        "DKB cash CSV current balance is outside the allowed range",
        "Import exactly one DKB Girokonto cash CSV",
        "Import form session is invalid; reload the page and try again",
        "Imported DKB cash CSV could not be activated",
    }
    return text if text in safe else "DKB cash CSV was rejected by the bounded importer"


def _public_csv_error(err: DkbCsvImportError) -> str:
    """Return a bounded parser/form reason without uploaded content or identifiers."""
    text = " ".join(str(err).split())
    safe_prefixes = (
        "Import ",
        "DKB CSV ",
        "No valid securities positions",
        "Multiple DKB exports",
        "Aggregated DKB position",
        "Parsed DKB CSV batch",
        "Imported DKB CSV batch",
    )
    if 1 <= len(text) <= 220 and text.startswith(safe_prefixes):
        # Row numbers and fixed parser field labels are safe; provider data is never
        # included by the parser's public exceptions.
        return text
    return "DKB CSV batch was rejected by the bounded import parser"


def _parse_csv_multipart_body(body: bytes, boundary: bytes) -> tuple[str, tuple[bytes, ...]]:
    """Parse one bounded multipart batch with one nonce and up to eight CSV parts."""
    delimiter = b"--" + boundary
    closing = delimiter + b"--"
    if not body.startswith(delimiter + b"\r\n") or closing not in body:
        raise DkbCsvImportError("Import form body is malformed")

    nonce_payload: bytes | None = None
    documents: list[bytes] = []
    total_document_bytes = 0
    for raw_part in body.split(delimiter)[1:]:
        if raw_part.startswith(b"--"):
            break
        if not raw_part.startswith(b"\r\n"):
            raise DkbCsvImportError("Import form part is malformed")
        part = raw_part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        try:
            header_blob, payload = part.split(b"\r\n\r\n", 1)
        except ValueError as err:
            raise DkbCsvImportError("Import form part headers are malformed") from err
        if len(header_blob) > 8192:
            raise DkbCsvImportError("Import form part headers are too large")
        headers = BytesHeaderParser(policy=policy.default).parsebytes(header_blob + b"\r\n")
        if headers.get_content_disposition() != "form-data":
            raise DkbCsvImportError("Import form part disposition is invalid")
        field = headers.get_param("name", header="content-disposition")
        if field == "nonce":
            if nonce_payload is not None or len(payload) > 256:
                raise DkbCsvImportError("Import form session field is invalid")
            nonce_payload = payload
            continue
        if field != "statement":
            raise DkbCsvImportError("Import form contains an unexpected field")
        if len(documents) >= MAX_CSV_FILES:
            raise DkbCsvImportError(f"Import must contain at most {MAX_CSV_FILES} DKB CSV files")
        content_type = headers.get_content_type()
        if content_type not in {
            "text/csv",
            "text/plain",
            "application/csv",
            "application/vnd.ms-excel",
            "application/octet-stream",
        }:
            raise DkbCsvImportError("Uploaded DKB export must be a CSV document")
        if not payload or len(payload) > MAX_CSV_FILE_BYTES:
            raise DkbCsvImportError("DKB CSV is empty or exceeds the 10 MiB per-file limit")
        total_document_bytes += len(payload)
        if total_document_bytes > MAX_CSV_BATCH_BYTES:
            raise DkbCsvImportError("DKB CSV import batch exceeds the 20 MiB safety limit")
        documents.append(payload)

    if nonce_payload is None or not documents:
        raise DkbCsvImportError("Import form is incomplete")
    try:
        nonce = nonce_payload.decode("ascii")
    except UnicodeDecodeError as err:
        raise DkbCsvImportError("Import form session field is invalid") from err
    return nonce, tuple(documents)

def _parse_persisted_probe(raw: dict[str, Any]) -> CapabilityProbeResult:
    schema = raw.get("schema_version")
    if schema == 1:
        expected = {"schema_version", "probed_at", "bpd_version", "parameter_segments", "return_codes", "holdings_advertised"}
        if set(raw) != expected:
            raise ValueError("unsupported probe state")
        outcome = "complete"
        failure_category = None
        http_status = None
        return_messages_raw = []
        response_sha256 = None
        response_bytes = None
        raw_response_sha256 = None
        raw_response_bytes = None
    elif schema == 2:
        expected = {
            "schema_version", "probed_at", "outcome", "failure_category", "http_status",
            "bpd_version", "parameter_segments", "return_codes", "return_messages",
            "response_sha256", "response_bytes", "holdings_advertised",
        }
        if set(raw) != expected:
            raise ValueError("unsupported probe state")
        outcome = raw["outcome"]
        failure_category = raw["failure_category"]
        http_status = raw["http_status"]
        return_messages_raw = raw["return_messages"]
        response_sha256 = raw["response_sha256"]
        response_bytes = raw["response_bytes"]
        raw_response_sha256 = None
        raw_response_bytes = None
        allowed_outcomes = {"complete", "bank_rejected", "remote_http_error", "transport_error", "protocol_error", "gateway_error", "unexpected_error"}
        if not isinstance(outcome, str) or outcome not in allowed_outcomes:
            raise ValueError("invalid probe outcome")
        if failure_category is not None and (not isinstance(failure_category, str) or failure_category not in {"bank_response_without_bpd", "remote_http_error", "transport_error", "protocol_error", "gateway_error", "unexpected_error"}):
            raise ValueError("invalid probe failure category")
        if http_status is not None and (isinstance(http_status, bool) or not isinstance(http_status, int) or not 100 <= http_status <= 599):
            raise ValueError("invalid probe HTTP status")
    elif schema == 3:
        expected = {
            "schema_version", "probed_at", "outcome", "failure_category", "http_status",
            "bpd_version", "parameter_segments", "return_codes", "return_messages",
            "response_sha256", "response_bytes", "raw_response_sha256", "raw_response_bytes",
            "holdings_advertised",
        }
        if set(raw) != expected:
            raise ValueError("unsupported probe state")
        outcome = raw["outcome"]
        failure_category = raw["failure_category"]
        http_status = raw["http_status"]
        return_messages_raw = raw["return_messages"]
        response_sha256 = raw["response_sha256"]
        response_bytes = raw["response_bytes"]
        raw_response_sha256 = raw["raw_response_sha256"]
        raw_response_bytes = raw["raw_response_bytes"]
        allowed_outcomes = {"complete", "bank_rejected", "remote_http_error", "transport_error", "protocol_error", "gateway_error", "unexpected_error"}
        if not isinstance(outcome, str) or outcome not in allowed_outcomes:
            raise ValueError("invalid probe outcome")
        if failure_category is not None and (not isinstance(failure_category, str) or failure_category not in {"bank_response_without_bpd", "remote_http_error", "transport_error", "protocol_error", "gateway_error", "unexpected_error"}):
            raise ValueError("invalid probe failure category")
        if http_status is not None and (isinstance(http_status, bool) or not isinstance(http_status, int) or not 100 <= http_status <= 599):
            raise ValueError("invalid probe HTTP status")
    else:
        raise ValueError("unsupported probe state")

    probed_at = raw["probed_at"]
    bpd_version = raw["bpd_version"]
    parameters = raw["parameter_segments"]
    codes = raw["return_codes"]
    holdings = raw["holdings_advertised"]
    if not isinstance(probed_at, str) or len(probed_at) > 40:
        raise ValueError("invalid probe time")
    try:
        parsed_time = datetime.fromisoformat(probed_at)
    except ValueError as err:
        raise ValueError("invalid probe time") from err
    if parsed_time.tzinfo is None or parsed_time.utcoffset() is None:
        raise ValueError("invalid probe time")
    if bpd_version is not None and (isinstance(bpd_version, bool) or not isinstance(bpd_version, int) or not 0 <= bpd_version <= 999):
        raise ValueError("invalid BPD version")
    if (
        not isinstance(parameters, list)
        or len(parameters) > 128
        or len(set(parameters)) != len(parameters)
        or parameters != sorted(parameters)
        or any(not isinstance(v, str) or _PARAMETER_SEGMENT_RE.fullmatch(v) is None for v in parameters)
    ):
        raise ValueError("invalid parameter list")
    if (
        not isinstance(codes, list)
        or len(codes) > 32
        or len(set(codes)) != len(codes)
        or any(not isinstance(v, str) or len(v) != 4 or not v.isdigit() for v in codes)
    ):
        raise ValueError("invalid return-code list")
    if holdings is not None and not isinstance(holdings, bool):
        raise ValueError("invalid holdings flag")
    if not isinstance(return_messages_raw, list) or len(return_messages_raw) > MAX_RETURN_MESSAGES:
        raise ValueError("invalid return-message list")
    return_messages: list[ReturnMessage] = []
    for item in return_messages_raw:
        if not isinstance(item, dict) or set(item) != {"code", "text"}:
            raise ValueError("invalid return message")
        code = item["code"]
        text = item["text"]
        if not isinstance(code, str) or code not in codes:
            raise ValueError("invalid return-message code")
        if (
            not isinstance(text, str)
            or not text
            or len(text) > MAX_RETURN_MESSAGE_CHARS
            or any(ord(char) < 32 or ord(char) == 127 for char in text)
        ):
            raise ValueError("invalid return-message text")
        message = ReturnMessage(code, text)
        if message in return_messages:
            raise ValueError("duplicate return message")
        return_messages.append(message)
    if response_sha256 is not None and (
        not isinstance(response_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", response_sha256) is None
    ):
        raise ValueError("invalid response fingerprint")
    if response_bytes is not None and (
        isinstance(response_bytes, bool)
        or not isinstance(response_bytes, int)
        or not 1 <= response_bytes <= MAX_RESPONSE_BYTES
    ):
        raise ValueError("invalid response size")
    if (response_sha256 is None) != (response_bytes is None):
        raise ValueError("incomplete response correlation metadata")
    if raw_response_sha256 is not None and (
        not isinstance(raw_response_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", raw_response_sha256) is None
    ):
        raise ValueError("invalid raw response fingerprint")
    if raw_response_bytes is not None and (
        isinstance(raw_response_bytes, bool)
        or not isinstance(raw_response_bytes, int)
        or not 1 <= raw_response_bytes <= MAX_BASE64_RESPONSE_BYTES
    ):
        raise ValueError("invalid raw response size")
    if (raw_response_sha256 is None) != (raw_response_bytes is None):
        raise ValueError("incomplete raw response correlation metadata")

    if outcome == "complete":
        if bpd_version is None or not isinstance(holdings, bool) or failure_category is not None or http_status is not None:
            raise ValueError("inconsistent successful probe state")
        if schema in {2, 3} and (response_sha256 is None or response_bytes is None):
            raise ValueError("successful probe lacks response correlation metadata")
        if schema == 3 and (raw_response_sha256 is None or raw_response_bytes is None):
            raise ValueError("successful probe lacks raw response correlation metadata")
    elif outcome == "bank_rejected":
        if bpd_version is not None or holdings is not None or not codes or failure_category != "bank_response_without_bpd" or http_status is not None:
            raise ValueError("inconsistent bank rejection state")
        if response_sha256 is None or response_bytes is None:
            raise ValueError("bank rejection lacks response correlation metadata")
        if schema == 3 and (raw_response_sha256 is None or raw_response_bytes is None):
            raise ValueError("bank rejection lacks raw response correlation metadata")
    elif outcome == "remote_http_error":
        if http_status is None or failure_category != "remote_http_error" or bpd_version is not None or holdings is not None or parameters or codes or return_messages or response_sha256 is not None or response_bytes is not None or raw_response_sha256 is not None or raw_response_bytes is not None:
            raise ValueError("inconsistent remote HTTP failure state")
    elif outcome in {"transport_error", "protocol_error", "gateway_error", "unexpected_error"}:
        if failure_category != outcome or http_status is not None or bpd_version is not None or holdings is not None or parameters or codes or return_messages:
            raise ValueError("inconsistent probe failure state")
        if outcome != "protocol_error" and (
            response_sha256 is not None or response_bytes is not None
            or raw_response_sha256 is not None or raw_response_bytes is not None
        ):
            raise ValueError("unexpected response correlation metadata")

    return CapabilityProbeResult(
        probed_at, bpd_version, tuple(parameters), tuple(codes), holdings,
        outcome=outcome, failure_category=failure_category, http_status=http_status,
        return_messages=tuple(return_messages),
        response_sha256=response_sha256,
        response_bytes=response_bytes,
        raw_response_sha256=raw_response_sha256,
        raw_response_bytes=raw_response_bytes,
    )


def serve_dkb_probe_app(*, provider_id: str, provider_name: str, options: PendingAppOptions | None = None, data_directory: Path = APP_DATA_DIRECTORY, ingress_address: tuple[str, int] = (INGRESS_BIND, INGRESS_PORT), allowed_ingress_sources: frozenset[str] = frozenset({"172.30.32.2"}), require_user_header: bool = True, ready_callback: Callable[[], None] | None = None, tls_cert_file: Path | None = None, tls_key_file: Path | None = None) -> None:
    """Run DKB CSV acquisition with an isolated anonymous FinTS research probe."""
    data_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    options = options or PendingAppOptions.load()
    server_config = build_server_config(options, data_directory, tls_cert_file=tls_cert_file, tls_key_file=tls_key_file)
    api_token = ensure_api_token(server_config.api_token_file)
    if provider_id != "dkb":
        raise RuntimeError("DKB Gateway provider identity is invalid")
    provider = DkbCsvProvider(server_config.snapshot_file)
    state = GatewayState(server_config, provider)
    state.refresh(trigger="startup")
    controller = DKBProbeController(data_directory)
    if not isinstance(provider_name, str) or not provider_name.strip() or len(provider_name.strip()) > 64:
        raise RuntimeError("Provider display name is invalid")
    gateway_server = create_server(server_config, state)
    ingress_server = DKBIngressServer(
        ingress_address,
        state=state,
        controller=controller,
        provider=provider,
        api_token=api_token,
        allowed_sources=allowed_ingress_sources,
        require_user_header=require_user_header,
    )
    gateway_thread = threading.Thread(target=gateway_server.serve_forever, kwargs={"poll_interval": 0.5}, name="portfolio-dkb-api", daemon=True)
    gateway_thread.start()
    _LOGGER.info("DKB CSV Gateway initialized; FinTS authenticated acquisition remains disabled")
    if ready_callback:
        ready_callback()
    try:
        ingress_server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _LOGGER.info("DKB Gateway shutdown requested")
    finally:
        ingress_server.shutdown()
        ingress_server.server_close()
        gateway_server.shutdown()
        gateway_server.server_close()
        gateway_thread.join(timeout=5)
