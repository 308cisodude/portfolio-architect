"""Home Assistant App runtime with authenticated Ingress bootstrap UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import secrets
import threading
from typing import Any, Callable, Final
from urllib.parse import parse_qs, urlsplit

from .cash_policy import MODE_ALL_AVAILABLE, MODE_CAPPED, MODE_RETAIN, parse_policy_input
from .comdirect import AccountBalanceCandidate, ComdirectClient
from .config import ComdirectConfig, GatewayConfig
from .runtime_config import ServerConfig, atomic_secret, ensure_api_token
from .errors import GatewayError, RemoteApiError
from .server import GatewayState, create_server, run_refresh_loop

_LOGGER = logging.getLogger(__name__)
APP_DATA_DIRECTORY: Final = Path("/data/gateway")
OPTIONS_FILE: Final = Path("/data/options.json")
INGRESS_BIND: Final = "0.0.0.0"
INGRESS_PORT: Final = 8099
GATEWAY_PORT: Final = 8787
MAX_FORM_BYTES: Final = 16 * 1024
MAX_HEADER_BYTES: Final = 32 * 1024
MAX_CHUNK_LINE_BYTES: Final = 128
LOCAL_ENDPOINT: Final = (
    "https://local-portfolio-architect-gateway:8787/api/v1/portfolio"
)


@dataclass(frozen=True, slots=True)
class AppOptions:
    """Strict non-secret Home Assistant App options."""

    poll_interval_seconds: int = 900
    max_cached_snapshot_age_seconds: int = 604800
    request_timeout_seconds: int = 20
    mfa_timeout_seconds: int = 180
    health_endpoint_enabled: bool = True
    depot_ids: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: Path = OPTIONS_FILE) -> "AppOptions":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = {}
        except (OSError, UnicodeError, json.JSONDecodeError) as err:
            raise RuntimeError("Home Assistant App options are unreadable") from err
        if not isinstance(raw, dict):
            raise RuntimeError("Home Assistant App options must be an object")
        allowed = {
            "poll_interval_seconds",
            "max_cached_snapshot_age_seconds",
            "request_timeout_seconds",
            "mfa_timeout_seconds",
            "health_endpoint_enabled",
            "depot_ids",
        }
        unknown = set(raw) - allowed
        if unknown:
            raise RuntimeError("Home Assistant App options contain unsupported keys")
        depot_raw = raw.get("depot_ids", [])
        if not isinstance(depot_raw, list) or len(depot_raw) > 32:
            raise RuntimeError("depot_ids must be a list with at most 32 entries")
        depot_ids: list[str] = []
        for value in depot_raw:
            if not isinstance(value, str):
                raise RuntimeError("Every depot ID must be text")
            cleaned = value.strip()
            if (
                not cleaned
                or len(cleaned) > 64
                or any(ord(char) < 33 or ord(char) > 126 for char in cleaned)
                or cleaned in depot_ids
            ):
                raise RuntimeError("depot_ids contains an invalid or duplicate entry")
            depot_ids.append(cleaned)
        return cls(
            poll_interval_seconds=_bounded_int(
                raw.get("poll_interval_seconds", 900), 300, 86400, "poll interval"
            ),
            max_cached_snapshot_age_seconds=_bounded_int(
                raw.get("max_cached_snapshot_age_seconds", 604800),
                0,
                2592000,
                "maximum cached snapshot age",
            ),
            request_timeout_seconds=_bounded_int(
                raw.get("request_timeout_seconds", 20), 5, 60, "request timeout"
            ),
            mfa_timeout_seconds=_bounded_int(
                raw.get("mfa_timeout_seconds", 180), 30, 600, "MFA timeout"
            ),
            health_endpoint_enabled=_bool(
                raw.get("health_endpoint_enabled", True), "health endpoint"
            ),
            depot_ids=tuple(depot_ids),
        )


def _bounded_int(value: Any, minimum: int, maximum: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} is outside the supported range")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise RuntimeError(f"{name} must be true or false")
    return value



def build_app_config(
    options: AppOptions,
    data_directory: Path = APP_DATA_DIRECTORY,
    *,
    tls_cert_file: Path | None = None,
    tls_key_file: Path | None = None,
) -> GatewayConfig:
    """Construct the fixed, private-network runtime configuration for HAOS."""
    return GatewayConfig(
        server=ServerConfig(
            bind="0.0.0.0",
            port=GATEWAY_PORT,
            api_token_file=data_directory / "gateway-api-token",
            snapshot_file=data_directory / "portfolio.json",
            max_cached_snapshot_age_seconds=options.max_cached_snapshot_age_seconds,
            tls_cert_file=tls_cert_file,
            tls_key_file=tls_key_file,
            health_endpoint_enabled=options.health_endpoint_enabled,
        ),
        comdirect=ComdirectConfig(
            base_url="https://api.comdirect.de",
            client_id_file=data_directory / "comdirect-client-id",
            client_secret_file=data_directory / "comdirect-client-secret",
            username_file=data_directory / ".username-not-persisted",
            password_file=data_directory / ".password-not-persisted",
            session_file=data_directory / "comdirect-session.json",
            investment_account_file=data_directory / "investment-account.json",
            investment_cash_policy_file=data_directory / "investment-cash-policy.json",
            poll_interval_seconds=options.poll_interval_seconds,
            request_timeout_seconds=options.request_timeout_seconds,
            mfa_timeout_seconds=options.mfa_timeout_seconds,
            depot_ids=options.depot_ids,
        ),
    )


@dataclass(frozen=True, slots=True)
class BootstrapView:
    state: str
    message: str
    started_at: str | None
    completed_at: str | None


@dataclass(frozen=True, slots=True)
class InvestmentAccountView:
    """Bounded admin-only account-selection state without account identifiers."""

    state: str
    message: str
    selected_label: str | None
    candidates: tuple[dict[str, str], ...]


class AppController:
    """Coordinate background refresh, one bootstrap operation, and safe UI state."""

    def __init__(
        self,
        config: GatewayConfig,
        client: ComdirectClient,
        state: GatewayState,
        api_token: str,
        endpoint_url: str = LOCAL_ENDPOINT,
    ) -> None:
        self.config = config
        self.client = client
        self.gateway_state = state
        self.api_token = api_token
        self.endpoint_url = endpoint_url
        self.csrf_token = secrets.token_urlsafe(32)
        self._lock = threading.RLock()
        self._bootstrap = BootstrapView("idle", "Ready for setup.", None, None)
        self._bootstrap_thread: threading.Thread | None = None
        self._account_tokens: dict[str, str] = {}
        self._account_view = InvestmentAccountView(
            "idle",
            "Discover eligible EUR accounts before enabling gateway-balance execution.",
            "Configured account" if client.selected_investment_account_id() else None,
            (),
        )

    def bootstrap_view(self) -> BootstrapView:
        with self._lock:
            return self._bootstrap

    def account_view(self) -> InvestmentAccountView:
        with self._lock:
            return self._account_view

    def status_document(self) -> dict[str, Any]:
        bootstrap = self.bootstrap_view()
        account = self.account_view()
        policy = self.client.investment_cash_policy()
        return {
            "bootstrap": {
                "state": bootstrap.state,
                "message": bootstrap.message,
                "started_at": bootstrap.started_at,
                "completed_at": bootstrap.completed_at,
            },
            "investment_account": {
                "state": account.state,
                "message": account.message,
                "selected": account.selected_label is not None,
                "selected_label": account.selected_label,
                "candidates": list(account.candidates),
            },
            "investment_cash_policy": {
                "mode": policy.mode,
                "cap_eur": format(policy.cap_eur, "f") if policy.cap_eur is not None else None,
                **(
                    {"retain_eur": format(policy.retain_eur, "f")}
                    if policy.retain_eur is not None
                    else {}
                ),
            },
            "gateway": self.gateway_state.health_document(version=6),
            "client_credentials_configured": (
                self.config.comdirect.client_id_file.is_file()
                and self.config.comdirect.client_secret_file.is_file()
            ),
            "endpoint": self.endpoint_url,
        }

    def discover_investment_accounts(self) -> None:
        """Discover masked account candidates through an authenticated live call."""
        try:
            candidates = self.client.discover_investment_accounts()
            selected_id = self.client.selected_investment_account_id()
        except GatewayError as err:
            _LOGGER.warning("Investment-account discovery failed: %s", type(err).__name__)
            with self._lock:
                self._account_tokens = {}
                self._account_view = InvestmentAccountView(
                    "error", _public_account_error(err), None, ()
                )
            return
        except Exception:
            _LOGGER.exception("Unexpected investment-account discovery failure")
            with self._lock:
                self._account_tokens = {}
                self._account_view = InvestmentAccountView(
                    "error", "Account discovery failed. Review the App log and retry.", None, ()
                )
            return
        token_map: dict[str, str] = {}
        views: list[dict[str, str]] = []
        selected_label = None
        for candidate in candidates:
            token = secrets.token_urlsafe(24)
            token_map[token] = candidate.account_id
            label = candidate.masked_label
            if candidate.account_id == selected_id:
                selected_label = label
            views.append(
                {
                    "token": token,
                    "label": label,
                    "account_balance_eur": format(candidate.account_balance_eur, "f"),
                    "available_eur": format(candidate.available_eur, "f"),
                    "as_of": candidate.as_of.isoformat(timespec="seconds"),
                }
            )
        message = (
            f"Found {len(views)} eligible EUR account candidate"
            + ("." if len(views) == 1 else "s.")
            if views
            else "No eligible EUR account with an available-cash balance was returned."
        )
        with self._lock:
            self._account_tokens = token_map
            self._account_view = InvestmentAccountView(
                "ready" if views else "empty", message, selected_label, tuple(views)
            )

    def select_investment_account(self, selection_token: str) -> None:
        """Persist one token-mapped account and refresh the bounded snapshot."""
        with self._lock:
            account_id = self._account_tokens.get(selection_token)
        if account_id is None:
            raise ValueError("Unknown or expired account selection")
        try:
            selected = self.client.select_investment_account(account_id)
            refreshed = self.gateway_state.refresh(trigger="manual")
        except GatewayError as err:
            _LOGGER.warning("Investment-account selection failed: %s", type(err).__name__)
            with self._lock:
                self._account_view = InvestmentAccountView(
                    "error", _public_account_error(err), self._account_view.selected_label, self._account_view.candidates
                )
            return
        message = (
            "Investment account selected and the live reserve was refreshed."
            if refreshed
            else "Investment account selected, but the portfolio refresh did not complete. Retry after restoring live access."
        )
        with self._lock:
            self._account_view = InvestmentAccountView(
                "selected" if refreshed else "warning",
                message,
                selected.masked_label,
                self._account_view.candidates,
            )

    def clear_investment_account(self) -> None:
        """Remove the selection and publish a snapshot without a reserve."""
        self.client.clear_investment_account()
        refreshed = self.gateway_state.refresh(trigger="manual")
        with self._lock:
            self._account_tokens = {}
            self._account_view = InvestmentAccountView(
                "idle" if refreshed else "warning",
                (
                    "Investment-account selection cleared."
                    if refreshed
                    else "Selection cleared, but the portfolio refresh did not complete."
                ),
                None,
                (),
            )

    def set_investment_cash_policy(self, *, mode: str, cap_eur: str, retain_eur: str = "") -> None:
        """Persist a validated authorization policy and refresh the live snapshot."""
        policy = parse_policy_input(mode, cap_eur, retain_eur)
        self.client.set_investment_cash_policy(policy)
        refreshed = self.gateway_state.refresh(trigger="manual")
        if not refreshed:
            _LOGGER.warning("Investment cash policy saved, but the live refresh did not complete")

    def start_bootstrap(
        self,
        *,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
    ) -> bool:
        """Start one in-memory PhotoTAN bootstrap; return false if already running."""
        with self._lock:
            if self._bootstrap_thread and self._bootstrap_thread.is_alive():
                return False
            started = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._bootstrap = BootstrapView(
                "running",
                "Authentication started. Approve the PhotoTAN push request.",
                started,
                None,
            )
            thread = threading.Thread(
                target=self._run_bootstrap,
                kwargs={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "username": username,
                    "password": password,
                },
                name="comdirect-bootstrap",
                daemon=True,
            )
            self._bootstrap_thread = thread
            thread.start()
            return True

    def start_manual_refresh(self) -> tuple[bool, int | None]:
        """Request one non-overlapping, rate-limited live portfolio refresh."""
        return self.gateway_state.request_manual_refresh()

    def _set_bootstrap(self, state: str, message: str) -> None:
        completed = None
        if state in {"success", "error"}:
            completed = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock:
            self._bootstrap = BootstrapView(
                state,
                message,
                self._bootstrap.started_at,
                completed,
            )

    def _run_bootstrap(
        self,
        *,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
    ) -> None:
        try:
            self.client.bootstrap_with_credentials(
                client_id=client_id,
                client_secret=client_secret,
                username=username,
                password=password,
                prompt=_reject_non_push_prompt,
                output=self._bootstrap_output,
            )
            atomic_secret(
                self.config.comdirect.client_id_file,
                client_id,
                name="Comdirect client ID",
                maximum=512,
            )
            atomic_secret(
                self.config.comdirect.client_secret_file,
                client_secret,
                name="Comdirect client secret",
                maximum=1024,
            )
            if not self.gateway_state.refresh(trigger="bootstrap"):
                raise RuntimeError("Authentication succeeded but the portfolio refresh failed")
        except GatewayError as err:
            if isinstance(err, RemoteApiError):
                _LOGGER.warning(
                    "Comdirect bootstrap failed: RemoteApiError operation=%s status=%s",
                    err.operation or "unknown",
                    err.status,
                )
            else:
                _LOGGER.warning("Comdirect bootstrap failed: %s", type(err).__name__)
            self._set_bootstrap("error", _public_bootstrap_error(err))
        except Exception:
            _LOGGER.exception("Unexpected Comdirect bootstrap failure")
            self._set_bootstrap(
                "error",
                "Setup failed. Review the App log and retry without changing the CSV source.",
            )
        else:
            self._set_bootstrap(
                "success",
                "Authentication and the first portfolio refresh completed successfully.",
            )
        finally:
            # Python cannot guarantee zeroisation of immutable strings. Keeping them only
            # in this short-lived thread prevents persistence in options, files, or logs.
            client_id = client_secret = username = password = ""

    def _bootstrap_output(self, message: str) -> None:
        if "Approve" in message and "PhotoTAN" in message:
            self._set_bootstrap(
                "running", "PhotoTAN approval requested. Approve it on the registered device."
            )


def _reject_non_push_prompt(_message: str) -> str:
    raise RuntimeError(
        "The Home Assistant App supports the PhotoTAN push flow only; an interactive TAN was requested"
    )


def _public_account_error(err: GatewayError) -> str:
    if type(err).__name__ == "ReauthenticationRequired":
        return "Comdirect requires another PhotoTAN bootstrap before accounts can be read."
    if isinstance(err, RemoteApiError):
        result = "transport failure" if err.status == 0 else f"HTTP {err.status}"
        return f"Comdirect account-balance retrieval failed with {result}."
    if type(err).__name__ == "ProtocolError":
        return "Comdirect returned an unexpected account-balance response."
    if type(err).__name__ == "ConfigurationError":
        return "The selected investment account is no longer available."
    return "Account operation failed. Review the App log and retry."


def _public_bootstrap_error(err: GatewayError) -> str:
    name = type(err).__name__
    if name == "AuthenticationError":
        return "Comdirect rejected or did not complete the authentication flow."
    if name == "RemoteApiError":
        operation = {
            "oauth_password": "initial OAuth authentication",
            "get_sessions": "session status",
            "validate_session": "PhotoTAN challenge creation",
            "activate_session": "PhotoTAN activation",
            "oauth_secondary": "secondary OAuth authentication",
            "poll_session_challenge": "PhotoTAN status",
            "get_account_balances": "account-balance retrieval",
            "get_depots": "depot retrieval",
            "get_positions": "position retrieval",
            "get_instrument": "instrument retrieval",
        }.get(err.operation or "", "API request")
        result = "transport failure" if err.status == 0 else f"HTTP {err.status}"
        return f"Comdirect {operation} failed with {result}."
    if name == "ProtocolError":
        return "Comdirect returned an unexpected authentication or portfolio response."
    if name == "ConfigurationError":
        return "One of the supplied setup values is invalid."
    return "Setup failed. Review the App log and retry."


class IngressHttpServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        controller: AppController,
        *,
        allowed_sources: frozenset[str] = frozenset({"172.30.32.2"}),
        require_user_header: bool = True,
    ) -> None:
        self.controller = controller
        self.allowed_sources = allowed_sources
        self.require_user_header = require_user_header
        super().__init__(address, IngressRequestHandler)


class IngressRequestHandler(BaseHTTPRequestHandler):
    """Small admin-only setup UI reachable exclusively through HA Ingress."""

    protocol_version = "HTTP/1.1"
    server_version = "PortfolioArchitectGatewayApp"
    sys_version = ""

    @property
    def ingress_server(self) -> IngressHttpServer:
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
            self._json(self.ingress_server.controller.status_document())
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
        if path not in {
            "/bootstrap",
            "/refresh",
            "/discover-accounts",
            "/select-account",
            "/clear-account",
            "/set-cash-policy",
        }:
            self._empty(HTTPStatus.NOT_FOUND)
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type != "application/x-www-form-urlencoded":
            self._empty(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return
        try:
            body = self._read_form_body()
        except _RequestBodyTooLarge:
            self._empty(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        except _MalformedRequestBody:
            self._empty(HTTPStatus.BAD_REQUEST)
            return
        if body is None:
            self._empty(HTTPStatus.LENGTH_REQUIRED)
            return
        try:
            values = parse_qs(
                body.decode("utf-8"),
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=8 if path == "/bootstrap" else (4 if path == "/set-cash-policy" else 3),
            )
            csrf = _single(values, "csrf")
            if not secrets.compare_digest(
                csrf, self.ingress_server.controller.csrf_token
            ):
                self._empty(HTTPStatus.FORBIDDEN)
                return
            retry_after = None
            if path == "/refresh":
                if set(values) != {"csrf"}:
                    raise ValueError("Unexpected manual refresh form field")
                accepted, retry_after = self.ingress_server.controller.start_manual_refresh()
            elif path == "/bootstrap":
                accepted = self.ingress_server.controller.start_bootstrap(
                    client_id=_single(values, "client_id"),
                    client_secret=_single(values, "client_secret"),
                    username=_single(values, "username"),
                    password=_single(values, "password"),
                )
            elif path == "/discover-accounts":
                if set(values) != {"csrf"}:
                    raise ValueError("Unexpected account-discovery form field")
                self.ingress_server.controller.discover_investment_accounts()
                accepted = True
            elif path == "/select-account":
                if set(values) != {"csrf", "selection"}:
                    raise ValueError("Unexpected account-selection form field")
                self.ingress_server.controller.select_investment_account(
                    _single(values, "selection")
                )
                accepted = True
            elif path == "/set-cash-policy":
                fields = set(values)
                if fields not in (
                    {"csrf", "mode"},
                    {"csrf", "mode", "cap_eur"},
                    {"csrf", "mode", "retain_eur"},
                ):
                    raise ValueError("Unexpected cash-policy form field")
                self.ingress_server.controller.set_investment_cash_policy(
                    mode=_single(values, "mode"),
                    cap_eur=_single(values, "cap_eur") if "cap_eur" in values else "",
                    retain_eur=(
                        _single(values, "retain_eur") if "retain_eur" in values else ""
                    ),
                )
                accepted = True
            else:
                if set(values) != {"csrf"}:
                    raise ValueError("Unexpected account-clear form field")
                self.ingress_server.controller.clear_investment_account()
                accepted = True
        except (UnicodeError, ValueError):
            self._empty(HTTPStatus.BAD_REQUEST)
            return
        finally:
            _wipe(body)
        if not accepted:
            if path == "/refresh" and retry_after and retry_after > 1:
                self._empty(HTTPStatus.TOO_MANY_REQUESTS, retry_after=retry_after)
            else:
                self._empty(HTTPStatus.CONFLICT)
            return
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "./")
        self._security_headers("text/plain; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()


    def _read_form_body(self) -> bytearray | None:
        """Read one bounded form body from a direct or streamed Ingress request."""
        length_text = self.headers.get("Content-Length")
        transfer_encoding = self.headers.get("Transfer-Encoding")
        if length_text is not None and transfer_encoding is not None:
            raise _MalformedRequestBody
        if length_text is not None:
            if not length_text.isdecimal():
                raise _MalformedRequestBody
            length = int(length_text)
            if length < 1:
                raise _MalformedRequestBody
            if length > MAX_FORM_BYTES:
                raise _RequestBodyTooLarge
            body = bytearray(self.rfile.read(length))
            if len(body) != length:
                _wipe(body)
                raise _MalformedRequestBody
            return body
        if transfer_encoding is None:
            return None
        codings = [part.strip().lower() for part in transfer_encoding.split(",")]
        if codings != ["chunked"]:
            raise _MalformedRequestBody
        return _read_chunked_body(self.rfile)

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

    def _authorised_ingress(self) -> bool:
        total = sum(len(key) + len(value) for key, value in self.headers.items())
        if total > MAX_HEADER_BYTES:
            return False
        if self.client_address[0] not in self.ingress_server.allowed_sources:
            return False
        if self.ingress_server.require_user_header and not self.headers.get(
            "X-Remote-User-Id"
        ):
            return False
        return True

    def _render_page(self) -> bytes:
        controller = self.ingress_server.controller
        document = controller.status_document()
        gateway = document["gateway"]
        bootstrap = document["bootstrap"]
        account = document["investment_account"]
        status_class = (
            "ok" if gateway["status"] == "ok" else "warn"
        )
        token = escape(controller.api_token)
        csrf = escape(controller.csrf_token)
        endpoint = escape(controller.endpoint_url)
        message = escape(str(bootstrap["message"]))
        state = escape(str(bootstrap["state"]))
        snapshot_integrity = (
            "verified" if gateway.get("snapshot_sha256") else "unavailable"
        )
        snapshot_count = gateway.get("snapshot_position_count")
        snapshot_fingerprint = (
            f"{gateway['snapshot_sha256'][:12]}…"
            if gateway.get("snapshot_sha256")
            else "unavailable"
        )
        operating_mode = escape(str(gateway.get("operating_mode", "unknown")))
        snapshot_age = gateway.get("snapshot_age_seconds")
        snapshot_age_text = (
            f"{snapshot_age} seconds" if snapshot_age is not None else "unavailable"
        )
        refresh_failures = gateway.get("consecutive_refresh_failures")
        refresh_in_progress = bool(gateway.get("refresh_in_progress"))
        refresh_state = "running" if refresh_in_progress else "idle"
        refresh_duration = gateway.get("last_refresh_duration_ms")
        refresh_duration_text = (
            f"{refresh_duration / 1000:.3f} seconds"
            if refresh_duration is not None
            else "unavailable"
        )
        refresh_trigger = gateway.get("last_refresh_trigger") or "unavailable"
        next_refresh = gateway.get("next_refresh_due_at") or "unavailable"
        failure_class = gateway.get("last_refresh_failure_class") or "none"
        recommended_action = gateway.get("recommended_action") or "none"
        last_failure = gateway.get("last_refresh_failure_at") or "unavailable"
        retry_after = gateway.get("retry_after_seconds")
        retry_after_text = (
            f"{retry_after} seconds" if retry_after is not None else "unavailable"
        )
        account_state = escape(str(account["state"]))
        account_message = escape(str(account["message"]))
        selected_label = escape(str(account.get("selected_label") or "None selected"))
        cash_policy = document["investment_cash_policy"]
        cash_policy_mode = str(cash_policy.get("mode") or MODE_ALL_AVAILABLE)
        cash_policy_cap = str(cash_policy.get("cap_eur") or "")
        cash_policy_retain = str(cash_policy.get("retain_eur") or "")
        all_available_selected = " selected" if cash_policy_mode == MODE_ALL_AVAILABLE else ""
        capped_selected = " selected" if cash_policy_mode == MODE_CAPPED else ""
        retain_selected = " selected" if cash_policy_mode == MODE_RETAIN else ""
        candidate_options = "".join(
            "<option value=\"" + escape(str(item["token"]), quote=True) + "\">"
            + escape(str(item["label"]))
            + " · eligible €" + escape(str(item["available_eur"]))
            + " · balance €" + escape(str(item["account_balance_eur"]))
            + "</option>"
            for item in account.get("candidates", [])
        )
        selection_form = (
            f'<form method="post" action="select-account" autocomplete="off">'
            f'<input type="hidden" name="csrf" value="{csrf}">'
            f'<label for="selection">Eligible account</label><select id="selection" name="selection" required>{candidate_options}</select>'
            '<button type="submit">Use as investment account</button></form>'
            if candidate_options
            else ""
        )
        clear_form = (
            f'<form method="post" action="clear-account" autocomplete="off">'
            f'<input type="hidden" name="csrf" value="{csrf}">'
            '<button type="submit">Clear investment account</button></form>'
            if account.get("selected")
            else ""
        )
        html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio Architect Gateway</title>
<style>
:root{{color-scheme:light dark;font-family:system-ui,sans-serif}}body{{margin:0;padding:24px;background:var(--ha-card-background,#111827);color:var(--primary-text-color,#e5e7eb)}}main{{max-width:900px;margin:auto}}h1{{font-size:1.55rem}}section{{border:1px solid #64748b55;border-radius:14px;padding:18px;margin:16px 0;background:#64748b12}}label{{display:block;margin-top:12px;font-weight:650}}input,select{{box-sizing:border-box;width:100%;padding:10px;margin-top:5px;border-radius:8px;border:1px solid #64748b;background:transparent;color:inherit}}button{{margin-top:16px;padding:10px 16px;border:0;border-radius:8px;font-weight:700;cursor:pointer}}code{{display:block;white-space:pre-wrap;word-break:break-all;padding:10px;border-radius:8px;background:#02061755}}.ok{{color:#22c55e}}.warn{{color:#f59e0b}}.small{{font-size:.9rem;opacity:.82}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>Portfolio Architect Gateway</h1>
<section><h2>Runtime status</h2><p>Gateway: <strong id="gateway-status" class="{status_class}">{escape(str(gateway['status']))}</strong></p><p>Operating mode: <strong id="operating-mode" class="{status_class}">{operating_mode}</strong></p><p>Refresh state: <strong id="refresh-state">{escape(refresh_state)}</strong></p><p>Last refresh trigger: <strong id="refresh-trigger">{escape(str(refresh_trigger))}</strong></p><p>Last refresh duration: <strong id="refresh-duration">{escape(refresh_duration_text)}</strong></p><p>Next scheduled refresh: <strong id="next-refresh">{escape(str(next_refresh))}</strong></p><p>Snapshot age: <strong id="snapshot-age">{escape(snapshot_age_text)}</strong></p><p>Consecutive refresh failures: <strong id="refresh-failures">{escape(str(refresh_failures if refresh_failures is not None else 'unavailable'))}</strong></p><p>Last failure class: <strong id="failure-class">{escape(str(failure_class))}</strong></p><p>Last failure at: <strong id="failure-at">{escape(str(last_failure))}</strong></p><p>Recommended action: <strong id="recommended-action">{escape(str(recommended_action))}</strong></p><p>Retry after: <strong id="retry-after">{escape(retry_after_text)}</strong></p><p>Snapshot integrity: <strong id="snapshot-integrity" class="{status_class}">{snapshot_integrity}</strong></p><p>Snapshot positions: <strong id="snapshot-count">{escape(str(snapshot_count if snapshot_count is not None else 'unavailable'))}</strong></p><p>Snapshot fingerprint: <code id="snapshot-fingerprint">{escape(snapshot_fingerprint)}</code></p><p>Bootstrap: <strong id="bootstrap-state">{state}</strong></p><p id="bootstrap-message">{message}</p><p class="small">The CSV fallback remains untouched after switching Portfolio Architect to live REST data.</p></section>
<section><h2>Home Assistant connection</h2><label>Endpoint</label><code>{endpoint}</code><label>Bearer token</label><code>{token}</code><p class="small">Portfolio Architect v1.27 discovers the verified HTTPS endpoint and public CA through Supervisor; the dedicated bearer token remains the separate authentication factor.</p></section>
<section><h2>Live portfolio refresh</h2><form method="post" action="refresh" autocomplete="off">
<input type="hidden" name="csrf" value="{csrf}">
<button type="submit">Refresh portfolio now</button></form>
<p class="small">The action is protected by Home Assistant admin Ingress, never exposes the Gateway token, does not alter the configured schedule, and is rate-limited to one request per minute.</p></section>
<section><h2>Dedicated investment account</h2><p>State: <strong id="investment-account-state">{account_state}</strong></p><p id="investment-account-message">{account_message}</p><p>Selected: <strong id="investment-account-selected">{selected_label}</strong></p>
<form method="post" action="discover-accounts" autocomplete="off"><input type="hidden" name="csrf" value="{csrf}"><button type="submit">Discover eligible EUR accounts</button></form>
{selection_form}{clear_form}
<p class="small">Only a masked account label, raw EUR balance, eligible non-borrowed cash and timestamp are shown in this admin-only page. The account identifier stays in App-private storage and is never sent to Home Assistant.</p></section>
<section><h2>Investment cash authorization</h2>
<form method="post" action="set-cash-policy" autocomplete="off">
<input type="hidden" name="csrf" value="{csrf}">
<label for="cash-policy-mode">Authorization policy</label><select id="cash-policy-mode" name="mode" required>
<option value="all_available"{all_available_selected}>All eligible cash</option>
<option value="capped"{capped_selected}>Cap authorized cash</option>
<option value="retain"{retain_selected}>Keep cash reserve</option></select>
<label for="cash-policy-cap">Authorization cap in EUR</label><input id="cash-policy-cap" name="cap_eur" inputmode="decimal" maxlength="16" value="{escape(cash_policy_cap, quote=True)}">
<label for="cash-policy-retain">Cash reserve to keep unallocated in EUR</label><input id="cash-policy-retain" name="retain_eur" inputmode="decimal" maxlength="16" value="{escape(cash_policy_retain, quote=True)}">
<button type="submit">Save authorization policy</button></form>
<p class="small">The Gateway first excludes unavailable, pending or credit-funded cash. All eligible cash authorizes the full eligible amount; Cap authorized cash limits the maximum allocation; Keep cash reserve authorizes only the amount above the retained EUR reserve. If eligible cash is below the retained reserve, authorized cash is zero.</p></section>
<section><h2>Comdirect bootstrap / reauthentication</h2><form method="post" action="bootstrap" autocomplete="off">
<input type="hidden" name="csrf" value="{csrf}">
<div class="grid"><div><label for="client_id">API client ID</label><input id="client_id" name="client_id" maxlength="512" required></div><div><label for="client_secret">API client secret</label><input id="client_secret" name="client_secret" type="password" maxlength="1024" required></div></div>
<div class="grid"><div><label for="username">Comdirect username</label><input id="username" name="username" maxlength="256" required></div><div><label for="password">Comdirect password</label><input id="password" name="password" type="password" maxlength="512" required></div></div>
<button type="submit">Start PhotoTAN bootstrap</button></form>
<p class="small">Username and password are used by the bootstrap thread only and are not written to App options, files, logs, or diagnostics. The API client ID and secret are retained in the App-private data directory because token renewal requires them.</p></section>
<script>
function syncCashPolicy(){{const mode=document.getElementById('cash-policy-mode');const cap=document.getElementById('cash-policy-cap');const retain=document.getElementById('cash-policy-retain');const capped=mode.value==='capped';const retained=mode.value==='retain';cap.disabled=!capped;cap.required=capped;retain.disabled=!retained;retain.required=retained;if(!capped)cap.value='';if(!retained)retain.value='';}}
function setRuntime(id,text,healthy){{const e=document.getElementById(id);e.textContent=text;e.classList.toggle('ok',healthy===true);e.classList.toggle('warn',healthy===false);}}
async function update(){{try{{const r=await fetch('status',{{cache:'no-store'}});if(!r.ok)return;const d=await r.json();const g=d.gateway;const gatewayOk=g.status==='ok';const live=g.operating_mode==='live';setRuntime('gateway-status',g.status||'unavailable',gatewayOk);setRuntime('operating-mode',g.operating_mode||'unavailable',live);document.getElementById('bootstrap-state').textContent=d.bootstrap.state;document.getElementById('bootstrap-message').textContent=d.bootstrap.message;document.getElementById('investment-account-state').textContent=d.investment_account.state;document.getElementById('investment-account-message').textContent=d.investment_account.message;document.getElementById('investment-account-selected').textContent=d.investment_account.selected_label||'None selected';document.getElementById('refresh-state').textContent=g.refresh_in_progress?'running':'idle';document.getElementById('refresh-trigger').textContent=g.last_refresh_trigger||'unavailable';document.getElementById('refresh-duration').textContent=g.last_refresh_duration_ms===null?'unavailable':(g.last_refresh_duration_ms/1000).toFixed(3)+' seconds';document.getElementById('next-refresh').textContent=g.next_refresh_due_at||'unavailable';document.getElementById('snapshot-age').textContent=g.snapshot_age_seconds===null?'unavailable':g.snapshot_age_seconds+' seconds';document.getElementById('refresh-failures').textContent=g.consecutive_refresh_failures===null?'unavailable':g.consecutive_refresh_failures;document.getElementById('failure-class').textContent=g.last_refresh_failure_class||'none';document.getElementById('failure-at').textContent=g.last_refresh_failure_at||'unavailable';document.getElementById('recommended-action').textContent=g.recommended_action||'none';document.getElementById('retry-after').textContent=g.retry_after_seconds===null?'unavailable':g.retry_after_seconds+' seconds';const verified=!!g.snapshot_sha256;setRuntime('snapshot-integrity',verified?'verified':'unavailable',verified);document.getElementById('snapshot-count').textContent=g.snapshot_position_count===null?'unavailable':g.snapshot_position_count;document.getElementById('snapshot-fingerprint').textContent=g.snapshot_sha256?g.snapshot_sha256.slice(0,12)+'…':'unavailable';}}catch(e){{}}}}const cashPolicyMode=document.getElementById('cash-policy-mode');cashPolicyMode.addEventListener('change',syncCashPolicy);syncCashPolicy();update();setInterval(update,2000);
</script></main></body></html>"""
        return html.encode("utf-8")

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

    def _empty(
        self, status: HTTPStatus, *, retry_after: int | None = None
    ) -> None:
        self.send_response(status)
        if retry_after is not None:
            self.send_header("Retry-After", str(retry_after))
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
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "connect-src 'self'; form-action 'self'; frame-ancestors 'self'; base-uri 'none'",
        )

    def log_message(self, format: str, *args: Any) -> None:
        _LOGGER.info("Ingress request completed")



class _MalformedRequestBody(Exception):
    """Raised when an Ingress request body framing is invalid."""


class _RequestBodyTooLarge(Exception):
    """Raised when a request body exceeds the bootstrap form limit."""


def _wipe(body: bytearray) -> None:
    for index in range(len(body)):
        body[index] = 0


def _read_chunked_body(stream: Any) -> bytearray:
    """Decode a strictly bounded HTTP/1.1 chunked request body."""
    body = bytearray()
    try:
        while True:
            line = stream.readline(MAX_CHUNK_LINE_BYTES + 1)
            if (
                not line
                or len(line) > MAX_CHUNK_LINE_BYTES
                or not line.endswith(b"\r\n")
            ):
                raise _MalformedRequestBody
            size_text = line[:-2].split(b";", 1)[0].strip()
            if (
                not size_text
                or len(size_text) > 16
                or any(char not in b"0123456789abcdefABCDEF" for char in size_text)
            ):
                raise _MalformedRequestBody
            size = int(size_text, 16)
            if size == 0:
                trailer_bytes = 0
                while True:
                    trailer = stream.readline(MAX_CHUNK_LINE_BYTES + 1)
                    if (
                        not trailer
                        or len(trailer) > MAX_CHUNK_LINE_BYTES
                        or not trailer.endswith(b"\r\n")
                    ):
                        raise _MalformedRequestBody
                    trailer_bytes += len(trailer)
                    if trailer_bytes > MAX_HEADER_BYTES:
                        raise _MalformedRequestBody
                    if trailer == b"\r\n":
                        break
                if not body:
                    raise _MalformedRequestBody
                return body
            if size > MAX_FORM_BYTES - len(body):
                raise _RequestBodyTooLarge
            chunk = stream.read(size)
            if len(chunk) != size or stream.read(2) != b"\r\n":
                raise _MalformedRequestBody
            body.extend(chunk)
    except Exception:
        _wipe(body)
        raise

def _single(values: dict[str, list[str]], key: str) -> str:
    value = values.get(key)
    if value is None or len(value) != 1:
        raise ValueError(f"Missing or repeated field: {key}")
    return value[0]


def serve_app(
    *,
    options_path: Path = OPTIONS_FILE,
    options: AppOptions | None = None,
    data_directory: Path = APP_DATA_DIRECTORY,
    ingress_address: tuple[str, int] = (INGRESS_BIND, INGRESS_PORT),
    allowed_ingress_sources: frozenset[str] = frozenset({"172.30.32.2"}),
    require_user_header: bool = True,
    ready_callback: Callable[[AppController], None] | None = None,
    tls_cert_file: Path | None = None,
    tls_key_file: Path | None = None,
    gateway_endpoint_url: str = LOCAL_ENDPOINT,
) -> None:
    """Run the private REST API, refresh loop, and HA Ingress setup UI.

    ``options`` may be preloaded by the root entrypoint before dropping
    privileges because Supervisor's ``/data/options.json`` is not guaranteed
    to be readable by the unprivileged service UID. Tests and standalone use
    may continue to supply ``options_path`` instead.
    """
    data_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if options is None:
        options = AppOptions.load(options_path)
    config = build_app_config(
        options,
        data_directory,
        tls_cert_file=tls_cert_file,
        tls_key_file=tls_key_file,
    )
    api_token = ensure_api_token(config.server.api_token_file)
    client = ComdirectClient(config.comdirect)
    state = GatewayState(config.server, client)
    controller = AppController(
        config, client, state, api_token, endpoint_url=gateway_endpoint_url
    )

    stop_event = threading.Event()
    gateway_server = create_server(config.server, state)
    ingress_server = IngressHttpServer(
        ingress_address,
        controller,
        allowed_sources=allowed_ingress_sources,
        require_user_header=require_user_header,
    )
    refresh_thread = threading.Thread(
        target=run_refresh_loop,
        args=(state, client.poll_interval_seconds, stop_event),
        name="portfolio-refresh",
        daemon=True,
    )
    session_maintenance_thread = threading.Thread(
        target=client.run_session_maintenance_loop,
        args=(stop_event,),
        name="comdirect-session-maintenance",
        daemon=True,
    )
    gateway_thread = threading.Thread(
        target=gateway_server.serve_forever,
        kwargs={"poll_interval": 0.5},
        name="portfolio-api",
        daemon=True,
    )
    refresh_thread.start()
    session_maintenance_thread.start()
    gateway_thread.start()
    _LOGGER.info("Private gateway API listening on internal port %d", GATEWAY_PORT)
    _LOGGER.info("Home Assistant Ingress setup UI listening on port %d", ingress_address[1])
    if ready_callback:
        ready_callback(controller)
    try:
        ingress_server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _LOGGER.info("Gateway App shutdown requested")
    finally:
        stop_event.set()
        ingress_server.shutdown()
        ingress_server.server_close()
        gateway_server.shutdown()
        gateway_server.server_close()
        gateway_thread.join(timeout=5)
        refresh_thread.join(timeout=5)
        session_maintenance_thread.join(timeout=5)
