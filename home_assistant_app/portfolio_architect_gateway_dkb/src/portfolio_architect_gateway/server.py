"""Authenticated local HTTP gateway and bounded background refresh loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import logging
import secrets
import ssl
import threading
import time
from typing import TYPE_CHECKING, Any, Callable

from . import __version__
from .runtime_config import ServerConfig, read_secret

if TYPE_CHECKING:
    from .config import GatewayConfig
from .errors import (
    AuthenticationError,
    ConfigurationError,
    GatewayError,
    ProtocolError,
    ReauthenticationRequired,
    RemoteApiError,
)
from .models import PortfolioSnapshot
from .provider import (
    PortfolioProvider,
    normalise_poll_interval_seconds,
    normalise_provider_id,
)
from .store import load_snapshot, save_snapshot

_LOGGER = logging.getLogger(__name__)
MAX_REQUEST_HEADER_BYTES = 32 * 1024
HEALTH_V2_MEDIA_TYPE = "application/vnd.portfolio-architect.health+json;version=2"
HEALTH_V3_MEDIA_TYPE = "application/vnd.portfolio-architect.health+json;version=3"
HEALTH_V4_MEDIA_TYPE = "application/vnd.portfolio-architect.health+json;version=4"
HEALTH_V5_MEDIA_TYPE = "application/vnd.portfolio-architect.health+json;version=5"
HEALTH_V6_MEDIA_TYPE = "application/vnd.portfolio-architect.health+json;version=6"
REFRESH_TRIGGERS = frozenset({"startup", "scheduled", "manual", "bootstrap"})
MANUAL_REFRESH_MIN_INTERVAL_SECONDS = 60


@dataclass(frozen=True, slots=True)
class SnapshotView:
    body: bytes
    etag: str
    last_modified: str
    generated_at: datetime
    sha256: str
    position_count: int


class GatewayState:
    """Thread-safe last-known-good snapshot and sanitized health state."""

    def __init__(self, config: ServerConfig, client: PortfolioProvider) -> None:
        self._config = config
        self._client = client
        self._provider_id = normalise_provider_id(client.provider_id)
        self._poll_interval_seconds = normalise_poll_interval_seconds(
            client.poll_interval_seconds
        )
        self._lock = threading.RLock()
        self._snapshot: PortfolioSnapshot | None = load_snapshot(
            config.snapshot_file
        )
        self._last_refresh_success: datetime | None = (
            self._snapshot.generated_at.astimezone(timezone.utc)
            if self._snapshot is not None
            else None
        )
        self._last_refresh_attempt: datetime | None = None
        self._last_error: str | None = None
        self._reauth_required = False
        self._consecutive_refresh_failures = 0
        self._live_refresh_completed = False
        self._refresh_execution_lock = threading.Lock()
        self._refresh_in_progress = False
        self._last_refresh_duration_ms: int | None = None
        self._last_refresh_trigger: str | None = None
        self._next_refresh_due_at: datetime | None = None
        self._last_manual_refresh_request: datetime | None = None
        self._last_refresh_failure_at: datetime | None = None
        self._last_refresh_failure_class: str | None = None
        self._recommended_action = "none"
        self._retry_after_seconds: int | None = None

    def refresh(self, *, trigger: str = "scheduled") -> bool:
        """Fetch and atomically publish one new snapshot without overlapping calls."""
        started = self._begin_refresh(trigger)
        if started is None:
            _LOGGER.info("Portfolio refresh skipped because another refresh is in progress")
            return False
        attempted_at, started_monotonic = started
        return self._execute_refresh(
            trigger=trigger,
            attempted_at=attempted_at,
            started_monotonic=started_monotonic,
        )

    def request_manual_refresh(self) -> tuple[bool, int | None]:
        """Start one bounded manual refresh thread from the protected Ingress UI."""
        now = datetime.now(timezone.utc)
        with self._lock:
            if self._refresh_in_progress:
                return False, 1
            last_request = self._last_manual_refresh_request
            if last_request is not None:
                elapsed = max(0.0, (now - last_request).total_seconds())
                if elapsed < MANUAL_REFRESH_MIN_INTERVAL_SECONDS:
                    remaining = max(
                        1,
                        int(MANUAL_REFRESH_MIN_INTERVAL_SECONDS - elapsed + 0.999),
                    )
                    return False, remaining

        started = self._begin_refresh("manual")
        if started is None:
            return False, 1
        attempted_at, started_monotonic = started
        with self._lock:
            self._last_manual_refresh_request = attempted_at
        thread = threading.Thread(
            target=self._execute_refresh,
            kwargs={
                "trigger": "manual",
                "attempted_at": attempted_at,
                "started_monotonic": started_monotonic,
            },
            name="portfolio-manual-refresh",
            daemon=True,
        )
        try:
            thread.start()
        except Exception:
            self._finish_refresh(started_monotonic)
            raise
        return True, None

    def set_next_refresh_due_at(self, value: datetime | None) -> None:
        """Publish the next fixed-cadence scheduled refresh timestamp."""
        if value is not None:
            value = value.astimezone(timezone.utc)
        with self._lock:
            self._next_refresh_due_at = value

    def _begin_refresh(self, trigger: str) -> tuple[datetime, float] | None:
        if trigger not in REFRESH_TRIGGERS:
            raise ValueError("Unsupported refresh trigger")
        if not self._refresh_execution_lock.acquire(blocking=False):
            return None
        attempted_at = datetime.now(timezone.utc)
        started_monotonic = time.monotonic()
        with self._lock:
            self._last_refresh_attempt = attempted_at
            self._last_refresh_trigger = trigger
            self._refresh_in_progress = True
        return attempted_at, started_monotonic

    def _execute_refresh(
        self,
        *,
        trigger: str,
        attempted_at: datetime,
        started_monotonic: float,
    ) -> bool:
        success = False
        try:
            snapshot = self._client.fetch_snapshot()
            save_snapshot(self._config.snapshot_file, snapshot)
        except ReauthenticationRequired:
            self._record_refresh_failure(
                attempted_at=attempted_at,
                error_code="reauthentication_required",
                failure_class="reauthentication_required",
                recommended_action="reauthenticate",
                reauthentication_required=True,
            )
            _LOGGER.warning("Portfolio refresh requires provider reauthentication")
        except AuthenticationError as err:
            self._record_refresh_failure(
                attempted_at=attempted_at,
                error_code=type(err).__name__,
                failure_class="authentication_error",
                recommended_action="reauthenticate",
                reauthentication_required=True,
            )
            _LOGGER.warning("Portfolio refresh authentication failed")
        except RemoteApiError as err:
            failure_class, action = _classify_remote_api_error(err)
            self._record_refresh_failure(
                attempted_at=attempted_at,
                error_code=type(err).__name__,
                failure_class=failure_class,
                recommended_action=action,
                retry_after_seconds=err.retry_after,
            )
            _LOGGER.warning(
                "Portfolio refresh remote API failure: status=%s operation=%s",
                err.status,
                err.operation or "unknown",
            )
        except ProtocolError:
            self._record_refresh_failure(
                attempted_at=attempted_at,
                error_code="ProtocolError",
                failure_class="invalid_response",
                recommended_action="inspect_logs",
            )
            _LOGGER.warning("Portfolio refresh rejected an invalid upstream response")
        except ConfigurationError:
            self._record_refresh_failure(
                attempted_at=attempted_at,
                error_code="ConfigurationError",
                failure_class="configuration_error",
                recommended_action="fix_configuration",
            )
            _LOGGER.warning("Portfolio refresh failed because the Gateway configuration is invalid")
        except GatewayError as err:
            self._record_refresh_failure(
                attempted_at=attempted_at,
                error_code=type(err).__name__,
                failure_class="gateway_error",
                recommended_action="inspect_logs",
            )
            _LOGGER.warning("Portfolio refresh failed: %s", type(err).__name__)
        except Exception:
            self._record_refresh_failure(
                attempted_at=attempted_at,
                error_code="unexpected_error",
                failure_class="internal_error",
                recommended_action="inspect_logs",
            )
            _LOGGER.exception("Unexpected portfolio refresh failure")
        else:
            completed_at = datetime.now(timezone.utc)
            with self._lock:
                self._snapshot = snapshot
                self._last_refresh_success = completed_at
                self._last_error = None
                self._reauth_required = False
                self._consecutive_refresh_failures = 0
                self._live_refresh_completed = True
                self._last_refresh_failure_at = None
                self._last_refresh_failure_class = None
                self._recommended_action = "none"
                self._retry_after_seconds = None
            _LOGGER.info("Portfolio snapshot refreshed successfully")
            success = True
        finally:
            self._finish_refresh(started_monotonic)
        return success

    def _finish_refresh(self, started_monotonic: float) -> None:
        duration_ms = max(0, int(round((time.monotonic() - started_monotonic) * 1000)))
        with self._lock:
            self._last_refresh_duration_ms = min(duration_ms, 600000)
            self._refresh_in_progress = False
        self._refresh_execution_lock.release()

    def _record_refresh_failure(
        self,
        *,
        attempted_at: datetime,
        error_code: str,
        failure_class: str,
        recommended_action: str,
        retry_after_seconds: int | None = None,
        reauthentication_required: bool = False,
    ) -> None:
        """Publish one sanitized refresh failure without retaining remote content."""
        retry_after = None
        if retry_after_seconds is not None:
            retry_after = min(max(int(retry_after_seconds), 0), 86400)
        with self._lock:
            self._last_error = error_code
            self._reauth_required = reauthentication_required
            self._consecutive_refresh_failures += 1
            self._last_refresh_failure_at = attempted_at.astimezone(timezone.utc)
            self._last_refresh_failure_class = failure_class
            self._recommended_action = recommended_action
            self._retry_after_seconds = retry_after

    def snapshot_view(self) -> SnapshotView | None:
        with self._lock:
            snapshot = self._snapshot
        if snapshot is None:
            return None
        maximum = self._config.max_cached_snapshot_age_seconds
        if maximum:
            age = (
                datetime.now(timezone.utc)
                - snapshot.generated_at.astimezone(timezone.utc)
            ).total_seconds()
            if age > maximum:
                return None
        generated_at = snapshot.generated_at.astimezone(timezone.utc)
        body = snapshot.to_bytes()
        digest = hashlib.sha256(body).hexdigest()
        return SnapshotView(
            body=body,
            etag=f'"sha256-{digest}"',
            last_modified=format_datetime(generated_at, usegmt=True),
            generated_at=generated_at,
            sha256=digest,
            position_count=len(snapshot.positions),
        )

    @property
    def poll_interval_seconds(self) -> int:
        """Return the validated provider refresh cadence."""
        return self._poll_interval_seconds

    def health_document(self, *, version: int = 1) -> dict[str, Any]:
        with self._lock:
            last_success = self._last_refresh_success
            last_attempt = self._last_refresh_attempt
            last_error = self._last_error
            reauth = self._reauth_required
            failures = self._consecutive_refresh_failures
            live_refresh_completed = self._live_refresh_completed
            refresh_in_progress = self._refresh_in_progress
            last_refresh_duration_ms = self._last_refresh_duration_ms
            last_refresh_trigger = self._last_refresh_trigger
            next_refresh_due_at = self._next_refresh_due_at
            last_refresh_failure_at = self._last_refresh_failure_at
            last_refresh_failure_class = self._last_refresh_failure_class
            recommended_action = self._recommended_action
            retry_after_seconds = self._retry_after_seconds
        view = self.snapshot_view()
        now = datetime.now(timezone.utc)
        generated_at = None
        snapshot_age_seconds = None
        snapshot_expires_in_seconds = None
        # Health schema 3+ deliberately exposes age metadata only while the
        # snapshot is available through the normal runtime endpoint. An expired
        # cached snapshot remains private state, but must not produce the
        # inconsistent combination snapshot_available=false plus age metadata.
        if view is not None:
            generated = view.generated_at
            generated_at = generated.isoformat(timespec="seconds")
            snapshot_age_seconds = max(0, int((now - generated).total_seconds()))
            maximum = self._config.max_cached_snapshot_age_seconds
            if maximum:
                snapshot_expires_in_seconds = max(0, maximum - snapshot_age_seconds)

        if reauth:
            operating_mode = "reauthentication_required"
        elif view is None:
            operating_mode = "unavailable"
        elif last_error is not None or failures > 0 or not live_refresh_completed:
            operating_mode = "last_known_good"
        else:
            operating_mode = "live"

        document = {
            "gateway_version": __version__,
            "status": "ok" if operating_mode == "live" else "degraded",
            "snapshot_available": view is not None,
            "snapshot_generated_at": generated_at,
            "last_refresh_success": (
                last_success.isoformat(timespec="seconds") if last_success else None
            ),
            "reauthentication_required": reauth,
            "last_error": last_error,
        }
        if version >= 2:
            document.update(
                {
                    "health_schema_version": min(version, 6),
                    "snapshot_sha256": view.sha256 if view is not None else None,
                    "snapshot_position_count": (
                        view.position_count if view is not None else None
                    ),
                    "poll_interval_seconds": (
                        self._poll_interval_seconds
                    ),
                    "max_cached_snapshot_age_seconds": (
                        self._config.max_cached_snapshot_age_seconds
                    ),
                }
            )
        if version >= 3:
            document.update(
                {
                    "operating_mode": operating_mode,
                    "last_refresh_attempt": (
                        last_attempt.isoformat(timespec="seconds")
                        if last_attempt
                        else None
                    ),
                    "consecutive_refresh_failures": failures,
                    "snapshot_age_seconds": snapshot_age_seconds,
                    "snapshot_expires_in_seconds": snapshot_expires_in_seconds,
                }
            )
        if version >= 4:
            document.update(
                {
                    "refresh_in_progress": refresh_in_progress,
                    "last_refresh_duration_ms": last_refresh_duration_ms,
                    "last_refresh_trigger": last_refresh_trigger,
                    "next_refresh_due_at": (
                        next_refresh_due_at.isoformat(timespec="seconds")
                        if next_refresh_due_at
                        else None
                    ),
                    "manual_refresh_min_interval_seconds": (
                        MANUAL_REFRESH_MIN_INTERVAL_SECONDS
                    ),
                }
            )
        if version >= 5:
            document.update(
                {
                    "last_refresh_failure_at": (
                        last_refresh_failure_at.isoformat(timespec="seconds")
                        if last_refresh_failure_at
                        else None
                    ),
                    "last_refresh_failure_class": last_refresh_failure_class,
                    "recommended_action": recommended_action,
                    "retry_after_seconds": retry_after_seconds,
                }
            )
        if version >= 6:
            document["provider_id"] = self._provider_id
        return document


def _classify_remote_api_error(err: RemoteApiError) -> tuple[str, str]:
    """Map a bounded upstream HTTP failure to stable operational guidance."""
    if err.status == 0:
        return "transport_error", "check_connectivity"
    if err.status == 429:
        return "rate_limited", "wait"
    if 500 <= err.status <= 599:
        return "remote_service_error", "wait"
    return "remote_api_error", "inspect_logs"


class GatewayHttpServer(ThreadingHTTPServer):
    """Threading server carrying immutable auth and shared state."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        state: GatewayState,
        api_token: str,
        *,
        health_endpoint_enabled: bool,
    ) -> None:
        self.gateway_state = state
        self.api_token = api_token
        self.health_endpoint_enabled = health_endpoint_enabled
        super().__init__(server_address, GatewayRequestHandler)


class GatewayRequestHandler(BaseHTTPRequestHandler):
    """GET-only authenticated local API with conditional response support."""

    protocol_version = "HTTP/1.1"
    server_version = "PortfolioArchitectGateway"
    sys_version = ""

    @property
    def gateway_server(self) -> GatewayHttpServer:
        return self.server  # type: ignore[return-value]

    def do_GET(self) -> None:  # noqa: N802
        if not self._headers_within_limit():
            self._send_error(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE)
            return
        if not self._authenticated():
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.send_header("WWW-Authenticate", 'Bearer realm="portfolio-architect"')
            self._security_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path in {"/api/v1/portfolio", "/v1/portfolio"}:
            self._serve_portfolio()
            return
        if self.path == "/healthz" and self.gateway_server.health_endpoint_enabled:
            self._serve_health()
            return
        self._send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PATCH(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_DELETE(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_HEAD(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def _serve_portfolio(self) -> None:
        view = self.gateway_server.gateway_state.snapshot_view()
        if view is None:
            self._send_error(HTTPStatus.SERVICE_UNAVAILABLE, retry_after=60)
            return
        if_none_match = self.headers.get("If-None-Match")
        if if_none_match is not None:
            if if_none_match == view.etag:
                self.send_response(HTTPStatus.NOT_MODIFIED)
                self.send_header("ETag", view.etag)
                self.send_header("Last-Modified", view.last_modified)
                self._snapshot_integrity_headers(view)
                self._security_headers()
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        elif _not_modified_since(
            self.headers.get("If-Modified-Since"), view.generated_at
        ):
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.send_header("ETag", view.etag)
            self.send_header("Last-Modified", view.last_modified)
            self._snapshot_integrity_headers(view)
            self._security_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("ETag", view.etag)
        self.send_header("Last-Modified", view.last_modified)
        self._snapshot_integrity_headers(view)
        self._security_headers()
        self.send_header("Content-Length", str(len(view.body)))
        self.end_headers()
        self.wfile.write(view.body)

    def _serve_health(self) -> None:
        accept = self.headers.get("Accept", "")
        use_v6 = HEALTH_V6_MEDIA_TYPE in accept
        use_v5 = not use_v6 and HEALTH_V5_MEDIA_TYPE in accept
        use_v4 = not use_v6 and not use_v5 and HEALTH_V4_MEDIA_TYPE in accept
        use_v3 = not use_v6 and not use_v5 and not use_v4 and HEALTH_V3_MEDIA_TYPE in accept
        use_v2 = (
            not use_v6 and not use_v5 and not use_v4 and not use_v3
            and HEALTH_V2_MEDIA_TYPE in accept
        )
        version = (
            6 if use_v6 else 5 if use_v5 else 4 if use_v4 else 3 if use_v3 else 2 if use_v2 else 1
        )
        body = json.dumps(
            self.gateway_server.gateway_state.health_document(version=version),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        content_type = (
            HEALTH_V6_MEDIA_TYPE
            if use_v6
            else HEALTH_V5_MEDIA_TYPE
            if use_v5
            else HEALTH_V4_MEDIA_TYPE
            if use_v4
            else HEALTH_V3_MEDIA_TYPE
            if use_v3
            else HEALTH_V2_MEDIA_TYPE
            if use_v2
            else "application/json"
        )
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self._security_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _snapshot_integrity_headers(self, view: SnapshotView) -> None:
        self.send_header("X-Portfolio-Snapshot-SHA256", view.sha256)
        self.send_header(
            "X-Portfolio-Position-Count", str(view.position_count)
        )

    def _authenticated(self) -> bool:
        value = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not value.startswith(prefix):
            return False
        supplied = value[len(prefix) :]
        return secrets.compare_digest(supplied, self.gateway_server.api_token)

    def _headers_within_limit(self) -> bool:
        total = sum(len(key) + len(value) for key, value in self.headers.items())
        return total <= MAX_REQUEST_HEADER_BYTES

    def _method_not_allowed(self) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", "GET")
        self._security_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_error(
        self, status: HTTPStatus, *, retry_after: int | None = None
    ) -> None:
        self.send_response(status)
        if retry_after is not None:
            self.send_header("Retry-After", str(retry_after))
        self._security_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "private, no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")

    def log_message(self, format: str, *args: Any) -> None:
        # The service has only fixed paths and no query API. Keep logs free of headers.
        _LOGGER.info("Gateway request completed for client %s", self.client_address[0])


def create_server(
    config: ServerConfig,
    state: GatewayState,
) -> GatewayHttpServer:
    token = read_secret(
        config.api_token_file,
        name="gateway API token",
        minimum=32,
        maximum=512,
    )
    server = GatewayHttpServer(
        (config.bind, config.port),
        state,
        token,
        health_endpoint_enabled=config.health_endpoint_enabled,
    )
    if config.tls_cert_file and config.tls_key_file:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(
            certfile=config.tls_cert_file,
            keyfile=config.tls_key_file,
        )
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def run_refresh_loop(
    state: GatewayState,
    interval_seconds: int,
    stop_event: threading.Event,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Refresh immediately, then retain a fixed cadence without duration drift."""
    del sleep  # Retained for backward-compatible test and caller signatures.
    if stop_event.is_set():
        return
    state.set_next_refresh_due_at(None)
    state.refresh(trigger="startup")
    next_deadline = time.monotonic() + interval_seconds

    while not stop_event.is_set():
        now_monotonic = time.monotonic()
        delay = max(0.0, next_deadline - now_monotonic)
        state.set_next_refresh_due_at(
            datetime.now(timezone.utc) + timedelta(seconds=delay)
        )
        if stop_event.wait(delay):
            state.set_next_refresh_due_at(None)
            return
        state.set_next_refresh_due_at(None)
        state.refresh(trigger="scheduled")
        now_monotonic = time.monotonic()
        next_deadline += interval_seconds
        while next_deadline <= now_monotonic:
            next_deadline += interval_seconds


def serve(config: GatewayConfig, client: PortfolioProvider) -> None:
    state = GatewayState(config.server, client)
    stop_event = threading.Event()
    refresher = threading.Thread(
        target=run_refresh_loop,
        args=(state, state.poll_interval_seconds, stop_event),
        name="portfolio-refresh",
        daemon=True,
    )
    server = create_server(config.server, state)
    refresher.start()
    scheme = "https" if config.server.tls_cert_file else "http"
    _LOGGER.info(
        "Gateway listening on %s://%s:%d",
        scheme,
        config.server.bind,
        config.server.port,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _LOGGER.info("Gateway shutdown requested")
    finally:
        stop_event.set()
        server.server_close()
        refresher.join(timeout=5)


def _not_modified_since(value: str | None, generated_at: datetime) -> bool:
    if not value:
        return False
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc) >= generated_at.astimezone(timezone.utc).replace(
        microsecond=0
    )
