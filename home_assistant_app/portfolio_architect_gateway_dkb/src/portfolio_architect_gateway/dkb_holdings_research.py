"""One-shot, read-only DKB FinTS holdings research; never a portfolio source."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from .dkb_authenticated import _IDENTIFIER, _TAN, _codes, _method
from .dkb_fints import DKB_BANK_CODE, DKB_FINTS_ENDPOINT, normalise_product_id


@dataclass(frozen=True, slots=True)
class HoldingsObservation:
    observed_at: str
    outcome: str
    eligible_accounts: int
    holding_count: int | None
    return_codes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self), "return_codes": list(self.return_codes)}


@dataclass(slots=True)
class HoldingsSession:
    client: Any
    challenge: Any
    decoupled: bool
    stage: str
    started_at: str

    def close(self) -> None:
        try:
            self.client.__exit__(None, None, None)
        except Exception:
            # Bank exception text can contain private challenge/response fields.
            pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _failure(client: Any, outcome: str = "request_failed") -> HoldingsObservation:
    return HoldingsObservation(_now(), outcome, 0, None, _codes(client))


def _summarize(client: Any, value: Any, accounts: int) -> HoldingsObservation:
    if not isinstance(value, (list, tuple)) or len(value) > 256:
        return HoldingsObservation(_now(), "invalid_response", accounts, None, _codes(client))
    return HoldingsObservation(_now(), "retrieved", accounts, len(value), _codes(client))


def _read(client: Any) -> tuple[HoldingsObservation, HoldingsSession | None]:
    from fints.client import FinTSOperations, NeedTANResponse
    from fints.models import SEPAAccount

    info = client.get_information()
    accounts = [a for a in info.get("accounts", ()) if isinstance(a, dict)
                and a.get("supported_operations", {}).get(FinTSOperations.GET_HOLDINGS) is True]
    if len(accounts) != 1:
        # Never guess an account when the user has multiple eligible depots.
        outcome = "no_eligible_account" if not accounts else "multiple_eligible_accounts"
        return HoldingsObservation(_now(), outcome, min(len(accounts), 256), None, _codes(client)), None
    account = accounts[0]
    bank = account.get("bank_identifier")
    code = getattr(bank, "bank_code", None)
    number = account.get("account_number")
    if not isinstance(code, str) or not isinstance(number, str) or not number:
        return HoldingsObservation(_now(), "account_metadata_incomplete", 1, None, _codes(client)), None
    sepa = SEPAAccount(account.get("iban"), None, number,
                       account.get("subaccount_number"), code)
    result = client.get_holdings(sepa)  # Only bank business operation in this module.
    if isinstance(result, NeedTANResponse):
        session = HoldingsSession(client, result, bool(result.decoupled), "holdings", _now())
        return HoldingsObservation(_now(), "approval_pending", 1, None, _codes(client)), session
    return _summarize(client, result, 1), None


def begin_holdings_observation(product_id: str, user_id: str, pin: str) -> tuple[HoldingsObservation, HoldingsSession | None]:
    from fints.client import FinTS3PinTanClient, NeedTANResponse
    from fints.formals import BankIdentifier

    product_id = normalise_product_id(product_id)
    if not isinstance(user_id, str) or not _IDENTIFIER.fullmatch(user_id):
        raise ValueError("Invalid bank user identifier")
    if not isinstance(pin, str) or not 1 <= len(pin) <= 256 or any(ord(c) < 32 for c in pin):
        raise ValueError("Invalid bank password")
    logger = logging.getLogger("fints")
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.CRITICAL + 1)
    client = None
    try:
        client = FinTS3PinTanClient(BankIdentifier("280", DKB_BANK_CODE), user_id, pin,
                                   DKB_FINTS_ENDPOINT, product_id=product_id)
        client.fetch_tan_mechanisms()
        client.__enter__()
        challenge = client.init_tan_response
        if isinstance(challenge, NeedTANResponse):
            session = HoldingsSession(client, challenge, bool(challenge.decoupled), "login", _now())
            return HoldingsObservation(_now(), "approval_pending", 0, None, _codes(client)), session
        observation, session = _read(client)
        if session is None:
            client.__exit__(None, None, None)
        return observation, session
    except Exception:
        result = _failure(client)
        if client is not None:
            HoldingsSession(client, None, False, "login", _now()).close()
        return result, None


def continue_holdings_observation(session: HoldingsSession, tan: str = "") -> tuple[HoldingsObservation, HoldingsSession | None]:
    from fints.client import NeedTANResponse

    if not session.decoupled and (not isinstance(tan, str) or not _TAN.fullmatch(tan)):
        raise ValueError("A bounded login TAN is required")
    try:
        result = session.client.send_tan(session.challenge, "" if session.decoupled else tan)
        if isinstance(result, NeedTANResponse):
            session.challenge = result
            session.decoupled = bool(result.decoupled)
            return HoldingsObservation(_now(), "approval_pending", 0, None, _codes(session.client)), session
        if session.stage == "login":
            observation, pending = _read(session.client)
            if pending is not None:
                pending.started_at = session.started_at
            else:
                session.close()
            return observation, pending
        observation = _summarize(session.client, result, 1)
        session.close()
        return observation, None
    except Exception:
        observation = _failure(session.client)
        session.close()
        return observation, None
