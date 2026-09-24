"""DKB authenticated UPD research with App-private, bounded SCA state."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import re
from typing import Any

from .dkb_fints import DKB_BANK_CODE, DKB_FINTS_ENDPOINT, normalise_product_id

_IDENTIFIER = re.compile(r"^[A-Za-z0-9._@-]{1,128}$")
_TAN = re.compile(r"^[A-Za-z0-9]{1,32}$")


@dataclass(frozen=True, slots=True)
class AuthObservation:
    observed_at: str
    outcome: str
    upd_received: bool
    upd_version: int | None
    securities_capability: str
    auth_method: str
    return_codes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self), "return_codes": list(self.return_codes)}


@dataclass(slots=True)
class AuthSession:
    """Transient client and challenge; never serialize or log this object."""
    client: Any
    challenge: Any
    decoupled: bool
    started_at: str

    def close(self) -> None:
        try:
            self.client.__exit__(None, None, None)
        except Exception:
            # Even close failures can contain bank/account/challenge payloads.
            pass


def _codes(client: object | None) -> tuple[str, ...]:
    result: list[str] = []
    try:
        for messages in getattr(getattr(client, "_standing_dialog", None), "messages", {}).values():
            for message in messages.values():
                for segment in message.find_segments("HIRMG", "HIRMS"):
                    for response in segment.responses:
                        code = response.code
                        if isinstance(code, str) and re.fullmatch(r"[0-9]{4}", code) and code not in result:
                            result.append(code)
                            if len(result) == 32:
                                return tuple(result)
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return tuple(result)


def _method(client: Any) -> str:
    value = client.get_current_tan_mechanism()
    return value if isinstance(value, str) and re.fullmatch(r"[0-9]{1,4}", value) else "unknown"


def _project(client: Any, timestamp: str) -> AuthObservation:
    from fints.client import FinTSOperations
    info = client.get_information()  # In-memory BPD/UPD only; no bank command.
    version = client.upd_version if client.upa is not None else None
    accounts = info.get("accounts", ())
    if version is None or not accounts:
        capability = "unknown"
    else:
        support = [account.get("supported_operations", {}).get(FinTSOperations.GET_HOLDINGS)
                   for account in accounts]
        capability = "yes" if True in support else ("no" if all(v is False for v in support) else "unknown")
    return AuthObservation(timestamp, "authenticated", version is not None, version,
                           capability, _method(client), _codes(client))


def _failure(client: Any, timestamp: str, err: BaseException) -> AuthObservation:
    names: set[str] = set()
    current: BaseException | None = err
    for _ in range(4):
        if current is None:
            break
        names.add(type(current).__name__)
        current = current.__cause__
    outcome = "sca_required" if names & {"FinTSSCARequiredError", "FinTSTANRequiredError"} else "authentication_failed"
    # Never render, persist or log exception text, credential, UPD or account data.
    return AuthObservation(timestamp, outcome, False, None, "unknown", "unknown", _codes(client))


def begin_authenticated_observation(product_id: str, user_id: str, pin: str) -> tuple[AuthObservation, AuthSession | None]:
    product_id = normalise_product_id(product_id)
    if not isinstance(user_id, str) or not _IDENTIFIER.fullmatch(user_id):
        raise ValueError("Invalid FinTS user identifier")
    if not isinstance(pin, str) or not 1 <= len(pin) <= 256 or any(ord(c) < 32 for c in pin):
        raise ValueError("Invalid FinTS PIN")

    # PyFinTS logs bank response text/parameters. Confine its entire logger tree.
    logger = logging.getLogger("fints")
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.CRITICAL + 1)
    from fints.client import FinTS3PinTanClient, NeedTANResponse
    from fints.formals import BankIdentifier

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    client = None
    try:
        client = FinTS3PinTanClient(BankIdentifier("280", DKB_BANK_CODE), user_id, pin,
                                   DKB_FINTS_ENDPOINT, product_id=product_id)
        # Discover the bank-approved mechanism before the actual user dialog.
        client.fetch_tan_mechanisms()
        client.__enter__()
        challenge = client.init_tan_response
        if isinstance(challenge, NeedTANResponse):
            session = AuthSession(client, challenge, bool(challenge.decoupled), timestamp)
            return AuthObservation(timestamp, "approval_pending", False, None, "unknown",
                                   _method(client), _codes(client)), session
        observation = _project(client, timestamp)
        client.__exit__(None, None, None)
        return observation, None
    except Exception as err:
        observation = _failure(client, timestamp, err)
        if client is not None:
            AuthSession(client, None, False, timestamp).close()
        return observation, None


def continue_authenticated_observation(session: AuthSession, tan: str = "") -> tuple[AuthObservation, AuthSession | None]:
    if not session.decoupled and (not isinstance(tan, str) or not _TAN.fullmatch(tan)):
        raise ValueError("A bounded TAN is required")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    from fints.client import NeedTANResponse
    try:
        result = session.client.send_tan(session.challenge, "" if session.decoupled else tan)
        if isinstance(result, NeedTANResponse):
            session.challenge = result
            session.decoupled = bool(result.decoupled)
            return AuthObservation(timestamp, "approval_pending", False, None, "unknown",
                                   _method(session.client), _codes(session.client)), session
        observation = _project(session.client, timestamp)
        session.close()
        return observation, None
    except Exception as err:
        observation = _failure(session.client, timestamp, err)
        session.close()
        return observation, None
