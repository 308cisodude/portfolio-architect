"""One-shot, read-only DKB FinTS holdings research; never a portfolio source."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Callable

from .dkb_authenticated import _IDENTIFIER, _TAN, _codes, _method
from .dkb_fints import DKB_BANK_CODE, DKB_FINTS_ENDPOINT, normalise_product_id
from .dkb_holdings_review import ReviewRow, project_fints, project_raw_hiwpd

# DKB's published BIC for BLZ 12030000. PyFinTS 5.0.0 uses its country
# component when converting SEPAAccount to HKWPD5/6 Account2/3. The UPD
# get_information() projection has no BIC; passing None raises TypeError.
# Account2/3 transmit the verified account number and bank identifier, not BIC.
DKB_BIC = "BYLADEM1001"


@dataclass(frozen=True, slots=True)
class HoldingsObservation:
    observed_at: str
    outcome: str
    eligible_accounts: int | None
    holding_count: int | None
    return_codes: tuple[str, ...] = ()
    failure_stage: str | None = None
    failure_kind: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {"schema_version": 2, **asdict(self), "return_codes": list(self.return_codes)}


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
        _clear_raw_hook(self.client)


def _clear_raw_hook(client: Any) -> None:
    if client is None:
        return
    if hasattr(client, "_pa_hiwpd_evidence"):
        del client._pa_hiwpd_evidence
    if "_fetch_with_touchdowns" in vars(client) and getattr(client, "_pa_raw_hook", False):
        processor = getattr(client, "_touchdown_response_processor", None)
        if getattr(processor, "_pa_observe", False):
            client._touchdown_response_processor = None
            client._touchdown_responses = []
        del client._fetch_with_touchdowns
        del client._pa_raw_hook


def _install_raw_hook(client: Any) -> None:
    """Observe only this client's HIWPD response before PyFinTS projects it.

    PyFinTS 5.0.0 drops the HOLD currency and narrowly parses 35B. This
    instance-local processor wrapper never retains the response or changes it.
    """
    original = getattr(client, "_fetch_with_touchdowns", None)
    if original is None:
        return  # Small offline test doubles may expose only get_holdings.

    def fetch(dialog: Any, segment_factory: Any, processor: Any, *args: Any, **kwargs: Any) -> Any:
        if args != ("HIWPD",):
            return original(dialog, segment_factory, processor, *args, **kwargs)

        def observe(responses: Any) -> Any:
            client._pa_hiwpd_evidence = project_raw_hiwpd(responses)
            return processor(responses)
        observe._pa_observe = True

        return original(dialog, segment_factory, observe, *args, **kwargs)

    client._fetch_with_touchdowns = fetch
    client._pa_raw_hook = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _failure(client: Any, stage: str, err: BaseException,
             accounts: int | None = None) -> HoldingsObservation:
    # Fixed labels only. Exception messages and bank response payloads may contain
    # credentials, account numbers, positions or challenge text.
    if isinstance(err, TimeoutError):
        kind = "timeout"
    elif isinstance(err, (ConnectionError, OSError)):
        kind = "transport"
    elif isinstance(err, AttributeError):
        kind = "attribute_error"
    elif isinstance(err, TypeError):
        kind = "type_error"
    elif isinstance(err, KeyError):
        kind = "key_error"
    elif isinstance(err, ValueError):
        kind = "value_error"
    elif isinstance(err, NotImplementedError):
        kind = "unsupported"
    else:
        kind = "unclassified"
    return HoldingsObservation(_now(), "request_failed", accounts, None,
                               _codes(client), stage, kind)


def _summarize(client: Any, value: Any, accounts: int,
               capture: Callable[[tuple[ReviewRow, ...]], None] | None = None) -> HoldingsObservation:
    if not isinstance(value, (list, tuple)) or len(value) > 256:
        return HoldingsObservation(_now(), "invalid_response", accounts, None, _codes(client))
    if capture is not None:
        rows = project_fints(value, getattr(client, "_pa_hiwpd_evidence", None))
        if hasattr(client, "_pa_hiwpd_evidence"):
            del client._pa_hiwpd_evidence
        if rows is not None:
            capture(rows)
    return HoldingsObservation(_now(), "retrieved", accounts, len(value), _codes(client))


def _read(client: Any, capture: Callable[[tuple[ReviewRow, ...]], None] | None = None
          ) -> tuple[HoldingsObservation, HoldingsSession | None]:
    from fints.client import FinTSOperations, NeedTANResponse
    from fints.models import SEPAAccount

    stage = "account_discovery"
    eligible: int | None = None
    try:
        info = client.get_information()
        accounts = [a for a in info.get("accounts", ()) if isinstance(a, dict)
                    and a.get("supported_operations", {}).get(FinTSOperations.GET_HOLDINGS) is True]
        eligible = min(len(accounts), 256)
        if len(accounts) != 1:
            # Never guess an account when the user has multiple eligible depots.
            outcome = "no_eligible_account" if not accounts else "multiple_eligible_accounts"
            return HoldingsObservation(_now(), outcome, eligible, None, _codes(client)), None
        stage = "account_metadata"
        account = accounts[0]
        bank = account.get("bank_identifier")
        code = getattr(bank, "bank_code", None)
        number = account.get("account_number")
        if code != DKB_BANK_CODE or not isinstance(number, str) or not number:
            return HoldingsObservation(_now(), "account_metadata_incomplete", 1, None, _codes(client)), None
        sepa = SEPAAccount(account.get("iban"), DKB_BIC, number,
                           account.get("subaccount_number"), code)
        stage = "holdings_request"
        result = client.get_holdings(sepa)  # Only bank business operation in this module.
        if isinstance(result, NeedTANResponse):
            session = HoldingsSession(client, result, bool(result.decoupled), "holdings", _now())
            return HoldingsObservation(_now(), "approval_pending", 1, None, _codes(client)), session
        stage = "response_summary"
        return _summarize(client, result, 1, capture), None
    except Exception as err:
        return _failure(client, stage, err, eligible), None


def begin_holdings_observation(product_id: str, user_id: str, pin: str,
                               capture: Callable[[tuple[ReviewRow, ...]], None] | None = None
                               ) -> tuple[HoldingsObservation, HoldingsSession | None]:
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
    stage = "client_creation"
    try:
        stage = "client_creation"
        client = FinTS3PinTanClient(BankIdentifier("280", DKB_BANK_CODE), user_id, pin,
                                   DKB_FINTS_ENDPOINT, product_id=product_id)
        _install_raw_hook(client)
        stage = "tan_mechanisms"
        client.fetch_tan_mechanisms()
        stage = "login_dialog"
        client.__enter__()
        challenge = client.init_tan_response
        if isinstance(challenge, NeedTANResponse):
            session = HoldingsSession(client, challenge, bool(challenge.decoupled), "login", _now())
            return HoldingsObservation(_now(), "approval_pending", None, None, _codes(client)), session
        observation, session = _read(client, capture)
        if session is None:
            client.__exit__(None, None, None)
            _clear_raw_hook(client)
        return observation, session
    except Exception as err:
        result = _failure(client, stage, err)
        if client is not None:
            HoldingsSession(client, None, False, "login", _now()).close()
        return result, None


def continue_holdings_observation(session: HoldingsSession, tan: str = "",
                                  capture: Callable[[tuple[ReviewRow, ...]], None] | None = None
                                  ) -> tuple[HoldingsObservation, HoldingsSession | None]:
    from fints.client import NeedTANResponse

    if not session.decoupled and (not isinstance(tan, str) or not _TAN.fullmatch(tan)):
        raise ValueError("A bounded login TAN is required")
    stage = "login_approval" if session.stage == "login" else "holdings_approval"
    try:
        result = session.client.send_tan(session.challenge, "" if session.decoupled else tan)
        if isinstance(result, NeedTANResponse):
            session.challenge = result
            session.decoupled = bool(result.decoupled)
            return HoldingsObservation(_now(), "approval_pending", None if session.stage == "login" else 1,
                                       None, _codes(session.client)), session
        if session.stage == "login":
            observation, pending = _read(session.client, capture)
            if pending is not None:
                pending.started_at = session.started_at
            else:
                session.close()
            return observation, pending
        observation = _summarize(session.client, result, 1, capture)
        session.close()
        return observation, None
    except Exception as err:
        observation = _failure(session.client, stage, err, 1 if session.stage == "holdings" else None)
        session.close()
        return observation, None
