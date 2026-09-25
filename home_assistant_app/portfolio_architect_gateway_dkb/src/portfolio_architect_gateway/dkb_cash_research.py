"""One-shot DKB HKSAL booked-balance research; CSV remains authoritative."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import logging
import re
from pathlib import Path
from typing import Any, Callable

from .dkb_authenticated import _IDENTIFIER, _TAN, _codes
from .dkb_fints import DKB_BANK_CODE, DKB_FINTS_ENDPOINT, normalise_product_id
from .dkb_holdings_research import DKB_BIC
from .errors import ProtocolError
from .store import load_json_state, save_json_state

_IBAN = re.compile(r"DE[0-9]{20}\Z")
_SUFFIX = re.compile(r"[0-9]{4}\Z")
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]{0,9})(?:\.[0-9]{1,12})?\Z")
_MAX_AMOUNT = Decimal("1000000000")
_MAX_AGE = timedelta(hours=24)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class CashObservation:
    observed_at: str
    outcome: str
    eligible_accounts: int | None
    return_codes: tuple[str, ...] = ()
    failure_stage: str | None = None
    failure_kind: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self), "return_codes": list(self.return_codes)}


@dataclass(frozen=True, slots=True)
class BookedBalance:
    amount: str
    currency: str
    bank_date: str
    observed_at: str

    def as_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


@dataclass(slots=True)
class CashSession:
    client: Any
    challenge: Any
    decoupled: bool
    stage: str
    started_at: str
    suffix: str
    eligible_accounts: int | None = None

    def close(self) -> None:
        try:
            self.client.__exit__(None, None, None)
        except Exception:
            pass  # Exception text may contain account or challenge detail.


def _failure(client: Any, stage: str, error: BaseException,
             accounts: int | None = None) -> CashObservation:
    kinds = {TimeoutError: "timeout", ConnectionError: "transport", OSError: "transport",
             AttributeError: "attribute_error", TypeError: "type_error", KeyError: "key_error",
             ValueError: "value_error", NotImplementedError: "unsupported"}
    kind = next((label for cls, label in kinds.items() if isinstance(error, cls)), "unclassified")
    return CashObservation(_now(), "request_failed", accounts, _codes(client), stage, kind)


def project_booked_balance(value: Any, observed_at: str) -> BookedBalance | None:
    """Accept only the explicit booked amount, EUR and bank date; never overdraft."""
    wrapper = getattr(value, "amount", None)
    amount = getattr(wrapper, "amount", None)
    currency = getattr(wrapper, "currency", None)
    bank_date = getattr(value, "date", None)
    if type(amount) is not Decimal or currency != "EUR" or type(bank_date) is not date:
        return None
    if not amount.is_finite() or abs(amount) > _MAX_AMOUNT:
        return None
    result = BookedBalance(format(amount, "f"), "EUR", bank_date.isoformat(), observed_at)
    try:
        validate_shadow(result.as_dict())
    except ValueError:
        return None
    return result


def validate_shadow(raw: dict[str, Any], now: datetime | None = None) -> BookedBalance:
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "amount", "currency", "bank_date", "observed_at"} or type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ValueError("invalid cash shadow schema")
    if raw["currency"] != "EUR" or not isinstance(raw["amount"], str) or not _NUMBER.fullmatch(raw["amount"]):
        raise ValueError("invalid cash shadow amount")
    try:
        amount = Decimal(raw["amount"])
        bank_date = date.fromisoformat(raw["bank_date"])
        observed = datetime.fromisoformat(raw["observed_at"])
    except (InvalidOperation, TypeError, ValueError) as err:
        raise ValueError("invalid cash shadow date") from err
    if abs(amount) > _MAX_AMOUNT or observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("invalid cash shadow evidence")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if observed.astimezone(timezone.utc) > current + timedelta(minutes=5) or bank_date > (current + timedelta(days=1)).date():
        raise ValueError("future cash shadow evidence")
    return BookedBalance(raw["amount"], "EUR", bank_date.isoformat(), observed.astimezone(timezone.utc).isoformat(timespec="seconds"))


def save_shadow(path: Path, value: BookedBalance) -> None:
    save_json_state(path, validate_shadow(value.as_dict()).as_dict())


def shadow_summary(path: Path, now: datetime | None = None) -> dict[str, Any]:
    try:
        raw = load_json_state(path)
        if raw is None:
            return {"state": "absent", "observed_at": None, "bank_date": None}
        value = validate_shadow(raw, now)
    except (ValueError, OSError, ProtocolError):
        return {"state": "invalid", "observed_at": None, "bank_date": None}
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age = current - datetime.fromisoformat(value.observed_at)
    state = "recent_observation" if timedelta(0) <= age < _MAX_AGE else "old_observation"
    return {"state": state, "observed_at": value.observed_at, "bank_date": value.bank_date}


def _summarize(client: Any, value: Any, count: int,
               capture: Callable[[BookedBalance], None] | None) -> CashObservation:
    timestamp = _now()
    projected = project_booked_balance(value, timestamp)
    if projected is None:
        return CashObservation(timestamp, "invalid_balance", count, _codes(client))
    if capture is not None:
        capture(projected)
    return CashObservation(timestamp, "retrieved", count, _codes(client))


def _read(client: Any, suffix: str, capture: Callable[[BookedBalance], None] | None
          ) -> tuple[CashObservation, CashSession | None]:
    from fints.client import FinTSOperations, NeedTANResponse
    from fints.models import SEPAAccount
    stage = "account_discovery"
    eligible: int | None = None
    try:
        info = client.get_information()
        accounts = info.get("accounts", ())
        if not isinstance(accounts, (list, tuple)) or len(accounts) > 256:
            return CashObservation(_now(), "invalid_account_list", None, _codes(client)), None
        candidates = [a for a in accounts if isinstance(a, dict) and a.get("currency") == "EUR"
                      and isinstance(a.get("supported_operations"), dict)
                      and a["supported_operations"].get(FinTSOperations.GET_BALANCE) is True]
        eligible = len(candidates)
        matches = [a for a in candidates if isinstance(a.get("iban"), str)
                   and _IBAN.fullmatch(a["iban"]) and a["iban"].endswith(suffix)]
        if len(matches) != 1:
            outcome = "account_not_found" if not matches else "ambiguous_account"
            return CashObservation(_now(), outcome, eligible, _codes(client)), None
        stage = "account_metadata"
        account = matches[0]
        bank = account.get("bank_identifier")
        code = getattr(bank, "bank_code", None)
        number = account.get("account_number")
        if code != DKB_BANK_CODE or not isinstance(number, str) or not number:
            return CashObservation(_now(), "account_metadata_incomplete", eligible, _codes(client)), None
        sepa = SEPAAccount(account["iban"], DKB_BIC, number,
                           account.get("subaccount_number"), code)
        stage = "balance_request"
        value = client.get_balance(sepa)  # Exactly one read-only HKSAL request.
        if isinstance(value, NeedTANResponse):
            session = CashSession(client, value, bool(value.decoupled), "balance", _now(), suffix, eligible)
            return CashObservation(_now(), "approval_pending", eligible, _codes(client)), session
        stage = "response_summary"
        return _summarize(client, value, eligible, capture), None
    except Exception as err:
        return _failure(client, stage, err, eligible), None


def begin_cash_observation(product_id: str, user_id: str, pin: str, suffix: str,
                           capture: Callable[[BookedBalance], None] | None = None
                           ) -> tuple[CashObservation, CashSession | None]:
    from fints.client import FinTS3PinTanClient, NeedTANResponse
    from fints.formals import BankIdentifier
    product_id = normalise_product_id(product_id)
    if not isinstance(user_id, str) or not _IDENTIFIER.fullmatch(user_id):
        raise ValueError("Invalid bank user identifier")
    if not isinstance(pin, str) or not 1 <= len(pin) <= 256 or any(ord(c) < 32 for c in pin):
        raise ValueError("Invalid bank password")
    if not isinstance(suffix, str) or not _SUFFIX.fullmatch(suffix):
        raise ValueError("Four Girokonto IBAN digits required")
    logger = logging.getLogger("fints")
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.CRITICAL + 1)
    client = None
    stage = "client_creation"
    try:
        client = FinTS3PinTanClient(BankIdentifier("280", DKB_BANK_CODE), user_id, pin,
                                   DKB_FINTS_ENDPOINT, product_id=product_id)
        stage = "tan_mechanisms"
        client.fetch_tan_mechanisms()
        stage = "login_dialog"
        client.__enter__()
        challenge = client.init_tan_response
        if isinstance(challenge, NeedTANResponse):
            session = CashSession(client, challenge, bool(challenge.decoupled), "login", _now(), suffix)
            return CashObservation(_now(), "approval_pending", None, _codes(client)), session
        observation, session = _read(client, suffix, capture)
        if session is None:
            client.__exit__(None, None, None)
        return observation, session
    except Exception as err:
        result = _failure(client, stage, err)
        if client is not None:
            CashSession(client, None, False, "login", _now(), suffix).close()
        return result, None


def continue_cash_observation(session: CashSession, tan: str = "",
                              capture: Callable[[BookedBalance], None] | None = None
                              ) -> tuple[CashObservation, CashSession | None]:
    from fints.client import NeedTANResponse
    if not session.decoupled and (not isinstance(tan, str) or not _TAN.fullmatch(tan)):
        raise ValueError("A bounded TAN is required")
    stage = "login_approval" if session.stage == "login" else "balance_approval"
    try:
        value = session.client.send_tan(session.challenge, "" if session.decoupled else tan)
        if isinstance(value, NeedTANResponse):
            session.challenge = value
            session.decoupled = bool(value.decoupled)
            return CashObservation(_now(), "approval_pending", session.eligible_accounts, _codes(session.client)), session
        if session.stage == "login":
            observation, pending = _read(session.client, session.suffix, capture)
            if pending is None:
                session.close()
            else:
                pending.started_at = session.started_at
            return observation, pending
        observation = _summarize(session.client, value, session.eligible_accounts or 1, capture)
        session.close()
        return observation, None
    except Exception as err:
        result = _failure(session.client, stage, err)
        session.close()
        return result, None
