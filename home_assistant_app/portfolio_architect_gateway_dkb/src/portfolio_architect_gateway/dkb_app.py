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
import time
from typing import Any, Final
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from . import __version__
from .acquisition_presentation import ACQUISITION_AUTHORITY_CSS, render_acquisition_authority
from .dkb_authenticated import AuthObservation, AuthSession, begin_authenticated_observation, continue_authenticated_observation
from .dkb_holdings_research import HoldingsObservation, HoldingsSession, begin_holdings_observation, continue_holdings_observation
from .dkb_holdings_review import HoldingsReview, ReviewRow, build_review, render_review
from .dkb_cash_research import (BookedBalance, CashObservation, CashSession,
                                AccountDiscoverySession, begin_account_discovery, continue_account_discovery,
                                begin_cash_observation, continue_cash_observation,
                                save_shadow as save_cash_shadow, shadow_summary as cash_shadow_summary)
from . import dkb_system_id
from . import dkb_account_selection
from .dkb_cash_policy import MODE_ALL_AVAILABLE, MODE_CAPPED, MODE_RETAIN, parse_policy_input
from .dkb_shadow import load_shadow as load_holdings_shadow, project_shadow, save_shadow, shadow_summary
from .dkb_cash_csv import DkbCashCsvImportError, MAX_CASH_CSV_BYTES, parse_dkb_cash_csv
from .dkb_csv import (
    DkbCsvImportError,
    DkbCsvProvider,
    MAX_CSV_BATCH_BYTES,
    MAX_CSV_FILE_BYTES,
    MAX_CSV_FILES,
    parse_dkb_csv_batch,
)
from .dkb_fints_authority import (
    DkbAcquisitionProvider, EVIDENCE_FILE_NAME, MODE_CSV, MODE_FINTS, stage_evidence,
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
from .errors import ConfigurationError, GatewayError, ProtocolError, RemoteApiError
from .models import PortfolioSnapshot
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
AUTH_STATE_FILE_NAME: Final = "dkb-fints-auth-observation.json"
_PARAMETER_SEGMENT_RE: Final = re.compile(r"^HI[A-Z0-9]{3}S$")
BERLIN_TIMEZONE: Final = ZoneInfo("Europe/Berlin")


def _probe_timestamp_display(value: str) -> tuple[str, str]:
    """Return deterministic Europe/Berlin presentation plus authoritative UTC."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as err:
        raise RuntimeError("Stored FinTS probe dispatch timestamp is invalid") from err
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError("Stored FinTS probe dispatch timestamp is invalid")
    utc_value = parsed.astimezone(timezone.utc)
    berlin_value = utc_value.astimezone(BERLIN_TIMEZONE)
    berlin_display = (
        f"{berlin_value.isoformat(timespec='seconds')} "
        f"({berlin_value.tzname() or 'Europe/Berlin'})"
    )
    return berlin_display, utc_value.isoformat(timespec="seconds")


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
        self.auth_state_file = data_directory / AUTH_STATE_FILE_NAME
        self.holdings_state_file = data_directory / "dkb-fints-holdings-observation.json"
        self.shadow_file = data_directory / "dkb-fints-holdings-shadow.json"
        self.cash_research_file = data_directory / "dkb-fints-cash-observation.json"
        self.cash_shadow_file = data_directory / "dkb-fints-cash-shadow.json"
        self.authority_evidence_file = data_directory / EVIDENCE_FILE_NAME
        self.acquisition_provider: DkbAcquisitionProvider | None = None
        self.cash_system_id_file = data_directory / dkb_system_id.FILE_NAME
        self.cash_fingerprint_key_file = data_directory / dkb_system_id.KEY_FILE_NAME
        self.selected_account_file = data_directory / dkb_account_selection.SELECTION_FILE_NAME
        self.account_binding_key_file = data_directory / dkb_account_selection.KEY_FILE_NAME
        self.csrf_token = secrets.token_urlsafe(32)
        self._lock = threading.RLock()
        self._probe_in_progress = False
        self._auth_session: AuthSession | None = None
        self._auth_deadline = 0.0
        self._holdings_session: HoldingsSession | None = None
        self._holdings_deadline = 0.0
        self._holdings_review: HoldingsReview | None = None
        self._review_deadline = 0.0
        self._cash_session: CashSession | None = None
        self._cash_deadline = 0.0
        self._cash_review: tuple[Any, BookedBalance] | None = None
        self._cash_review_deadline = 0.0
        # Only trial booleans and a pending identity are held in RAM. The bounded
        # bank ID is App-private, excluded from backups and never rendered.
        self._cash_system_trial: tuple[bool, bool] | None = None
        self._cash_diagnostic: dict[str, str] | None = None
        self._cash_pending_identity: str | None = None
        self._account_discovery: AccountDiscoverySession | None = None
        self._account_discovery_deadline = 0.0
        self._account_options: dict[str, dict[str, str]] = {}
        self._account_options_deadline = 0.0
        self._account_discovery_user: str | None = None
        self._account_discovery_state = "not_started"
        self._portfolio_stage = "idle"
        self._portfolio_holdings_observed_at: str | None = None
        self._portfolio_credentials: tuple[str, str] | None = None
        self._portfolio_deadline = 0.0
        self._portfolio_generation = 0
        self._portfolio_timer: threading.Timer | None = None

    def _drop_portfolio_credentials(self) -> None:
        with self._lock:
            self._portfolio_credentials = None
            self._portfolio_generation += 1
            timer = self._portfolio_timer
            self._portfolio_timer = None
        if timer is not None:
            timer.cancel()

    def _expire_portfolio_credentials(self, generation: int) -> None:
        with self._lock:
            if generation != self._portfolio_generation:
                return
            self._portfolio_credentials = None
            self._portfolio_timer = None
            if self._portfolio_stage in {"starting", "holdings_pending"}:
                self._portfolio_stage = "expired"
                session = self._holdings_session
                self._holdings_session = None
            else:
                session = None
        if session is not None:
            session.close()

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
        if self.acquisition_provider is not None and self.acquisition_provider.acquisition_mode == MODE_FINTS:
            raise ValueError("Switch DKB authority to CSV before changing FinTS registration")
        product_id = normalise_product_id(value)
        with self._lock:
            if self._auth_session is not None:
                self._auth_session.close()
                self._auth_session = None
            if self._holdings_session is not None:
                self._holdings_session.close()
                self._holdings_session = None
            if self._cash_session is not None:
                self._cash_session.close()
                self._cash_session = None
            if self._account_discovery is not None:
                self._account_discovery.close()
                self._account_discovery = None
            self._account_options.clear()
            self._account_discovery_user = None
            self._account_discovery_state = "not_started"
            self._portfolio_stage = "idle"
            self._drop_portfolio_credentials()
            self.selected_account_file.unlink(missing_ok=True)
            self.account_binding_key_file.unlink(missing_ok=True)
            self._cash_review = None
            self._cash_system_trial = None
            self._cash_diagnostic = None
            self._cash_pending_identity = None
            self.cash_system_id_file.unlink(missing_ok=True)
            self.cash_fingerprint_key_file.unlink(missing_ok=True)
            self.cash_research_file.unlink(missing_ok=True)
            self.cash_shadow_file.unlink(missing_ok=True)
            self.authority_evidence_file.unlink(missing_ok=True)
            self._holdings_review = None
            self.holdings_state_file.unlink(missing_ok=True)
            self.shadow_file.unlink(missing_ok=True)
        # Capability evidence belongs to the registration identity that produced it.
        # Remove any previous result before changing that identity so stale BPD data
        # can never be presented as evidence for a newly configured product.
        self.probe_state_file.unlink(missing_ok=True)
        self.probe_sent_at_file.unlink(missing_ok=True)
        self.auth_state_file.unlink(missing_ok=True)
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
            if self._probe_in_progress or self._auth_session is not None or self._holdings_session is not None or self._cash_session is not None:
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

    def auth_observation(self) -> AuthObservation | None:
        with self._lock:
            if self._auth_session is not None:
                if time.monotonic() < self._auth_deadline:
                    return AuthObservation(self._auth_session.started_at, "approval_pending", False,
                                           None, "unknown", "unknown")
                self._auth_session.close()
                self._auth_session = None
                expired = AuthObservation(datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                          "approval_expired", False, None, "unknown", "unknown")
                save_json_state(self.auth_state_file, expired.as_dict())
        raw = load_json_state(self.auth_state_file)
        if raw is None:
            return None
        try:
            if raw.get("schema_version") != 1 or set(raw) != {
                "schema_version", "observed_at", "outcome", "upd_received",
                "upd_version", "securities_capability", "auth_method", "return_codes",
            }:
                raise ValueError("invalid observation")
            if raw["outcome"] not in {"authenticated", "authentication_failed", "sca_required", "approval_expired"}:
                raise ValueError("invalid outcome")
            if raw["securities_capability"] not in {"yes", "no", "unknown"}:
                raise ValueError("invalid capability")
            if not isinstance(raw["upd_received"], bool) or raw["upd_version"] is not None and (
                type(raw["upd_version"]) is not int or not 0 <= raw["upd_version"] <= 999
            ):
                raise ValueError("invalid UPD")
            if not isinstance(raw["auth_method"], str) or not re.fullmatch(r"unknown|[0-9]{1,4}", raw["auth_method"]):
                raise ValueError("invalid auth method")
            codes = raw["return_codes"]
            if not isinstance(codes, list) or len(codes) > 32 or any(
                not isinstance(code, str) or not re.fullmatch(r"[0-9]{4}", code) for code in codes
            ) or not isinstance(raw["observed_at"], str) or len(raw["observed_at"]) > 40:
                raise ValueError("invalid evidence")
            _probe_timestamp_display(raw["observed_at"])
            return AuthObservation(raw["observed_at"], raw["outcome"], raw["upd_received"],
                                   raw["upd_version"], raw["securities_capability"],
                                   raw["auth_method"], tuple(codes))
        except (KeyError, TypeError, ValueError) as err:
            raise RuntimeError("Stored DKB authenticated research state is invalid") from err

    def run_auth_observation(self, user_id: str, pin: str) -> AuthObservation:
        product_id = self.product_id()
        if product_id is None:
            raise ValueError("FinTS registration required")
        with self._lock:
            if self._probe_in_progress or self._account_discovery is not None or self._auth_session is not None or self._holdings_session is not None or self._cash_session is not None:
                raise ValueError("FinTS research is already running")
            self._probe_in_progress = True
        try:
            # Clear stale user evidence before a new identity or attempt.
            self.auth_state_file.unlink(missing_ok=True)
            result, session = begin_authenticated_observation(product_id, user_id, pin)
            if session is not None:
                with self._lock:
                    self._auth_session = session
                    self._auth_deadline = time.monotonic() + 300
            else:
                save_json_state(self.auth_state_file, result.as_dict())
            _LOGGER.info("DKB authenticated FinTS research outcome=%s UPD=%s capability=%s",
                         result.outcome, result.upd_received, result.securities_capability)
            return result
        finally:
            with self._lock:
                self._probe_in_progress = False

    def continue_auth_observation(self, tan: str = "") -> AuthObservation:
        with self._lock:
            session = self._auth_session
            if session is None or time.monotonic() >= self._auth_deadline:
                self.auth_observation()
                raise ValueError("No pending bank approval")
            if self._probe_in_progress:
                raise ValueError("FinTS research is already running")
            self._probe_in_progress = True
        try:
            result, pending = continue_authenticated_observation(session, tan)
            with self._lock:
                self._auth_session = pending
            if pending is None:
                save_json_state(self.auth_state_file, result.as_dict())
            return result
        finally:
            with self._lock:
                self._probe_in_progress = False

    def pending_auth_is_decoupled(self) -> bool:
        with self._lock:
            return bool(self._auth_session and self._auth_session.decoupled)

    def holdings_observation(self) -> HoldingsObservation | None:
        with self._lock:
            if self._holdings_session is not None:
                if time.monotonic() < self._holdings_deadline:
                    return HoldingsObservation(self._holdings_session.started_at, "approval_pending", 0, None)
                self._holdings_session.close()
                self._holdings_session = None
                expired = HoldingsObservation(datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                              "approval_expired", 0, None)
                save_json_state(self.holdings_state_file, expired.as_dict())
        raw = load_json_state(self.holdings_state_file)
        if raw is None:
            return None
        try:
            schema = raw.get("schema_version")
            common = {"schema_version", "observed_at", "outcome", "eligible_accounts", "holding_count", "return_codes"}
            if schema not in {1, 2} or set(raw) != (common if schema == 1 else common | {
                "failure_stage", "failure_kind"
            }) or raw["outcome"] not in {
                "retrieved", "no_eligible_account", "multiple_eligible_accounts", "account_metadata_incomplete",
                "invalid_response", "request_failed", "approval_expired"
            } or (raw["eligible_accounts"] is not None and (
                type(raw["eligible_accounts"]) is not int or not 0 <= raw["eligible_accounts"] <= 256
            )) or (schema == 1 and raw["eligible_accounts"] is None):
                raise ValueError("invalid holdings observation")
            stage = raw.get("failure_stage")
            kind = raw.get("failure_kind")
            stages = {"client_creation", "tan_mechanisms", "login_dialog", "login_approval",
                      "account_discovery", "account_metadata", "holdings_request", "holdings_approval",
                      "response_summary"}
            kinds = {"timeout", "transport", "attribute_error", "type_error", "key_error",
                     "value_error", "unsupported", "unclassified"}
            if schema == 2 and ((raw["outcome"] == "request_failed") != (stage in stages and kind in kinds) or
                                (stage is not None and stage not in stages) or (kind is not None and kind not in kinds)):
                raise ValueError("invalid holdings diagnostic")
            count = raw["holding_count"]
            if count is not None and (type(count) is not int or not 0 <= count <= 256):
                raise ValueError("invalid holdings count")
            if (raw["outcome"] == "retrieved") != (count is not None):
                raise ValueError("invalid holdings outcome")
            codes = raw["return_codes"]
            if not isinstance(codes, list) or len(codes) > 32 or any(
                not isinstance(code, str) or not re.fullmatch(r"[0-9]{4}", code) for code in codes
            ) or not isinstance(raw["observed_at"], str) or len(raw["observed_at"]) > 40:
                raise ValueError("invalid holdings evidence")
            _probe_timestamp_display(raw["observed_at"])
            eligible = None if schema == 1 and raw["outcome"] in {"request_failed", "approval_expired"} else raw["eligible_accounts"]
            return HoldingsObservation(raw["observed_at"], raw["outcome"], eligible,
                                       count, tuple(codes), stage, kind)
        except (KeyError, TypeError, ValueError) as err:
            raise RuntimeError("Stored DKB holdings research state is invalid") from err

    def holdings_review(self) -> HoldingsReview | None:
        with self._lock:
            if self._holdings_review is not None and time.monotonic() >= self._review_deadline:
                self._holdings_review = None
                self._review_deadline = 0.0
            return self._holdings_review

    def holdings_review_seconds_remaining(self) -> int:
        with self._lock:
            if self._holdings_review is None:
                return 0
            remaining = max(0, int(self._review_deadline - time.monotonic() + 0.999))
            if not remaining:
                self._holdings_review = None
                self._review_deadline = 0.0
            return remaining

    def clear_holdings_review(self) -> None:
        with self._lock:
            self._holdings_review = None
            self._review_deadline = 0.0

    def _capture_review(self, rows: list[tuple[ReviewRow, ...]],
                        snapshot: PortfolioSnapshot | None, result: HoldingsObservation) -> None:
        if result.outcome == "retrieved" and rows:
            with self._lock:
                self._holdings_review = build_review(snapshot, result.observed_at, rows[0])
                self._review_deadline = time.monotonic() + 300
            projected = project_shadow(rows[0], result.observed_at)
            if projected is not None:
                save_shadow(self.shadow_file, projected)

    def run_holdings_observation(self, user_id: str, pin: str,
                                 csv_snapshot: PortfolioSnapshot | None = None) -> HoldingsObservation:
        product_id = self.product_id()
        if product_id is None:
            raise ValueError("FinTS registration required")
        with self._lock:
            if self._probe_in_progress or self._account_discovery is not None or self._auth_session is not None or self._holdings_session is not None or self._cash_session is not None:
                raise ValueError("FinTS research is already running")
            self._probe_in_progress = True
        try:
            self.holdings_state_file.unlink(missing_ok=True)
            self.clear_holdings_review()
            rows: list[tuple[ReviewRow, ...]] = []
            result, session = begin_holdings_observation(product_id, user_id, pin, rows.append)
            self._capture_review(rows, csv_snapshot, result)
            if session is not None:
                with self._lock:
                    self._holdings_session = session
                    self._holdings_deadline = time.monotonic() + 300
            else:
                save_json_state(self.holdings_state_file, result.as_dict())
            _LOGGER.info("DKB read-only holdings research outcome=%s", result.outcome)
            return result
        finally:
            with self._lock:
                self._probe_in_progress = False

    def continue_holdings_observation(self, tan: str = "",
                                      csv_snapshot: PortfolioSnapshot | None = None) -> HoldingsObservation:
        with self._lock:
            session = self._holdings_session
            if session is None or time.monotonic() >= self._holdings_deadline:
                self.holdings_observation()
                raise ValueError("No pending bank approval")
            if self._probe_in_progress:
                raise ValueError("FinTS research is already running")
            self._probe_in_progress = True
        try:
            rows: list[tuple[ReviewRow, ...]] = []
            result, pending = continue_holdings_observation(session, tan, rows.append)
            self._capture_review(rows, csv_snapshot, result)
            with self._lock:
                self._holdings_session = pending
            if pending is None:
                save_json_state(self.holdings_state_file, result.as_dict())
            return result
        finally:
            with self._lock:
                self._probe_in_progress = False

    def pending_holdings_is_decoupled(self) -> bool:
        with self._lock:
            return bool(self._holdings_session and self._holdings_session.decoupled)

    def cash_observation(self) -> CashObservation | None:
        with self._lock:
            if self._cash_session is not None:
                if time.monotonic() < self._cash_deadline:
                    return CashObservation(self._cash_session.started_at, "approval_pending", None)
                self._cash_session.close()
                self._cash_session = None
                expired = CashObservation(datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                          "approval_expired", None)
                save_json_state(self.cash_research_file, expired.as_dict())
        raw = load_json_state(self.cash_research_file)
        if raw is None:
            return None
        try:
            if set(raw) != {"schema_version", "observed_at", "outcome", "eligible_accounts",
                            "return_codes", "failure_stage", "failure_kind"} or raw["schema_version"] != 1:
                raise ValueError("invalid cash observation")
            outcomes = {"retrieved", "invalid_balance", "invalid_account_list", "account_not_found",
                        "ambiguous_account", "account_metadata_incomplete", "request_failed", "approval_expired"}
            stages = {"client_creation", "tan_mechanisms", "login_dialog", "login_approval",
                      "account_discovery", "account_metadata", "balance_request", "balance_approval",
                      "response_summary"}
            kinds = {"timeout", "transport", "attribute_error", "type_error", "key_error",
                     "value_error", "unsupported", "unclassified"}
            if raw["outcome"] not in outcomes or (raw["outcome"] == "request_failed") != (
                raw["failure_stage"] in stages and raw["failure_kind"] in kinds):
                raise ValueError("invalid cash result")
            if raw["outcome"] != "request_failed" and (
                raw["failure_stage"] is not None or raw["failure_kind"] is not None):
                raise ValueError("invalid cash failure")
            count = raw["eligible_accounts"]
            if count is not None and (type(count) is not int or not 0 <= count <= 256):
                raise ValueError("invalid cash account count")
            codes = raw["return_codes"]
            if not isinstance(codes, list) or len(codes) > 32 or any(
                not isinstance(code, str) or not re.fullmatch(r"[0-9]{4}", code) for code in codes
            ) or not isinstance(raw["observed_at"], str) or len(raw["observed_at"]) > 40:
                raise ValueError("invalid cash codes or timestamp")
            _probe_timestamp_display(raw["observed_at"])
            return CashObservation(raw["observed_at"], raw["outcome"], count,
                                   tuple(codes), raw["failure_stage"], raw["failure_kind"])
        except (KeyError, TypeError, ValueError) as err:
            raise RuntimeError("Stored DKB cash research state is invalid") from err

    def cash_review(self) -> tuple[Any, BookedBalance] | None:
        with self._lock:
            if self._cash_review is not None and time.monotonic() >= self._cash_review_deadline:
                self._cash_review = None
            return self._cash_review

    def clear_cash_review(self) -> None:
        with self._lock:
            self._cash_review = None
            self._cash_review_deadline = 0.0

    def _capture_cash(self, values: list[BookedBalance], csv_snapshot: Any,
                      result: CashObservation) -> None:
        if result.outcome == "retrieved" and len(values) == 1:
            save_cash_shadow(self.cash_shadow_file, values[0])
            with self._lock:
                self._cash_review = (csv_snapshot, values[0])
                self._cash_review_deadline = time.monotonic() + 300

    def _store_cash_system_id(self, identity: str, values: list[str],
                              result: CashObservation, seeded_at: datetime | None = None) -> None:
        if result.outcome != "retrieved" or len(values) != 1:
            return
        try:
            dkb_system_id.save(self.cash_system_id_file, identity, values[0],
                               seeded_at or datetime.now(timezone.utc))
            fingerprint = dkb_system_id.fingerprint(self.cash_fingerprint_key_file, values[0])
            with self._lock:
                if self._cash_diagnostic is not None:
                    self._cash_diagnostic["save"] = "succeeded"
                    self._cash_diagnostic["fingerprint"] = fingerprint or "unavailable"
        except (OSError, ValueError):
            # The booked balance remains a valid research observation. A failed
            # hint write must never expose its value or the bank identifier.
            _LOGGER.warning("DKB private system ID research state unavailable")
            with self._lock:
                if self._cash_diagnostic is not None:
                    self._cash_diagnostic["save"] = "failed"

    def _record_cash_system_id_capture(self, value: object, ids: list[str]) -> None:
        category = dkb_system_id.capture_category(value)
        if category == "valid":
            # The classifier has proved that this is a bounded printable ID.
            ids.append(value)
        with self._lock:
            if self._cash_diagnostic is not None:
                # A later invalid callback must not erase a valid capture.
                if category == "valid" or self._cash_diagnostic["capture"] != "valid":
                    self._cash_diagnostic["capture"] = (
                        "valid" if category == "valid" else "absent" if category == "absent" else "invalid")
                    self._cash_diagnostic["capture_reason"] = category

    def run_cash_observation(self, user_id: str, pin: str, suffix: str,
                             csv_snapshot: Any = None) -> CashObservation:
        product_id = self.product_id()
        if product_id is None:
            raise ValueError("FinTS registration required")
        with self._lock:
            if self._probe_in_progress or self._account_discovery is not None or self._auth_session is not None or self._holdings_session is not None or self._cash_session is not None:
                raise ValueError("FinTS research is already running")
            self._probe_in_progress = True
        try:
            self.cash_research_file.unlink(missing_ok=True)
            self.clear_cash_review()
            values: list[BookedBalance] = []
            selected = dkb_account_selection.load(self.selected_account_file, self.account_binding_key_file)
            matcher = None
            if selected is not None:
                if suffix != selected.suffix or not dkb_account_selection.user_matches(
                    selected, self.account_binding_key_file, product_id=product_id, user_id=user_id
                ):
                    raise ValueError("Selected DKB investment account does not match this request")
                matcher = lambda account: dkb_account_selection.matches(
                    selected, self.account_binding_key_file, product_id=product_id,
                    user_id=user_id, account=account)
            identity = dkb_system_id.binding(product_id, user_id)
            prior, load_reason = dkb_system_id.inspect(self.cash_system_id_file, identity)
            prior_id = prior.system_id if prior else None
            with self._lock:
                self._cash_system_trial = (prior_id is not None, False)
                self._cash_diagnostic = {"load": load_reason, "capture": "absent",
                                         "capture_reason": "not_observed",
                                         "save": "skipped", "fingerprint": "unavailable"}
                if prior_id is not None:
                    self._cash_diagnostic["fingerprint"] = (
                        dkb_system_id.fingerprint(self.cash_fingerprint_key_file, prior_id)
                        or "unavailable")
            ids: list[str] = []
            def capture_id(value: object) -> None:
                self._record_cash_system_id_capture(value, ids)
            result, session = begin_cash_observation(
                product_id, user_id, pin, suffix, values.append,
                system_id=prior_id, capture_system_id=capture_id, account_matcher=matcher)
            self._capture_cash(values, csv_snapshot, result)
            if session is None:
                self._store_cash_system_id(identity, ids, result, prior.seeded_at if prior else None)
            with self._lock:
                self._cash_system_trial = (prior_id is not None, session is not None)
            if session is not None:
                with self._lock:
                    self._cash_session = session
                    self._cash_deadline = time.monotonic() + 300
                    self._cash_pending_identity = identity
            else:
                self._cash_pending_identity = None
                save_json_state(self.cash_research_file, result.as_dict())
            _LOGGER.info("DKB read-only booked-balance research outcome=%s", result.outcome)
            return result
        finally:
            with self._lock:
                self._probe_in_progress = False

    def continue_cash_observation(self, tan: str = "", csv_snapshot: Any = None) -> CashObservation:
        with self._lock:
            session = self._cash_session
            if session is None or time.monotonic() >= self._cash_deadline:
                self.cash_observation()
                raise ValueError("No pending bank approval")
            if self._probe_in_progress:
                raise ValueError("FinTS research is already running")
            self._probe_in_progress = True
        try:
            values: list[BookedBalance] = []
            ids: list[str] = []
            def capture_id(value: object) -> None:
                if self._cash_pending_identity is not None:
                    self._record_cash_system_id_capture(value, ids)
            result, pending = continue_cash_observation(session, tan, values.append, capture_id)
            self._capture_cash(values, csv_snapshot, result)
            if pending is None and self._cash_pending_identity is not None:
                # Completing an actual bank challenge starts a fresh, fixed
                # research window. Approval-free reads never extend it.
                self._store_cash_system_id(self._cash_pending_identity, ids, result)
            with self._lock:
                self._cash_session = pending
                if pending is None:
                    self._cash_pending_identity = None
            if pending is None:
                save_json_state(self.cash_research_file, result.as_dict())
            return result
        finally:
            with self._lock:
                self._probe_in_progress = False

    def pending_cash_is_decoupled(self) -> bool:
        with self._lock:
            return bool(self._cash_session and self._cash_session.decoupled)

    def cash_system_trial(self) -> tuple[bool, bool] | None:
        """Only bounded, current-process research facts; no system ID is exposed."""
        with self._lock:
            return self._cash_system_trial

    def cash_system_diagnostic(self) -> dict[str, str] | None:
        """Bounded current-process facts for admin Ingress only."""
        with self._lock:
            return self._cash_diagnostic.copy() if self._cash_diagnostic else None

    def selected_account(self) -> dkb_account_selection.SelectedAccount | None:
        return dkb_account_selection.load(self.selected_account_file, self.account_binding_key_file)

    def account_discovery_view(self) -> tuple[str, tuple[tuple[str, str], ...], bool]:
        with self._lock:
            if self._account_discovery is not None and time.monotonic() >= self._account_discovery_deadline:
                self._account_discovery.close()
                self._account_discovery = None
                self._account_discovery_user = None
                self._account_discovery_state = "expired"
            if self._account_options and time.monotonic() >= self._account_options_deadline:
                self._account_options.clear()
                self._account_discovery_user = None
                self._account_discovery_state = "expired"
            options = tuple((token, f"EUR balance account ending {account['iban'][-8:]} · option {index}")
                            for index, (token, account) in enumerate(self._account_options.items(), start=1))
            return self._account_discovery_state, options, bool(self._account_discovery and self._account_discovery.decoupled)

    def _capture_account_candidates(self, values: tuple[dict[str, str], ...]) -> None:
        if not 1 <= len(values) <= 256:
            raise ValueError("No selectable DKB EUR balance accounts")
        with self._lock:
            self._account_options = {secrets.token_urlsafe(18): item for item in values}
            self._account_options_deadline = time.monotonic() + 300
            self._account_discovery_state = "ready"

    def discover_accounts(self, user_id: str, pin: str) -> None:
        product_id = self.product_id()
        if product_id is None:
            raise ValueError("FinTS registration required")
        with self._lock:
            if (self._probe_in_progress or self._account_discovery is not None or
                    self._auth_session is not None or self._holdings_session is not None or self._cash_session is not None):
                raise ValueError("FinTS request already running")
            self._probe_in_progress = True
            self._account_options.clear()
            self._account_discovery_state = "running"
            self._account_discovery_user = user_id
        try:
            identity = dkb_system_id.binding(product_id, user_id)
            prior = dkb_system_id.load(self.cash_system_id_file, identity)
            values, pending = begin_account_discovery(
                product_id, user_id, pin, system_id=prior.system_id if prior else None)
            with self._lock:
                self._account_discovery = pending
                self._account_discovery_deadline = time.monotonic() + 300 if pending else 0.0
                self._account_discovery_state = "approval_pending" if pending else "ready"
            if values is not None:
                self._capture_account_candidates(values)
        except Exception:
            with self._lock:
                self._account_discovery_state = "failed"
                self._account_discovery_user = None
            raise
        finally:
            with self._lock:
                self._probe_in_progress = False

    def continue_account_discovery(self, tan: str = "") -> None:
        with self._lock:
            session = self._account_discovery
            if session is None or time.monotonic() >= self._account_discovery_deadline:
                self.account_discovery_view()
                raise ValueError("No pending DKB approval")
            if self._probe_in_progress:
                raise ValueError("FinTS request already running")
            self._probe_in_progress = True
        try:
            values, pending = continue_account_discovery(session, tan)
            with self._lock:
                self._account_discovery = pending
                self._account_discovery_state = "approval_pending" if pending else "ready"
            if values is not None:
                self._capture_account_candidates(values)
        except Exception:
            with self._lock:
                self._account_discovery = None
                self._account_discovery_user = None
                self._account_discovery_state = "failed"
            raise
        finally:
            with self._lock:
                self._probe_in_progress = False

    def select_account(self, token: str) -> dkb_account_selection.SelectedAccount:
        if self.acquisition_provider is not None and self.acquisition_provider.acquisition_mode == MODE_FINTS:
            raise ValueError("Switch DKB authority to CSV before changing the account")
        with self._lock:
            self.account_discovery_view()
            if self.portfolio_refresh_state() in {"holdings_pending", "cash_pending"}:
                raise ValueError("Complete the pending bank refresh first")
            if self._probe_in_progress or self._auth_session is not None or self._holdings_session is not None or self._cash_session is not None:
                raise ValueError("Complete the pending bank request first")
            account = self._account_options.get(token) if isinstance(token, str) else None
            user_id = self._account_discovery_user
            if account is None or user_id is None:
                raise ValueError("Unknown or expired account selection")
            selected = dkb_account_selection.select(
                self.selected_account_file, self.account_binding_key_file,
                product_id=self.product_id() or "", user_id=user_id, account=account)
            self._account_options.clear()
            self._account_discovery_user = None
            self._account_discovery_state = "selected"
            self.cash_shadow_file.unlink(missing_ok=True)
            self.authority_evidence_file.unlink(missing_ok=True)
            self.cash_research_file.unlink(missing_ok=True)
            self.clear_cash_review()
            return selected

    def clear_selected_account(self) -> None:
        if self.acquisition_provider is not None and self.acquisition_provider.acquisition_mode == MODE_FINTS:
            raise ValueError("Switch DKB authority to CSV before clearing the account")
        with self._lock:
            if self.portfolio_refresh_state() in {"holdings_pending", "cash_pending"}:
                raise ValueError("Complete the pending bank refresh first")
            if self._probe_in_progress or self._auth_session is not None or self._holdings_session is not None or self._cash_session is not None:
                raise ValueError("Complete the pending bank request first")
            self.selected_account_file.unlink(missing_ok=True)
            self.cash_shadow_file.unlink(missing_ok=True)
            self.authority_evidence_file.unlink(missing_ok=True)
            self.cash_research_file.unlink(missing_ok=True)
            self.clear_cash_review()

    def portfolio_refresh_state(self) -> str:
        with self._lock:
            if self._portfolio_stage in {"holdings_pending", "cash_pending"} and time.monotonic() >= self._portfolio_deadline:
                self._drop_portfolio_credentials()
                self._portfolio_stage = "expired"
                self.holdings_observation()
                self.cash_observation()
            return self._portfolio_stage

    def _advance_portfolio_refresh(self, result: HoldingsObservation | CashObservation,
                                   *, holdings: bool, csv_cash: Any = None) -> str:
        if result.outcome == "approval_pending":
            self._portfolio_stage = "holdings_pending" if holdings else "cash_pending"
            return self._portfolio_stage
        if result.outcome != "retrieved":
            self._drop_portfolio_credentials()
            self._portfolio_stage = "failed"
            return self._portfolio_stage
        if holdings:
            shadow = shadow_summary(self.shadow_file)
            if shadow["observed_at"] != result.observed_at:
                self._drop_portfolio_credentials()
                self._portfolio_stage = "incomplete_holdings"
                return self._portfolio_stage
            self._portfolio_holdings_observed_at = result.observed_at
            credentials = self._portfolio_credentials
            self._drop_portfolio_credentials()
            selected = self.selected_account()
            if credentials is None or selected is None:
                self._portfolio_stage = "failed"
                return self._portfolio_stage
            cash = self.run_cash_observation(credentials[0], credentials[1], selected.suffix, csv_cash)
            return self._advance_portfolio_refresh(cash, holdings=False)
        cash_shadow = cash_shadow_summary(self.cash_shadow_file)
        if cash_shadow["observed_at"] != result.observed_at:
            self._portfolio_stage = "incomplete_cash"
            return self._portfolio_stage
        try:
            selected = self.selected_account()
            holdings_raw = load_holdings_shadow(self.shadow_file)
            cash_raw = load_json_state(self.cash_shadow_file)
            if (selected is None or holdings_raw is None or cash_raw is None
                    or holdings_raw["observed_at"] != self._portfolio_holdings_observed_at
                    or cash_raw.get("observed_at") != result.observed_at):
                raise ValueError("Complete DKB FinTS evidence is unavailable")
            stage_evidence(self.authority_evidence_file, selected, holdings_raw, cash_raw)
        except (ValueError, ProtocolError, ConfigurationError, OSError):
            self._portfolio_stage = "incomplete_evidence"
            return self._portfolio_stage
        finally:
            self._portfolio_holdings_observed_at = None
        self._portfolio_stage = "complete"
        return self._portfolio_stage

    def run_portfolio_refresh(self, user_id: str, pin: str,
                              csv_holdings: PortfolioSnapshot | None = None,
                              csv_cash: Any = None) -> str:
        selected = self.selected_account()
        product_id = self.product_id()
        if (selected is None or product_id is None or not dkb_account_selection.user_matches(
            selected, self.account_binding_key_file, product_id=product_id, user_id=user_id
        )):
            raise ValueError("Select a DKB EUR account for this user before refreshing")
        with self._lock:
            if self.portfolio_refresh_state() in {"holdings_pending", "cash_pending"}:
                raise ValueError("Portfolio refresh is already awaiting bank approval")
            if self._account_discovery is not None or self._probe_in_progress:
                raise ValueError("Complete the pending bank request first")
            self._portfolio_stage = "starting"
            self._portfolio_holdings_observed_at = None
            self._portfolio_credentials = (user_id, pin)
            self._portfolio_deadline = time.monotonic() + 300
            self._portfolio_generation += 1
            timer = threading.Timer(300, self._expire_portfolio_credentials,
                                    args=(self._portfolio_generation,))
            timer.daemon = True
            self._portfolio_timer = timer
            timer.start()
        try:
            holdings = self.run_holdings_observation(user_id, pin, csv_holdings)
            return self._advance_portfolio_refresh(holdings, holdings=True, csv_cash=csv_cash)
        except Exception:
            with self._lock:
                self._drop_portfolio_credentials()
                self._portfolio_stage = "failed"
            raise

    def continue_portfolio_refresh(self, tan: str = "",
                                   csv_holdings: PortfolioSnapshot | None = None,
                                   csv_cash: Any = None) -> str:
        stage = self.portfolio_refresh_state()
        try:
            if stage == "holdings_pending":
                holdings = self.continue_holdings_observation(tan, csv_holdings)
                return self._advance_portfolio_refresh(holdings, holdings=True, csv_cash=csv_cash)
            if stage == "cash_pending":
                cash = self.continue_cash_observation(tan, csv_cash)
                return self._advance_portfolio_refresh(cash, holdings=False)
            raise ValueError("No pending DKB portfolio approval")
        except Exception:
            with self._lock:
                self._drop_portfolio_credentials()
                self._portfolio_stage = "failed"
            raise

    def status_document(self, gateway_state: GatewayState) -> dict[str, Any]:
        view = self.probe_view()
        auth = self.auth_observation()
        try:
            selected = self.selected_account()
            account_state = "selected" if selected is not None else "unselected"
            account_label = selected.masked_label if selected is not None else None
        except (ProtocolError, OSError):
            account_state, account_label = "invalid", None
        return {
            "gateway": gateway_state.health_document(version=8),
            "authenticated_research": auth.as_dict() if auth else None,
            "holdings_research": (holdings.as_dict() if (holdings := self.holdings_observation()) else None),
            "holdings_shadow": shadow_summary(self.shadow_file),
            "cash_research": (cash.as_dict() if (cash := self.cash_observation()) else None),
            "cash_shadow": cash_shadow_summary(self.cash_shadow_file),
            "investment_account": {"state": account_state, "masked_label": account_label},
            "manual_portfolio_refresh": self.portfolio_refresh_state(),
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
        provider: DkbAcquisitionProvider,
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
                if (self.app_server.csv_provider.acquisition_mode == MODE_CSV
                        and not self.app_server.gateway_state.refresh(trigger="manual")):
                    self.app_server.csv_provider.replace_snapshot(previous)
                    raise DkbCsvImportError("Imported DKB CSV batch could not be activated")
                self.app_server.controller.clear_holdings_review()
                self.app_server.last_import_notice = (
                    "accepted",
                    f"DKB CSV batch stored: {summary.position_count} positions from "
                    f"{summary.selected_depot_count} selected depot export(s); snapshot timestamp "
                    f"{summary.generated_at.isoformat(timespec='seconds')}.",
                )
                _LOGGER.info(
                    "DKB CSV import stored: input_files=%s selected_exports=%s positions=%s",
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
                if (self.app_server.csv_provider.acquisition_mode == MODE_CSV
                        and not self.app_server.gateway_state.refresh(trigger="manual")):
                    self.app_server.csv_provider.replace_cash_snapshot(previous_cash)
                    self.app_server.csv_provider.persist_cash_snapshot(previous_cash)
                    raise DkbCashCsvImportError("Imported DKB cash CSV could not be activated")
                self.app_server.controller.clear_cash_review()
                self.app_server.last_import_notice = (
                    "accepted",
                    f"DKB cash CSV stored: EUR {cash.eligible_eur}; cash timestamp "
                    f"{cash.as_of.isoformat(timespec='seconds')}.",
                )
                _LOGGER.info("DKB cash CSV import stored normalized provider-scoped cash evidence")
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
        if path == "/discover-accounts":
            if set(form) != {"csrf", "user_id", "pin"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                self.app_server.controller.discover_accounts(form["user_id"], form["pin"])
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB account discovery failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
            self._redirect("./")
            return
        if path == "/complete-account-discovery":
            if set(form) != {"csrf", "tan"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                self.app_server.controller.continue_account_discovery(form["tan"])
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB account discovery approval failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
            self._redirect("./")
            return
        if path == "/select-account":
            if set(form) != {"csrf", "candidate"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                with self.app_server.csv_provider.selection_guard():
                    selected = self.app_server.controller.select_account(form["candidate"])
                self.app_server.last_import_notice = ("accepted", f"Selected {selected.masked_label}. A fresh manual read is required.")
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB account selection failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._redirect("./")
            return
        if path == "/clear-account":
            if set(form) != {"csrf"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                with self.app_server.csv_provider.selection_guard():
                    self.app_server.controller.clear_selected_account()
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            self.app_server.last_import_notice = ("accepted", "DKB investment cash account selection cleared.")
            self._redirect("./")
            return
        if path == "/set-cash-policy":
            if set(form) != {"csrf", "mode", "cap_eur", "retain_eur"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                policy = parse_policy_input(form["mode"], form["cap_eur"], form["retain_eur"])
                provider = self.app_server.csv_provider
                previous = provider.investment_cash_policy()
                provider.set_investment_cash_policy(policy)
                if provider.holdings_snapshot is not None and not self.app_server.gateway_state.refresh(trigger="manual"):
                    provider.set_investment_cash_policy(previous)
                    self.app_server.gateway_state.refresh(trigger="manual")
                    raise ValueError("Cash authorization change could not be published")
                self.app_server.last_import_notice = ("accepted", "DKB investment cash authorization policy saved.")
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB cash authorization update failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._redirect("./")
            return
        if path == "/set-acquisition":
            if set(form) != {"csrf", "mode", "confirm"} or form["confirm"] != "yes":
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                provider = self.app_server.csv_provider
                if self.app_server.controller.portfolio_refresh_state() in {"holdings_pending", "cash_pending", "starting"}:
                    raise ValueError("Complete the current bank read before switching")
                provider.activate_mode(form["mode"],
                                       lambda: self.app_server.gateway_state.refresh(trigger="manual"))
                self.app_server.last_import_notice = (
                    "accepted", f"DKB {provider.acquisition_mode.upper()} acquisition selected explicitly.")
            except (ValueError, ConfigurationError):
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB acquisition switch failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._redirect("./")
            return
        if path == "/refresh-portfolio":
            if set(form) != {"csrf", "user_id", "pin"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                outcome = self.app_server.controller.run_portfolio_refresh(
                    form["user_id"], form["pin"], self.app_server.csv_provider.holdings_snapshot,
                    self.app_server.csv_provider.cash_snapshot)
                if (outcome == "complete" and self.app_server.csv_provider.acquisition_mode == MODE_FINTS
                        and not self.app_server.gateway_state.refresh(trigger="manual")):
                    raise ValueError("DKB FinTS observation could not be published")
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB manual portfolio refresh failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
            self._redirect("./")
            return
        if path == "/complete-portfolio-approval":
            if set(form) != {"csrf", "tan"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                outcome = self.app_server.controller.continue_portfolio_refresh(
                    form["tan"], self.app_server.csv_provider.holdings_snapshot,
                    self.app_server.csv_provider.cash_snapshot)
                if (outcome == "complete" and self.app_server.csv_provider.acquisition_mode == MODE_FINTS
                        and not self.app_server.gateway_state.refresh(trigger="manual")):
                    raise ValueError("DKB FinTS observation could not be published")
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB manual portfolio approval failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
            self._redirect("./")
            return
        if path == "/configure-product":
            if set(form) != {"csrf", "product_id"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                with self.app_server.csv_provider.selection_guard():
                    self.app_server.controller.configure_product_id(form.get("product_id", ""))
            except ValueError:
                self._redirect("./?error=invalid_product_id")
                return
            self._redirect("./")
            return
        if path == "/observe-user":
            if set(form) != {"csrf", "user_id", "pin"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                self.app_server.controller.run_auth_observation(form["user_id"], form["pin"])
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                # The error may carry bank challenge/account/credential text.
                _LOGGER.error("DKB authenticated FinTS research failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
            self._redirect("./")
            return
        if path == "/complete-user-approval":
            if set(form) != {"csrf", "tan"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                self.app_server.controller.continue_auth_observation(form["tan"])
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB authenticated FinTS approval failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
            self._redirect("./")
            return
        if path == "/observe-holdings":
            if set(form) != {"csrf", "user_id", "pin"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                self.app_server.controller.run_holdings_observation(
                    form["user_id"], form["pin"], self.app_server.csv_provider.holdings_snapshot)
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB read-only holdings research failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
            self._redirect("./")
            return
        if path == "/complete-holdings-approval":
            if set(form) != {"csrf", "tan"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                self.app_server.controller.continue_holdings_observation(
                    form["tan"], self.app_server.csv_provider.holdings_snapshot)
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB read-only holdings approval failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
            self._redirect("./")
            return
        if path == "/observe-cash-balance":
            if set(form) != {"csrf", "user_id", "pin", "iban_suffix"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                self.app_server.controller.run_cash_observation(
                    form["user_id"], form["pin"], form["iban_suffix"],
                    self.app_server.csv_provider.cash_snapshot)
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB read-only cash research failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
            self._redirect("./")
            return
        if path == "/complete-cash-approval":
            if set(form) != {"csrf", "tan"}:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            try:
                self.app_server.controller.continue_cash_observation(
                    form["tan"], self.app_server.csv_provider.cash_snapshot)
            except ValueError:
                self._empty(HTTPStatus.BAD_REQUEST)
                return
            except Exception:
                _LOGGER.error("DKB read-only cash approval failed internally")
                self._empty(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            finally:
                form.clear()
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
        """Admin-only DKB operations; historical anonymous probe has no UI control."""
        controller = self.app_server.controller
        product = controller.product_id()
        csrf = escape(controller.csrf_token, quote=True)
        registration = f"…{product[-6:]}" if product else "not configured"
        state, options, discovery_decoupled = controller.account_discovery_view()
        try:
            selected = controller.selected_account()
            selected_label = selected.masked_label if selected else "None selected"
        except (ProtocolError, OSError):
            selected = None
            selected_label = "Invalid private selection; clear and rediscover"
        portfolio = controller.portfolio_refresh_state()
        pending = portfolio in {"holdings_pending", "cash_pending"}
        discovery_pending = state == "approval_pending"
        disabled = "disabled" if product is None or pending or discovery_pending else ""
        try:
            cash_policy = self.app_server.csv_provider.investment_cash_policy()
            policy_warning = ""
        except (ProtocolError, OSError):
            cash_policy = None
            policy_warning = '<p class="warn">Stored cash authorization is invalid; planning cash is unavailable.</p>'
        mode = cash_policy.mode if cash_policy else ""
        acquisition_mode = self.app_server.csv_provider.acquisition_mode
        fints_ready = next(item.can_activate for item in self.app_server.csv_provider.acquisition_control.methods
                           if item.method_id == MODE_FINTS)
        cap = str(cash_policy.cap_eur) if cash_policy and cash_policy.cap_eur is not None else ""
        retain = str(cash_policy.retain_eur) if cash_policy and cash_policy.retain_eur is not None else ""
        notice = ""
        if self.app_server.last_import_notice is not None:
            outcome, message = self.app_server.last_import_notice
            notice = f'<p class="{"ok" if outcome == "accepted" else "warn"}">{escape(message)}</p>'
        holdings = self.app_server.csv_provider.holdings_snapshot
        csv_holdings = (f"{len(holdings.positions)} positions; observed {holdings.generated_at.isoformat(timespec='seconds')} UTC"
                        if holdings is not None else "Not imported")
        cash = self.app_server.csv_provider.cash_snapshot
        csv_cash = (f"Balance date {cash.as_of.isoformat(timespec='seconds')} UTC"
                    if cash is not None else "Not imported")
        candidate_form = ""
        if options:
            choices = "".join(f'<option value="{escape(token, quote=True)}">{escape(label)}</option>'
                              for token, label in options)
            candidate_form = (f'<form method="post" action="select-account"><input type="hidden" name="csrf" value="{csrf}">'
                              f'<label for="candidate">Eligible EUR account</label><select id="candidate" name="candidate" required>{choices}</select>'
                              '<button type="submit">Select investment account</button></form>'
                              '<p class="small">Masked choices expire after five minutes; raw account identifiers are not saved.</p>')
        discovery_approval = ""
        if discovery_pending:
            control = ('<input type="hidden" name="tan" value="">' if discovery_decoupled else
                       '<label for="discovery-tan">TAN</label><input id="discovery-tan" name="tan" type="password" maxlength="32" autocomplete="off" required>')
            discovery_approval = (f'<form method="post" action="complete-account-discovery">'
                                  f'<input type="hidden" name="csrf" value="{csrf}">{control}'
                                  '<button type="submit">Check bank approval</button></form>')
        portfolio_approval = ""
        if pending:
            decoupled = (controller.pending_holdings_is_decoupled() if portfolio == "holdings_pending" else
                         controller.pending_cash_is_decoupled())
            control = ('<input type="hidden" name="tan" value="">' if decoupled else
                       '<label for="refresh-tan">TAN</label><input id="refresh-tan" name="tan" type="password" maxlength="32" autocomplete="off" required>')
            portfolio_approval = (f'<form method="post" action="complete-portfolio-approval">'
                                  f'<input type="hidden" name="csrf" value="{csrf}">{control}'
                                  '<button type="submit">Check bank approval and continue refresh</button></form>')
        holdings_shadow = shadow_summary(controller.shadow_file)
        cash_shadow = cash_shadow_summary(controller.cash_shadow_file)
        evidence = (f'Holdings: {holdings_shadow["state"]}; observed {holdings_shadow["observed_at"] or "none"} UTC. '
                    f'Cash: {cash_shadow["state"]}; observed {cash_shadow["observed_at"] or "none"} UTC; '
                    f'bank balance date {cash_shadow["bank_date"] or "none"}.')
        review = controller.holdings_review()
        holdings_detail = render_review(review) if review is not None else ""
        cash_review = controller.cash_review()
        cash_detail = ""
        if cash_review is not None:
            csv_observation, bank = cash_review
            csv_value = str(csv_observation.account_balance_eur) if csv_observation is not None else "unavailable"
            cash_detail = (f'<p>CSV booked balance: EUR {escape(csv_value)}; FinTS booked balance: '
                           f'{escape(bank.currency)} {escape(bank.amount)}; bank date {escape(bank.bank_date)}. '
                           'The observations may differ because their times differ.</p>')
        authority = render_acquisition_authority(
            self.app_server.csv_provider.acquisition_control,
            evidence_timestamps=self.app_server.gateway_state.capability_evidence_timestamps())
        body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio Architect Gateway — DKB</title><style>
:root{{color-scheme:dark;font-family:system-ui,sans-serif}}body{{max-width:920px;margin:1.5rem auto;padding:0 1rem;background:#111;color:#eee}}
h1{{font-size:1.55rem}}section{{border:1px solid #555;border-radius:12px;padding:1rem;margin:1rem 0}}.active{{border-color:#4ade80}}
.prepared{{border-color:#fbbf24}}.small{{font-size:.9rem;color:#bbb}}.warn{{color:#ffca28}}.ok{{color:#66bb6a}}
label{{display:block;margin-top:.7rem}}input,select{{box-sizing:border-box;width:min(34rem,100%);padding:.55rem;margin-top:.25rem}}
button{{padding:.55rem .8rem;margin:.6rem .4rem .2rem 0}}code{{overflow-wrap:anywhere}}details{{margin-top:1rem}}
{ACQUISITION_AUTHORITY_CSS}</style></head><body><main><h1>Portfolio Architect Gateway — DKB</h1>{notice}
<section class="{'active' if acquisition_mode == MODE_CSV else 'prepared'}"><h2>DKB CSV · {'authoritative' if acquisition_mode == MODE_CSV else 'staged'}</h2><p>Depot: {escape(csv_holdings)}<br>Girokonto: {escape(csv_cash)}</p>
<form method="post" action="import-csv" enctype="multipart/form-data"><input type="hidden" name="nonce" value="{csrf}">
<label for="statement">DKB depot CSV export(s)</label><input id="statement" type="file" name="statement" accept="text/csv,.csv" multiple required>
<button type="submit">Import depot CSV</button></form>
<form method="post" action="import-cash" enctype="multipart/form-data"><input type="hidden" name="nonce" value="{csrf}">
<label for="cash-statement">DKB Girokonto cash CSV</label><input id="cash-statement" type="file" name="statement" accept="text/csv,.csv" required>
<button type="submit">Import cash CSV</button></form><p class="small">CSV imports update this independent source. They never switch acquisition authority.</p></section>
<section class="{'active' if acquisition_mode == MODE_FINTS else 'prepared'}"><h2>Manual DKB FinTS · {'authoritative' if acquisition_mode == MODE_FINTS else 'staged'}</h2><p>Registration: <code>{escape(registration)}</code></p>
<form method="post" action="configure-product"><input type="hidden" name="csrf" value="{csrf}">
<label for="product-id">Portfolio Architect FinTS registration number</label><input id="product-id" name="product_id" minlength="25" maxlength="25" pattern="[A-Za-z0-9]{{25}}" autocomplete="off" required>
<button type="submit">Store registration number</button></form>
<h3>Dedicated investment account</h3><p>Selected: <strong>{escape(selected_label)}</strong>. Discovery: {escape(state)}.</p>
<form method="post" action="discover-accounts" autocomplete="off"><input type="hidden" name="csrf" value="{csrf}">
<label for="discover-user">DKB banking login name</label><input id="discover-user" name="user_id" maxlength="128" autocomplete="off" required>
<label for="discover-pin">DKB banking password</label><input id="discover-pin" name="pin" type="password" maxlength="256" autocomplete="off" required>
<button type="submit" {disabled}>Discover eligible EUR accounts</button></form>{discovery_approval}{candidate_form}
<form method="post" action="clear-account"><input type="hidden" name="csrf" value="{csrf}"><button type="submit">Clear selection</button></form>
<p class="small">Only a keyed private account binding and masked ending are saved. Credentials and the complete account inventory remain transient. Changing the selection invalidates the old cash research observation.</p>
<h3>Refresh portfolio</h3><p>State: <strong>{escape(portfolio)}</strong>. {escape(evidence)}</p>
<form method="post" action="refresh-portfolio" autocomplete="off"><input type="hidden" name="csrf" value="{csrf}">
<label for="refresh-user">DKB banking login name</label><input id="refresh-user" name="user_id" maxlength="128" autocomplete="off" required>
<label for="refresh-pin">DKB banking password</label><input id="refresh-pin" name="pin" type="password" maxlength="256" autocomplete="off" required>
<button type="submit" {disabled if selected is not None else 'disabled'}>Refresh portfolio now</button></form>{portfolio_approval}
<p class="small">One manual workflow reads the authorized depot and selected account. DKB may ask for approval at either step. A complete read stages private evidence; it affects planning only while FinTS is explicitly authoritative.</p>
<details><summary>Transient FinTS review</summary>{holdings_detail}{cash_detail or '<p>No current detail; a successful read is visible for five minutes.</p>'}</details></section>
<section><h2>Investment cash authorization</h2>{policy_warning}
<form method="post" action="set-cash-policy" autocomplete="off"><input type="hidden" name="csrf" value="{csrf}">
<label for="mode">Authorization policy</label><select id="mode" name="mode" required>
<option value="all_available" {'selected' if mode == MODE_ALL_AVAILABLE else ''}>All eligible cash</option>
<option value="capped" {'selected' if mode == MODE_CAPPED else ''}>Cap authorized cash</option>
<option value="retain" {'selected' if mode == MODE_RETAIN else ''}>Keep cash reserve</option></select>
<label for="cap">Authorized cash cap in EUR</label><input id="cap" name="cap_eur" inputmode="decimal" maxlength="16" value="{escape(cap, quote=True)}">
<label for="retain">Cash reserve to keep unallocated in EUR</label><input id="retain" name="retain_eur" inputmode="decimal" maxlength="16" value="{escape(retain, quote=True)}">
<button type="submit">Save authorization policy</button></form>
<p class="small">This policy applies to the authoritative DKB cash source. A negative booked balance authorizes EUR 0; pending transactions can make booked cash differ from spendable cash.</p></section>
<section><h2>Acquisition source</h2><p>Selected source: <strong>{escape(acquisition_mode)}</strong>. Automatic fallback: <strong>none</strong>.</p>
<p class="small">FinTS requires one complete manual read made with this release and the selected account. Both observations expire after 14 days. When FinTS evidence is unavailable, planning stops until a manual refresh or an explicit switch to fresh CSV.</p>
<form method="post" action="set-acquisition"><input type="hidden" name="csrf" value="{csrf}">
<label for="acquisition-mode">Use for holdings and cash</label><select id="acquisition-mode" name="mode" required>
<option value="csv" {'selected' if acquisition_mode == MODE_CSV else ''}>DKB CSV</option>
<option value="fints" {'selected' if acquisition_mode == MODE_FINTS else ''} {'disabled' if not fints_ready and acquisition_mode != MODE_FINTS else ''}>Manual DKB FinTS{' · fresh read required' if not fints_ready and acquisition_mode != MODE_FINTS else ''}</option></select>
<label><input type="checkbox" name="confirm" value="yes" required> Confirm explicit source change</label>
<button type="submit">Switch acquisition source</button></form></section>
{authority}<section><h2>Home Assistant connection</h2><p>Acquisition mode: <strong>{escape(acquisition_mode)}</strong></p><details><summary>Show bearer token</summary><code>{escape(self.app_server.api_token)}</code></details></section>
<script>const mode=document.getElementById('mode'),cap=document.getElementById('cap'),retain=document.getElementById('retain');
function sync(){{cap.disabled=mode.value!=='capped';cap.required=mode.value==='capped';retain.disabled=mode.value!=='retain';retain.required=mode.value==='retain';}}
mode.addEventListener('change',sync);sync();</script></main></body></html>'''
        return body.encode("utf-8")

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
        _LOGGER.debug("DKB Gateway Ingress request completed")



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
    """Run explicit DKB CSV/FinTS acquisition with no automatic fallback."""
    data_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    options = options or PendingAppOptions.load()
    server_config = build_server_config(options, data_directory, tls_cert_file=tls_cert_file, tls_key_file=tls_key_file)
    api_token = ensure_api_token(server_config.api_token_file)
    if provider_id != "dkb":
        raise RuntimeError("DKB Gateway provider identity is invalid")
    provider = DkbAcquisitionProvider(server_config.snapshot_file)
    state = GatewayState(server_config, provider)
    state.refresh(trigger="startup")
    controller = DKBProbeController(data_directory)
    controller.acquisition_provider = provider
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
    _LOGGER.info("DKB Gateway initialized; acquisition mode=%s", provider.acquisition_mode)
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
