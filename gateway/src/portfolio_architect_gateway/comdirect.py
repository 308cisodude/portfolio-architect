"""Minimal Comdirect authentication and read-only portfolio retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import logging
from pathlib import Path
import re
import time
import threading
from typing import Any, Callable, Protocol

from .config import ComdirectConfig, normalise_secret, read_secret
from .errors import (
    AuthenticationError,
    ConfigurationError,
    ProtocolError,
    ReauthenticationRequired,
    RemoteApiError,
)
from .models import MAX_POSITIONS, PortfolioSnapshot, Position, validate_snapshot
from .store import load_json_state, save_json_state
from .transport import ComdirectTransport, HttpResponse, decode_json_response

_LOGGER = logging.getLogger(__name__)
_WKN_RE = re.compile(r"^[A-Z0-9]{6}$")
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


class TransportProtocol(Protocol):
    """Narrow interface used by the client and fakes."""

    def restore_qsession(self, value: str | None) -> None: ...
    def current_qsession(self) -> str | None: ...
    def oauth_password(self, **kwargs: str) -> HttpResponse: ...
    def oauth_secondary(self, **kwargs: str) -> HttpResponse: ...
    def oauth_refresh(self, **kwargs: str) -> HttpResponse: ...
    def get_sessions(self, *, bearer: str) -> HttpResponse: ...
    def get_account_balances(self, *, bearer: str) -> HttpResponse: ...
    def validate_session(self, **kwargs: Any) -> HttpResponse: ...
    def activate_session(self, **kwargs: Any) -> HttpResponse: ...
    def poll_session_challenge(self, *, href: str, bearer: str) -> HttpResponse: ...
    def get_depots(self, *, bearer: str) -> HttpResponse: ...
    def get_positions(self, **kwargs: Any) -> HttpResponse: ...
    def get_instrument(self, *, instrument_id: str, bearer: str) -> HttpResponse: ...
    def get_instrument_probe(self, *, isin: str, bearer: str) -> HttpResponse: ...
    def post_cost_indication(self, *, order_document: dict[str, Any], bearer: str) -> HttpResponse: ...


@dataclass(frozen=True, slots=True)
class TokenState:
    """Persisted OAuth state; no username, password, or monetary value."""

    access_token: str
    refresh_token: str
    expires_at: int
    scope: str
    qsession: str

    def usable(self, *, now: int | None = None, margin_seconds: int = 90) -> bool:
        current = int(time.time()) if now is None else now
        return bool(self.access_token) and self.expires_at > current + margin_seconds

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "scope": self.scope,
            "qsession": self.qsession,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TokenState":
        if raw.get("schema_version") != 1:
            raise ProtocolError("Unsupported Comdirect session-state schema")
        access_token = _opaque(raw.get("access_token"), "access token", maximum=8192)
        refresh_token = _opaque(raw.get("refresh_token"), "refresh token", maximum=8192)
        scope = _text(raw.get("scope", ""), "scope", maximum=2048, required=False)
        qsession = _opaque(raw.get("qsession"), "qSession", maximum=2048)
        expires_at = raw.get("expires_at")
        if isinstance(expires_at, bool) or not isinstance(expires_at, int):
            raise ProtocolError("Comdirect session expiry is invalid")
        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scope=scope,
            qsession=qsession,
        )


@dataclass(frozen=True, slots=True)
class AccountBalanceCandidate:
    """One bounded EUR account candidate for investment-reserve selection."""

    account_id: str
    display_id: str
    account_type: str
    available_eur: Decimal
    as_of: datetime

    @property
    def masked_label(self) -> str:
        token = "".join(ch for ch in self.display_id if ch.isalnum())
        suffix = token[-4:] if token else self.account_id[-4:]
        return f"{self.account_type} · …{suffix}"




@dataclass(frozen=True, slots=True)
class DepotCandidate:
    """One private depot identifier with a display-safe admin label."""

    depot_id: str
    display_id: str

    @property
    def masked_label(self) -> str:
        token = "".join(ch for ch in self.display_id if ch.isalnum())
        return f"Depot · …{token[-4:]}" if token else "Depot candidate"


@dataclass(frozen=True, slots=True)
class InstrumentProbeResult:
    """Bounded public instrument fields retained by the experimental probe."""

    isin: str
    name: str
    wkn: str
    fund_status: str | None
    fund_flags: tuple[str, ...]
    currency: str | None
    surcharges: dict[str, str]
    venues: tuple[dict[str, str], ...]
    probed_at: datetime

    def public_dict(self) -> dict[str, Any]:
        return {
            "probe_type": "instrument_metadata",
            "isin": self.isin,
            "name": self.name,
            "wkn": self.wkn,
            "fund_status": self.fund_status,
            "fund_flags": list(self.fund_flags),
            "currency": self.currency,
            "surcharges": dict(self.surcharges),
            "venues": [
                {key: value for key, value in item.items() if key != "venue_id"}
                for item in self.venues
            ],
            "probed_at": self.probed_at.isoformat(timespec="seconds"),
            "interpretation": "opaque_observation_only",
        }


@dataclass(frozen=True, slots=True)
class CostProbeResult:
    """Sanitized ex-ante ordinary-order cost indication."""

    document: dict[str, Any]

    def public_dict(self) -> dict[str, Any]:
        return dict(self.document)


class ComdirectClient:
    """Own the required login/session flow and expose only portfolio reads."""

    def __init__(
        self,
        config: ComdirectConfig,
        *,
        transport: TransportProtocol | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._config = config
        self._transport = transport or ComdirectTransport(
            config.base_url, config.request_timeout_seconds
        )
        self._clock = clock
        self._operation_lock = threading.RLock()
        self._state = self._load_state()
        if self._state:
            self._transport.restore_qsession(self._state.qsession)

    def bootstrap(
        self,
        *,
        prompt: Callable[[str], str] = input,
        output: Callable[[str], None] = print,
        sleep: Callable[[float], None] = time.sleep,
    ) -> TokenState:
        """Run the file-backed interactive bootstrap and persist refresh state."""
        return self.bootstrap_with_credentials(
            client_id=read_secret(
                self._config.client_id_file,
                name="Comdirect client ID",
                maximum=512,
            ),
            client_secret=read_secret(
                self._config.client_secret_file,
                name="Comdirect client secret",
                maximum=1024,
            ),
            username=read_secret(
                self._config.username_file,
                name="Comdirect username",
                maximum=256,
            ),
            password=read_secret(
                self._config.password_file,
                name="Comdirect password",
                maximum=512,
            ),
            prompt=prompt,
            output=output,
            sleep=sleep,
        )

    def bootstrap_with_credentials(
        self,
        *,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        prompt: Callable[[str], str] = input,
        output: Callable[[str], None] = print,
        sleep: Callable[[float], None] = time.sleep,
    ) -> TokenState:
        """Bootstrap from bounded in-memory credentials and persist only OAuth state."""
        client_id = normalise_secret(
            client_id, name="Comdirect client ID", maximum=512
        )
        client_secret = normalise_secret(
            client_secret, name="Comdirect client secret", maximum=1024
        )
        username = normalise_secret(
            username, name="Comdirect username", maximum=256
        )
        password = normalise_secret(
            password, name="Comdirect password", maximum=512
        )

        with self._operation_lock:
            initial = _parse_token_response(
                self._transport.oauth_password(
                    client_id=client_id,
                    client_secret=client_secret,
                    username=username,
                    password=password,
                ),
                now=int(self._clock()),
                require_refresh=False,
                require_brokerage=False,
            )

            sessions_raw = decode_json_response(
                self._transport.get_sessions(bearer=initial.access_token)
            )
            session_document = _select_session(sessions_raw)
            session_id = _text(
                session_document.get("identifier"),
                "session identifier",
                maximum=128,
            )
            # Comdirect's session-TAN validation endpoint expects the exact
            # activation intent, not the unmodified session-status document.
            # Sending the status response back with false flags is rejected
            # with HTTP 422 before a PhotoTAN challenge is created.
            validation_document = {
                "identifier": session_id,
                "sessionTanActive": True,
                "activated2FA": True,
            }
            validation = self._transport.validate_session(
                session_id=session_id,
                session_document=validation_document,
                bearer=initial.access_token,
            )
            challenge = _parse_challenge_header(
                validation.headers.get("x-once-authentication-info")
            )
            challenge_info_header = _activation_challenge_info(challenge)
            once_authentication = self._complete_challenge(
                challenge,
                bearer=initial.access_token,
                prompt=prompt,
                output=output,
                sleep=sleep,
            )
            activation_document = dict(validation_document)
            self._transport.activate_session(
                session_id=session_id,
                session_document=activation_document,
                bearer=initial.access_token,
                once_authentication_info=challenge_info_header,
                once_authentication=once_authentication,
            )

            secondary = _parse_token_response(
                self._transport.oauth_secondary(
                    client_id=client_id,
                    client_secret=client_secret,
                    initial_access_token=initial.access_token,
                ),
                now=int(self._clock()),
                require_refresh=True,
                require_brokerage=True,
            )
            qsession = self._transport.current_qsession()
            if not qsession:
                raise AuthenticationError(
                    "Comdirect did not establish the required qSession cookie"
                )
            state = TokenState(
                access_token=secondary.access_token,
                refresh_token=secondary.refresh_token,
                expires_at=secondary.expires_at,
                scope=secondary.scope,
                qsession=qsession,
            )
            self._state = state
            save_json_state(self._config.session_file, state.as_dict())
            return state

    def ensure_access_token(self) -> str:
        """Return a usable secondary token or refresh it without using bank credentials."""
        with self._operation_lock:
            return self._ensure_access_token_locked()

    def _ensure_access_token_locked(self) -> str:
        if self._state and self._state.usable(now=int(self._clock())):
            return self._state.access_token
        if not self._state or not self._state.refresh_token:
            raise ReauthenticationRequired("Interactive Comdirect bootstrap is required")

        client_id = read_secret(
            self._config.client_id_file, name="Comdirect client ID", maximum=512
        )
        client_secret = read_secret(
            self._config.client_secret_file,
            name="Comdirect client secret",
            maximum=1024,
        )
        try:
            refreshed = _parse_token_response(
                self._transport.oauth_refresh(
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=self._state.refresh_token,
                ),
                now=int(self._clock()),
                require_refresh=False,
                require_brokerage=True,
                fallback_refresh_token=self._state.refresh_token,
            )
        except RemoteApiError as err:
            if err.error_code == "invalid_client":
                raise ConfigurationError(
                    "Comdirect rejected the configured API client credentials"
                ) from err
            if err.error_code in {"invalid_grant", "invalid_token"} or err.status in {
                401,
                403,
            }:
                raise ReauthenticationRequired(
                    "Comdirect rejected the persisted refresh session; rerun the interactive bootstrap"
                ) from err
            # Connectivity, rate-limit, upstream-service and unclassified protocol
            # failures are retryable operational failures, not evidence that the
            # user's PhotoTAN session is invalid. Preserve their classification.
            raise
        qsession = self._transport.current_qsession() or self._state.qsession
        state = TokenState(
            access_token=refreshed.access_token,
            refresh_token=refreshed.refresh_token,
            expires_at=refreshed.expires_at,
            scope=refreshed.scope,
            qsession=qsession,
        )
        self._state = state
        save_json_state(self._config.session_file, state.as_dict())
        return state.access_token

    def discover_investment_accounts(self) -> tuple[AccountBalanceCandidate, ...]:
        """Return bounded masked EUR balance candidates through the admin-only UI."""
        with self._operation_lock:
            bearer = self._ensure_access_token_locked()
            return self._fetch_account_candidates_locked(bearer)

    def selected_investment_account_id(self) -> str | None:
        raw = load_json_state(self._config.investment_account_file)
        if raw is None:
            return None
        if raw.get("schema_version") != 1:
            raise ProtocolError("Unsupported investment-account selection schema")
        value = raw.get("account_id")
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            raise ProtocolError("Stored investment-account selection is invalid")
        return value.strip()

    def select_investment_account(self, account_id: str) -> AccountBalanceCandidate:
        """Persist one explicitly selected account after live candidate validation."""
        cleaned = _text(account_id, "investment account ID", maximum=128)
        with self._operation_lock:
            bearer = self._ensure_access_token_locked()
            candidates = self._fetch_account_candidates_locked(bearer)
            match = next((item for item in candidates if item.account_id == cleaned), None)
            if match is None:
                raise ConfigurationError("Selected investment account is not available")
            save_json_state(
                self._config.investment_account_file,
                {"schema_version": 1, "account_id": cleaned},
            )
            return match

    def clear_investment_account(self) -> None:
        self._config.investment_account_file.unlink(missing_ok=True)

    def _fetch_account_candidates_locked(
        self, bearer: str
    ) -> tuple[AccountBalanceCandidate, ...]:
        raw = decode_json_response(self._transport.get_account_balances(bearer=bearer))
        values = _extract_values(raw, field="account balances")
        result: list[AccountBalanceCandidate] = []
        seen: set[str] = set()
        fetched_at = datetime.now(timezone.utc)
        for item in values:
            if not isinstance(item, dict):
                raise ProtocolError("Comdirect account balance list contains a non-object")
            account = item.get("account")
            if not isinstance(account, dict):
                account = {}
            account_id = _optional_first_text(item, ("accountId",)) or _optional_first_text(
                account, ("accountId", "identifier", "id")
            )
            if not account_id:
                raise ProtocolError("Comdirect account balance lacks an account ID")
            account_id = account_id.strip()
            if len(account_id) > 128 or account_id in seen:
                raise ProtocolError("Comdirect account balance contains an invalid or duplicate ID")
            seen.add(account_id)
            currency = _optional_first_text(account, ("currency",)) or "EUR"
            if currency.upper() != "EUR":
                continue
            available_raw = item.get("availableCashAmountEUR")
            if available_raw is None:
                available_raw = item.get("availableCashAmount")
            balance_raw = item.get("balanceEUR")
            if balance_raw is None:
                balance_raw = item.get("balance")
            if available_raw is None or balance_raw is None:
                # A reserve must be both liquid and backed by a non-negative cash
                # balance. Requiring both fields prevents an overdraft or credit
                # line from being treated as investable retirement-plan cash.
                continue
            available = _signed_amount_eur(
                available_raw, field="account availableCashAmount"
            )
            balance = _signed_amount_eur(balance_raw, field="account balance")
            amount = max(Decimal("0"), min(available, balance))
            display = (
                _optional_first_text(account, ("accountDisplayId", "iban"))
                or _optional_first_text(item, ("accountDisplayId",))
                or account_id
            )
            account_type = (
                _optional_first_text(account, ("accountType", "type"))
                or _optional_first_text(item, ("accountType",))
                or "ACCOUNT"
            )
            if account_type.upper() in {"DEPOT", "CREDIT_CARD", "CARD"}:
                continue
            result.append(
                AccountBalanceCandidate(
                    account_id=account_id,
                    display_id=display,
                    account_type=account_type,
                    available_eur=amount,
                    as_of=fetched_at,
                )
            )
        return tuple(sorted(result, key=lambda item: (item.account_type, item.masked_label, item.account_id)))

    def discover_depots(self) -> tuple[DepotCandidate, ...]:
        """Return bounded depot candidates for the admin-only probe UI."""
        with self._operation_lock:
            bearer = self._ensure_access_token_locked()
            raw = decode_json_response(self._transport.get_depots(bearer=bearer))
            values = _extract_values(raw, field="depots")
            candidates: list[DepotCandidate] = []
            seen: set[str] = set()
            for item in values:
                if not isinstance(item, dict):
                    raise ProtocolError("Comdirect depot list contains a non-object")
                depot_id = _first_text(item, ("depotId",), "depot ID")
                if depot_id in seen:
                    raise ProtocolError("Comdirect depot list contains duplicate IDs")
                seen.add(depot_id)
                display = _optional_first_text(item, ("depotDisplayId",)) or depot_id[-4:]
                candidates.append(DepotCandidate(depot_id, _text(display, "depot display ID", maximum=64)))
                if len(candidates) > 32:
                    raise ProtocolError("Comdirect returned too many depots")
            return tuple(candidates)

    def probe_instrument(self, isin: str) -> InstrumentProbeResult:
        """Probe documented fundDistribution and orderDimensions for one ISIN."""
        cleaned = _validated_isin(isin)
        with self._operation_lock:
            bearer = self._ensure_access_token_locked()
            raw = decode_json_response(
                self._transport.get_instrument_probe(isin=cleaned, bearer=bearer)
            )
        document = _extract_instrument_document(raw)
        actual_isin = _instrument_isin(document) or cleaned
        if actual_isin != cleaned:
            raise ProtocolError("Comdirect instrument probe returned a different ISIN")
        funds = document.get("fundsDistribution")
        if not isinstance(funds, dict):
            funds = {}
        flags_raw = funds.get("fundFlags", [])
        if not isinstance(flags_raw, list) or len(flags_raw) > 64:
            raise ProtocolError("Comdirect fundFlags is malformed or unbounded")
        flags = tuple(sorted({_text(value, "fund flag", maximum=64) for value in flags_raw}))
        surcharges: dict[str, str] = {}
        for key in (
            "regularIssueSurcharge",
            "discountIssueSurcharge",
            "reducedIssueSurcharge",
            "individualIssueSurcharge",
        ):
            value = funds.get(key)
            if value is not None:
                surcharges[key] = _decimal_text(value, key, maximum=Decimal("1000"))
        venues = _public_venues(document.get("orderDimensions"))
        return InstrumentProbeResult(
            isin=cleaned,
            name=_instrument_name(document, fallback=cleaned),
            wkn=_optional_first_text(document, ("wkn",)) or "",
            fund_status=_optional_bounded_text(funds.get("fundStatus"), "fund status", 16),
            fund_flags=flags,
            currency=_optional_bounded_text(funds.get("currency"), "fund currency", 8),
            surcharges=surcharges,
            venues=venues,
            probed_at=datetime.now(timezone.utc),
        )

    def probe_cost_indication(
        self,
        *,
        depot_id: str,
        isin: str,
        venue_id: str,
        venue_name: str,
        quantity: Decimal,
    ) -> CostProbeResult:
        """Request a BUY/MARKET ex-ante indication without validating or placing an order."""
        cleaned_isin = _validated_isin(isin)
        cleaned_depot = _text(depot_id, "depot ID", maximum=40)
        cleaned_venue = _text(venue_id, "venue ID", maximum=40)
        display_venue = _text(venue_name, "venue name", maximum=80)
        if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity <= 0 or quantity > Decimal("1000000"):
            raise ProtocolError("Probe quantity is outside the allowed range")
        quantity_text = format(quantity.normalize(), "f")
        order = {
            "depotId": cleaned_depot,
            "side": "BUY",
            "instrumentId": cleaned_isin,
            "venueId": cleaned_venue,
            "quantity": {"value": quantity_text, "unit": "XXX"},
            "orderType": "MARKET",
            "validityType": "GFD",
            "bestEx": False,
        }
        with self._operation_lock:
            bearer = self._ensure_access_token_locked()
            raw = decode_json_response(
                self._transport.post_cost_indication(order_document=order, bearer=bearer)
            )
        value = _extract_single_cost_indication(raw)
        result = _sanitize_cost_indication(
            value,
            requested_depot=cleaned_depot,
            requested_isin=cleaned_isin,
            requested_quantity=quantity_text,
            requested_venue=display_venue,
        )
        return CostProbeResult(result)

    def fetch_snapshot(self) -> PortfolioSnapshot:
        """Fetch all selected depots and normalize their positions into schema 1."""
        with self._operation_lock:
            return self._fetch_snapshot_locked()

    def _fetch_snapshot_locked(self) -> PortfolioSnapshot:
        bearer = self._ensure_access_token_locked()
        depots = _extract_values(
            decode_json_response(self._transport.get_depots(bearer=bearer)),
            field="depots",
        )
        available: dict[str, dict[str, Any]] = {}
        for item in depots:
            if not isinstance(item, dict):
                raise ProtocolError("Comdirect depot list contains a non-object")
            depot_id = _first_text(item, ("depotId", "identifier", "id"), "depot ID")
            if depot_id in available:
                raise ProtocolError("Comdirect returned a duplicate depot ID")
            available[depot_id] = item
        if not available:
            raise ProtocolError("Comdirect returned no securities depot")

        selected = self._config.depot_ids or tuple(available)
        missing = [depot_id for depot_id in selected if depot_id not in available]
        if missing:
            raise ProtocolError("A configured depot ID is not present in the account")

        metadata_cache: dict[str, dict[str, Any]] = {}
        combined: dict[str, Position] = {}
        seen_isin_to_wkn: dict[str, str] = {}
        for depot_id in selected:
            raw_positions = self._fetch_all_positions(depot_id, bearer=bearer)
            for raw_position in raw_positions:
                position = self._normalise_position(
                    raw_position,
                    bearer=bearer,
                    metadata_cache=metadata_cache,
                )
                if position.isin:
                    prior_wkn = seen_isin_to_wkn.get(position.isin)
                    if prior_wkn and prior_wkn != position.identifier:
                        raise ProtocolError(
                            "Comdirect returned one ISIN under multiple WKN identifiers"
                        )
                    seen_isin_to_wkn[position.isin] = position.identifier
                existing = combined.get(position.identifier)
                if existing is None:
                    combined[position.identifier] = position
                else:
                    if (
                        existing.isin != position.isin
                        or existing.name != position.name
                        or existing.instrument_type != position.instrument_type
                    ):
                        raise ProtocolError(
                            "Conflicting metadata for the same WKN across depots"
                        )
                    combined[position.identifier] = Position(
                        identifier=existing.identifier,
                        name=existing.name,
                        market_value_eur=existing.market_value_eur
                        + position.market_value_eur,
                        isin=existing.isin,
                        instrument_type=existing.instrument_type,
                    )
                if len(combined) > MAX_POSITIONS:
                    raise ProtocolError("Portfolio exceeds the 512-position contract limit")

        reserve_eur = None
        reserve_as_of = None
        selected_account_id = self.selected_investment_account_id()
        if selected_account_id is not None:
            candidates = self._fetch_account_candidates_locked(bearer)
            selected_account = next(
                (item for item in candidates if item.account_id == selected_account_id),
                None,
            )
            if selected_account is None:
                raise ProtocolError("Configured investment account is not present in the live balance response")
            reserve_eur = selected_account.available_eur
            reserve_as_of = selected_account.as_of
        snapshot = PortfolioSnapshot(
            generated_at=datetime.now(timezone.utc),
            positions=tuple(combined[key] for key in sorted(combined)),
            investment_reserve_eur=reserve_eur,
            investment_reserve_as_of=reserve_as_of,
        )
        return validate_snapshot(snapshot)

    def _fetch_all_positions(self, depot_id: str, *, bearer: str) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        first = 0
        page_size = 100
        for _page in range(0, 7):
            response = decode_json_response(
                self._transport.get_positions(
                    depot_id=depot_id,
                    first=first,
                    count=page_size,
                    bearer=bearer,
                )
            )
            values = _extract_values(response, field="positions")
            for item in values:
                if not isinstance(item, dict):
                    raise ProtocolError("Comdirect position list contains a non-object")
                collected.append(item)
                if len(collected) > MAX_POSITIONS:
                    raise ProtocolError("One depot exceeds the 512-position contract limit")
            if not values:
                break
            matches = _paging_matches(response)
            first += len(values)
            if matches is None:
                if len(values) < page_size:
                    break
            elif first >= matches:
                break
        else:
            raise ProtocolError("Comdirect position pagination exceeded the bounded page limit")
        return collected

    def _normalise_position(
        self,
        raw: dict[str, Any],
        *,
        bearer: str,
        metadata_cache: dict[str, dict[str, Any]],
    ) -> Position:
        nested_instrument = raw.get("instrument")
        if not isinstance(nested_instrument, dict):
            nested_instrument = {}
        wkn = _optional_first_text(raw, ("wkn",)) or _optional_first_text(
            nested_instrument, ("wkn",)
        )
        if not wkn:
            raise ProtocolError("Comdirect position lacks a WKN")
        wkn = wkn.strip().upper()
        if _WKN_RE.fullmatch(wkn) is None:
            raise ProtocolError("Comdirect position contains an invalid WKN")

        instrument_id = (
            _optional_first_text(raw, ("instrumentId",))
            or _optional_first_text(nested_instrument, ("instrumentId", "identifier"))
            or wkn
        )
        metadata = dict(nested_instrument)
        if not _metadata_complete(metadata):
            cached = metadata_cache.get(instrument_id)
            if cached is None:
                fetched = decode_json_response(
                    self._transport.get_instrument(
                        instrument_id=instrument_id, bearer=bearer
                    )
                )
                cached = _extract_instrument_document(fetched)
                metadata_cache[instrument_id] = cached
            metadata = _merge_metadata(metadata, cached)

        amount = _amount_eur(raw.get("currentValue"), field="position currentValue")
        name = _instrument_name(metadata, fallback=wkn)
        isin = _instrument_isin(metadata)
        instrument_type = _instrument_type(metadata)
        return Position(
            identifier=wkn,
            name=name,
            market_value_eur=amount,
            isin=isin,
            instrument_type=instrument_type,
        )

    def _complete_challenge(
        self,
        challenge: dict[str, Any],
        *,
        bearer: str,
        prompt: Callable[[str], str],
        output: Callable[[str], None],
        sleep: Callable[[float], None],
    ) -> str | None:
        challenge_type = _challenge_type(challenge)
        if "P_TAN_PUSH" in challenge_type.upper() or "PUSH" in challenge_type.upper():
            output("Approve the Comdirect PhotoTAN push request on the registered device.")
            href = _challenge_href(challenge)
            if href:
                deadline = self._clock() + self._config.mfa_timeout_seconds
                while self._clock() < deadline:
                    status_document = decode_json_response(
                        self._transport.poll_session_challenge(
                            href=href, bearer=bearer
                        )
                    )
                    status = _find_status(status_document)
                    if status in {"AUTHENTICATED", "APPROVED", "SUCCESS"}:
                        return None
                    if status in {"REJECTED", "DENIED", "FAILED", "EXPIRED"}:
                        raise AuthenticationError("Comdirect PhotoTAN challenge was not approved")
                    sleep(2)
                raise AuthenticationError("Comdirect PhotoTAN challenge timed out")
            prompt("Approve the PhotoTAN push request, then press Enter to continue: ")
            return None

        tan = prompt(f"Enter the one-time authentication value for {challenge_type}: ").strip()
        if not tan or len(tan) > 128 or any(ord(ch) < 33 or ord(ch) > 126 for ch in tan):
            raise AuthenticationError("The one-time authentication value is invalid")
        return tan

    def _load_state(self) -> TokenState | None:
        raw = load_json_state(self._config.session_file)
        if raw is None:
            return None
        return TokenState.from_dict(raw)


def _parse_token_response(
    response: HttpResponse,
    *,
    now: int,
    require_refresh: bool,
    require_brokerage: bool,
    fallback_refresh_token: str = "",
) -> TokenState:
    raw = decode_json_response(response)
    if not isinstance(raw, dict):
        raise AuthenticationError("Comdirect OAuth response must be an object")
    access_token = _opaque(raw.get("access_token"), "access token", maximum=8192)
    refresh_raw = raw.get("refresh_token", fallback_refresh_token)
    if require_refresh and not refresh_raw:
        raise AuthenticationError("Comdirect secondary token lacks a refresh token")
    refresh_token = (
        _opaque(refresh_raw, "refresh token", maximum=8192)
        if refresh_raw
        else ""
    )
    expires_in = raw.get("expires_in")
    if isinstance(expires_in, bool) or not isinstance(expires_in, int):
        if isinstance(expires_in, str) and expires_in.isdecimal():
            expires_in = int(expires_in)
        else:
            raise AuthenticationError("Comdirect OAuth response lacks a valid expiry")
    if not 60 <= expires_in <= 86400:
        raise AuthenticationError("Comdirect OAuth expiry is outside the expected range")
    token_type = _text(raw.get("token_type", "Bearer"), "token type", maximum=32)
    if token_type.casefold() != "bearer":
        raise AuthenticationError("Comdirect returned an unsupported OAuth token type")
    scope = _text(raw.get("scope", ""), "scope", maximum=2048, required=False)
    if require_brokerage and "BROKERAGE" not in scope.upper():
        raise AuthenticationError("Comdirect token does not include brokerage access")
    return TokenState(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=now + expires_in,
        scope=scope,
        qsession="",
    )


def _select_session(raw: Any) -> dict[str, Any]:
    values = _extract_values(raw, field="sessions")
    candidates = [value for value in values if isinstance(value, dict)]
    if len(candidates) != 1:
        raise AuthenticationError("Comdirect returned an unexpected number of sessions")
    return dict(candidates[0])


def _parse_challenge_header(value: str | None) -> dict[str, Any]:
    if not value or len(value) > 32 * 1024:
        raise AuthenticationError("Comdirect did not return an MFA challenge")
    try:
        raw = json.loads(value)
    except json.JSONDecodeError as err:
        raise AuthenticationError("Comdirect returned a malformed MFA challenge") from err
    if not isinstance(raw, dict):
        raise AuthenticationError("Comdirect MFA challenge must be an object")
    return raw


def _activation_challenge_info(challenge: dict[str, Any]) -> str:
    challenge_id = challenge.get("id")
    if not isinstance(challenge_id, str) or not challenge_id.strip():
        raise AuthenticationError("Comdirect MFA challenge lacks its activation ID")
    cleaned = challenge_id.strip()
    if len(cleaned) > 256 or any(ord(ch) < 33 or ord(ch) > 126 for ch in cleaned):
        raise AuthenticationError("Comdirect MFA challenge ID is invalid")
    return json.dumps({"id": cleaned}, separators=(",", ":"))


def _challenge_type(challenge: dict[str, Any]) -> str:
    for key in ("typ", "type", "challengeType"):
        value = challenge.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "TAN"


def _challenge_href(challenge: dict[str, Any]) -> str | None:
    link = challenge.get("link")
    if isinstance(link, dict):
        href = link.get("href")
        method = link.get("method", "GET")
        if isinstance(href, str) and href.strip() and str(method).upper() == "GET":
            return href.strip()
    links = challenge.get("links")
    if isinstance(links, list):
        for item in links:
            if isinstance(item, dict):
                href = item.get("href")
                method = item.get("method", "GET")
                if isinstance(href, str) and href.strip() and str(method).upper() == "GET":
                    return href.strip()
    return None


def _find_status(raw: Any) -> str:
    if isinstance(raw, dict):
        for key in ("status", "authenticationStatus", "challengeStatus"):
            value = raw.get(key)
            if isinstance(value, str):
                return value.strip().upper()
        for value in raw.values():
            status = _find_status(value)
            if status:
                return status
    elif isinstance(raw, list):
        for value in raw:
            status = _find_status(value)
            if status:
                return status
    return "PENDING"


def _extract_values(raw: Any, *, field: str) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        values = raw.get("values")
        if isinstance(values, list):
            return values
    raise ProtocolError(f"Comdirect {field} response does not contain a values array")


def _paging_matches(raw: Any) -> int | None:
    if not isinstance(raw, dict):
        return None
    paging = raw.get("paging")
    if not isinstance(paging, dict):
        return None
    matches = paging.get("matches")
    if isinstance(matches, int) and not isinstance(matches, bool) and matches >= 0:
        return matches
    if isinstance(matches, str) and matches.isdecimal():
        return int(matches)
    return None


def _extract_instrument_document(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        values = raw.get("values")
        if isinstance(values, list):
            objects = [value for value in values if isinstance(value, dict)]
            if len(objects) != 1:
                raise ProtocolError("Comdirect instrument response is ambiguous")
            return dict(objects[0])
        return dict(raw)
    raise ProtocolError("Comdirect instrument response must be an object")


def _metadata_complete(metadata: dict[str, Any]) -> bool:
    return bool(
        _optional_first_text(metadata, ("name", "shortName"))
        and _optional_first_text(metadata, ("isin",))
    )


def _merge_metadata(primary: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    merged = dict(fallback)
    for key, value in primary.items():
        if value not in (None, "", {}, []):
            merged[key] = value
    primary_static = primary.get("staticData")
    fallback_static = fallback.get("staticData")
    if isinstance(primary_static, dict) or isinstance(fallback_static, dict):
        static: dict[str, Any] = {}
        if isinstance(fallback_static, dict):
            static.update(fallback_static)
        if isinstance(primary_static, dict):
            static.update(
                {key: value for key, value in primary_static.items() if value not in (None, "")}
            )
        merged["staticData"] = static
    return merged


def _instrument_name(metadata: dict[str, Any], *, fallback: str) -> str:
    value = _optional_first_text(metadata, ("name", "shortName"))
    if not value:
        static = metadata.get("staticData")
        if isinstance(static, dict):
            value = _optional_first_text(static, ("name", "shortName"))
    return _text(value or fallback, "instrument name", maximum=160)


def _instrument_isin(metadata: dict[str, Any]) -> str:
    value = _optional_first_text(metadata, ("isin",))
    if not value:
        static = metadata.get("staticData")
        if isinstance(static, dict):
            value = _optional_first_text(static, ("isin",))
    if not value:
        return ""
    isin = value.strip().upper()
    if _ISIN_RE.fullmatch(isin) is None:
        raise ProtocolError("Comdirect instrument contains an invalid ISIN")
    return isin


def _instrument_type(metadata: dict[str, Any]) -> str:
    candidates: list[Any] = []
    for key in ("instrumentType", "type"):
        candidates.append(metadata.get(key))
    static = metadata.get("staticData")
    if isinstance(static, dict):
        for key in ("instrumentType", "type", "productType"):
            candidates.append(static.get(key))
    tokens: list[str] = []
    for candidate in candidates:
        if isinstance(candidate, str):
            tokens.append(candidate)
        elif isinstance(candidate, dict):
            for key in ("key", "text", "name", "value"):
                value = candidate.get(key)
                if isinstance(value, str):
                    tokens.append(value)
    text = " ".join(tokens).casefold()
    mapping = (
        (("etf", "exchange traded fund"), "ETF"),
        (("aktie", "stock", "share"), "Stock"),
        (("fonds", "fund"), "Fund"),
        (("anleihe", "bond"), "Bond"),
        (("zertifikat", "certificate"), "Certificate"),
        (("optionsschein", "warrant"), "Warrant"),
        (("etc", "commodity"), "Commodity"),
        (("etn", "note"), "Note"),
    )
    for needles, result in mapping:
        if any(needle in text for needle in needles):
            return result
    return "Other"



def _validated_isin(value: str) -> str:
    cleaned = _text(value, "ISIN", maximum=12).upper()
    if _ISIN_RE.fullmatch(cleaned) is None:
        raise ProtocolError("Probe ISIN is invalid")
    return cleaned


def _optional_bounded_text(value: Any, field: str, maximum: int) -> str | None:
    if value in (None, ""):
        return None
    return _text(value, field, maximum=maximum)


def _decimal_text(value: Any, field: str, *, maximum: Decimal) -> str:
    if not isinstance(value, (str, int, float, Decimal)) or isinstance(value, bool):
        raise ProtocolError(f"{field} must be a decimal value")
    try:
        number = Decimal(str(value))
    except InvalidOperation as err:
        raise ProtocolError(f"{field} contains an invalid decimal") from err
    if not number.is_finite() or abs(number) > maximum:
        raise ProtocolError(f"{field} is outside the allowed range")
    return format(number.normalize(), "f")


def _public_venues(raw: Any) -> tuple[dict[str, str], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise ProtocolError("Comdirect orderDimensions must be an object")
    venues_raw = raw.get("venues", [])
    if not isinstance(venues_raw, list) or len(venues_raw) > 128:
        raise ProtocolError("Comdirect venue list is malformed or unbounded")
    venues: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in venues_raw:
        if not isinstance(item, dict):
            raise ProtocolError("Comdirect venue list contains a non-object")
        venue_id = _text(item.get("venueId"), "venue ID", maximum=40)
        if venue_id in seen:
            raise ProtocolError("Comdirect venue list contains a duplicate ID")
        seen.add(venue_id)
        name = _text(item.get("name"), "venue name", maximum=80)
        sides = item.get("sides", [])
        order_types = item.get("orderTypes", {})
        currencies = item.get("currencies", [])
        validity_types = item.get("validityTypes", [])
        if not isinstance(sides, list) or any(not isinstance(value, str) for value in sides):
            raise ProtocolError("Comdirect venue sides are malformed")
        if not isinstance(order_types, dict) or any(not isinstance(key, str) for key in order_types):
            raise ProtocolError("Comdirect venue order types are malformed")
        if not isinstance(currencies, list) or any(not isinstance(value, str) for value in currencies):
            raise ProtocolError("Comdirect venue currencies are malformed")
        if not isinstance(validity_types, list) or any(not isinstance(value, str) for value in validity_types):
            raise ProtocolError("Comdirect venue validity types are malformed")
        if sides and "BUY" not in sides:
            continue
        if order_types and "MARKET" not in order_types:
            continue
        if currencies and "EUR" not in currencies:
            continue
        if validity_types and "GFD" not in validity_types:
            continue
        venues.append({
            "venue_id": venue_id,
            "name": name,
            "country": _optional_bounded_text(item.get("country"), "venue country", 8) or "",
            "type": _optional_bounded_text(item.get("type"), "venue type", 16) or "",
        })
    venues.sort(key=lambda item: (item["name"], item["country"], item["venue_id"]))
    return tuple(venues)

def _extract_single_cost_indication(raw: Any) -> dict[str, Any]:
    values = _extract_values(raw, field="cost indication")
    objects = [item for item in values if isinstance(item, dict)]
    if len(objects) != 1 or len(values) != 1:
        raise ProtocolError("Comdirect cost indication response is ambiguous")
    return objects[0]


def _public_amount(raw: Any, field: str) -> dict[str, str] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ProtocolError(f"Comdirect {field} must be an amount object")
    value = _decimal_text(raw.get("value"), field, maximum=Decimal("1000000000"))
    unit = _text(raw.get("unit"), f"{field} currency", maximum=8)
    return {"value": value, "unit": unit}


def _public_currency(raw: Any, field: str) -> str | None:
    if raw is None:
        return None
    value = raw
    if isinstance(raw, dict):
        value = raw.get("Currency", raw.get("currency"))
    return _optional_bounded_text(value, field, 8)


def _strict_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ProtocolError(f"Comdirect {field} must be boolean")
    return value


def _public_percentage(raw: Any, field: str) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        value = raw.get("percentString")
        if value is None:
            before = raw.get("preDecimalPlaces", "0")
            after = raw.get("decimalPlaces", "")
            value = f"{before}.{after}" if after else str(before)
    else:
        value = raw
    return _decimal_text(value, field, maximum=Decimal("1000000"))


def _public_cost_group(
    raw: Any, field: str, *, expected_type: str
) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ProtocolError(f"Comdirect {field} must be an object")
    group_type = _optional_bounded_text(raw.get("type"), "cost group type", 8)
    if group_type not in (None, expected_type):
        raise ProtocolError(f"Comdirect {field} has an unexpected type")
    costs_raw = raw.get("costs", [])
    if not isinstance(costs_raw, list) or len(costs_raw) > 64:
        raise ProtocolError(f"Comdirect {field} costs are malformed or unbounded")
    costs: list[dict[str, Any]] = []
    for entry in costs_raw:
        if not isinstance(entry, dict):
            raise ProtocolError(f"Comdirect {field} contains a non-object cost")
        entry_type = _optional_bounded_text(entry.get("type"), "cost type", 8)
        if entry_type not in (None, "E", "F", "P"):
            raise ProtocolError(f"Comdirect {field} contains an unexpected cost type")
        costs.append({
            "type": entry_type,
            "label": _optional_bounded_text(entry.get("label"), "cost label", 160),
            "amount": _public_amount(entry.get("amount"), "cost amount"),
            "amount_reporting_currency": _public_amount(entry.get("amountReportingCurrency"), "reporting cost amount"),
        })
    return {
        "type": group_type,
        "label": _optional_bounded_text(raw.get("label"), "cost group label", 160),
        "sum": _public_amount(raw.get("sum"), f"{field} sum"),
        "sum_reporting_currency": _public_amount(raw.get("sumReportingCurrency"), f"{field} reporting sum"),
        "costs": costs,
    }

def _sanitize_cost_indication(
    raw: dict[str, Any],
    *,
    requested_depot: str,
    requested_isin: str,
    requested_quantity: str,
    requested_venue: str,
) -> dict[str, Any]:
    returned_depot = _optional_bounded_text(raw.get("depotId"), "cost indication depot ID", 40)
    if returned_depot not in (None, requested_depot):
        raise ProtocolError("Comdirect cost indication returned a different depot")
    side = _optional_bounded_text(raw.get("side"), "cost indication side", 8)
    if side not in (None, "BUY"):
        raise ProtocolError("Comdirect cost indication returned an unexpected side")
    quantity = _public_amount(raw.get("quantity"), "quantity")
    if quantity is not None:
        try:
            returned_quantity = Decimal(quantity["value"])
            expected_quantity = Decimal(requested_quantity)
        except InvalidOperation as err:
            raise ProtocolError("Comdirect cost indication returned an invalid quantity") from err
        if returned_quantity != expected_quantity or quantity["unit"] != "XXX":
            raise ProtocolError("Comdirect cost indication returned a different quantity")
    calculation_successful = _strict_bool(
        raw.get("calculationSuccessful"), "calculationSuccessful"
    )
    purchase_costs = _public_cost_group(
        raw.get("purchaseCosts"), "purchase costs", expected_type="K"
    )
    holding_costs = _public_cost_group(
        raw.get("holdingCosts"), "holding costs", expected_type="H"
    )
    sales_costs = _public_cost_group(
        raw.get("salesCosts"), "sales costs", expected_type="V"
    )
    if calculation_successful and purchase_costs is None:
        raise ProtocolError("Successful Comdirect cost indication lacks purchase costs")
    return {
        "probe_type": "ordinary_order_cost_indication",
        "warning": "No order was validated or submitted. This is not a savings-plan quotation.",
        "requested_isin": requested_isin,
        "requested_quantity": requested_quantity,
        "requested_venue": requested_venue,
        "requested_side": "BUY",
        "requested_order_type": "MARKET",
        "calculation_successful": calculation_successful,
        "instrument_name": _optional_bounded_text(raw.get("name"), "instrument name", 160),
        "wkn": _optional_bounded_text(raw.get("wkn"), "WKN", 16),
        "quantity": quantity,
        "expected_value": _public_amount(raw.get("expectedValue"), "expected value"),
        "venue_name": _optional_bounded_text(raw.get("venueName"), "venue name", 80),
        "settlement_currency": _public_currency(raw.get("settlementCurrency"), "settlement currency"),
        "trading_currency": _public_currency(raw.get("tradingCurrency"), "trading currency"),
        "reporting_currency": _public_currency(raw.get("reportingCurrency"), "reporting currency"),
        "expected_settlement_costs": _public_amount(raw.get("expectedSettlementCosts"), "expected settlement costs"),
        "purchase_costs": purchase_costs,
        "holding_costs": holding_costs,
        "sales_costs": sales_costs,
        "holding_period_years": _optional_bounded_text(raw.get("holdingPeriod"), "holding period", 16),
        "total_costs_abs": _public_amount(raw.get("totalCostsAbs"), "total costs"),
        "total_costs_rel_pct": _public_percentage(raw.get("totalCostsRel"), "relative total costs"),
        "probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

def _signed_amount_eur(raw: Any, *, field: str) -> Decimal:
    """Parse one bounded signed EUR account amount."""
    if not isinstance(raw, dict):
        raise ProtocolError(f"Comdirect {field} must be an amount object")
    unit = raw.get("unit")
    value = raw.get("value")
    if unit != "EUR" or not isinstance(value, str):
        raise ProtocolError(f"Comdirect {field} must contain a EUR decimal string")
    try:
        amount = Decimal(value)
    except InvalidOperation as err:
        raise ProtocolError(f"Comdirect {field} contains an invalid decimal") from err
    if not amount.is_finite() or abs(amount) > Decimal("1000000000"):
        raise ProtocolError(f"Comdirect {field} is outside the allowed range")
    return amount

def _amount_eur(raw: Any, *, field: str) -> Decimal:
    if not isinstance(raw, dict):
        raise ProtocolError(f"Comdirect {field} must be an amount object")
    unit = raw.get("unit")
    value = raw.get("value")
    if unit != "EUR" or not isinstance(value, str):
        raise ProtocolError(f"Comdirect {field} must contain a EUR decimal string")
    try:
        amount = Decimal(value)
    except InvalidOperation as err:
        raise ProtocolError(f"Comdirect {field} contains an invalid decimal") from err
    if not amount.is_finite() or amount < 0 or amount > Decimal("1000000000"):
        raise ProtocolError(f"Comdirect {field} is outside the allowed range")
    return amount


def _first_text(raw: dict[str, Any], keys: tuple[str, ...], field: str) -> str:
    value = _optional_first_text(raw, keys)
    if not value:
        raise ProtocolError(f"Comdirect response lacks {field}")
    return _text(value, field, maximum=128)


def _optional_first_text(raw: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _text(value: Any, field: str, *, maximum: int, required: bool = True) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise ProtocolError(f"{field} must be a string")
    cleaned = value.strip()
    if required and not cleaned:
        raise ProtocolError(f"{field} is empty")
    if len(cleaned) > maximum or any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise ProtocolError(f"{field} is too long or contains control characters")
    return cleaned


def _opaque(value: Any, field: str, *, maximum: int) -> str:
    token = _text(value, field, maximum=maximum)
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in token):
        raise ProtocolError(f"{field} contains whitespace or control characters")
    return token
