"""Offline HKSAL selection, bounded projection, shadow lifecycle and privacy contracts."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib
import importlib.util
import sys

import pytest

PACKAGE = Path(__file__).parents[1] / "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway"
NAME = "portfolio_architect_gateway_dkb_v1652_test"
spec = importlib.util.spec_from_file_location(NAME, PACKAGE / "__init__.py", submodule_search_locations=[str(PACKAGE)])
module = importlib.util.module_from_spec(spec)
sys.modules[NAME] = module
spec.loader.exec_module(module)
cash = importlib.import_module(f"{NAME}.dkb_cash_research")
DKBProbeController = importlib.import_module(f"{NAME}.dkb_app").DKBProbeController


def _balance(amount: str = "281.58", currency: str = "EUR"):
    return SimpleNamespace(amount=SimpleNamespace(amount=Decimal(amount), currency=currency),
                           date=date(2026, 9, 25))


@pytest.fixture
def fake_fints(monkeypatch):
    """Exercise the bank-independent control flow without a PyFinTS install."""
    package = ModuleType("fints")
    package.__path__ = []
    client = ModuleType("fints.client")
    models = ModuleType("fints.models")
    formals = ModuleType("fints.formals")

    class Operations:
        GET_BALANCE = "HKSAL"

    class NeedTANResponse:
        pass

    class SEPAAccount:
        def __init__(self, *args):
            self.fields = args

    class BankIdentifier:
        def __init__(self, country, bank_code):
            self.country = country
            self.bank_code = bank_code

    client.FinTSOperations = Operations
    client.NeedTANResponse = NeedTANResponse
    models.SEPAAccount = SEPAAccount
    formals.BankIdentifier = BankIdentifier
    package.client, package.models, package.formals = client, models, formals
    for name, value in (("fints", package), ("fints.client", client),
                        ("fints.models", models), ("fints.formals", formals)):
        monkeypatch.setitem(sys.modules, name, value)
    return client


def test_booked_balance_projection_rejects_missing_non_eur_and_unbounded_values():
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    assert cash.project_booked_balance(_balance("-12.34"), observed).amount == "-12.34"
    assert cash.project_booked_balance(_balance(currency="USD"), observed) is None
    assert cash.project_booked_balance(_balance("1000000001"), observed) is None
    assert cash.project_booked_balance(SimpleNamespace(amount=None, date=date.today()), observed) is None


def test_exact_account_selection_and_ambiguous_suffix_stop_before_hksal(fake_fints):
    FinTSOperations = fake_fints.FinTSOperations
    calls = []
    account = lambda iban: {
        "iban": iban, "currency": "EUR", "supported_operations": {FinTSOperations.GET_BALANCE: True},
        "bank_identifier": SimpleNamespace(bank_code=cash.DKB_BANK_CODE), "account_number": "111111",
    }
    class Client:
        def __init__(self, accounts): self.accounts = accounts
        def get_information(self): return {"accounts": self.accounts}
        def get_balance(self, value):
            calls.append(value)
            return _balance()
    captured = []
    result, pending = cash._read(Client([account("DE00000000000000001234")]), "1234", captured.append)
    assert result.outcome == "retrieved" and pending is None and len(calls) == 1
    assert captured[0].amount == "281.58"
    result, pending = cash._read(Client([account("DE00000000000000001234"),
                                          account("DE00000000000000011234")]), "1234", captured.append)
    assert result.outcome == "ambiguous_account" and pending is None and len(calls) == 1
    result, pending = cash._read(Client([account("DE00000000000000001234")]), "9999", captured.append)
    assert result.outcome == "account_not_found" and pending is None and len(calls) == 1


def test_decoupled_login_then_one_hksal_response(monkeypatch, fake_fints):
    FinTSOperations = fake_fints.FinTSOperations
    NeedTANResponse = fake_fints.NeedTANResponse
    class Challenge(NeedTANResponse):
        def __init__(self):
            self.decoupled = True
    class Client:
        instances = []
        def __init__(self, *args, **kwargs):
            self.calls = 0
            self.init_tan_response = Challenge()
            self.instances.append(self)
        def fetch_tan_mechanisms(self): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def send_tan(self, challenge, tan):
            assert tan == ""
            return None
        def get_information(self):
            return {"accounts": [{"iban": "DE00000000000000001234", "currency": "EUR",
                    "supported_operations": {FinTSOperations.GET_BALANCE: True},
                    "bank_identifier": SimpleNamespace(bank_code=cash.DKB_BANK_CODE),
                    "account_number": "111111"}]}
        def get_balance(self, account):
            self.calls += 1
            return _balance()
    monkeypatch.setattr(fake_fints, "FinTS3PinTanClient", Client, raising=False)
    values = []
    pending, session = cash.begin_cash_observation("A" * 25, "login", "password", "1234", values.append)
    assert pending.outcome == "approval_pending" and session is not None and not values
    result, session = cash.continue_cash_observation(session, "", values.append)
    assert result.outcome == "retrieved" and session is None
    assert Client.instances[0].calls == 1 and values[0].currency == "EUR"


def test_private_shadow_survives_controller_restart_and_failed_refresh(tmp_path: Path):
    controller = DKBProbeController(tmp_path)
    controller.configure_product_id("A" * 25)
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    balance = cash.BookedBalance("281.58", "EUR", date.today().isoformat(), observed)
    controller._capture_cash([balance], None, cash.CashObservation(observed, "retrieved", 1))
    restarted = DKBProbeController(tmp_path)
    assert restarted.cash_review() is None
    status = restarted.status_document(SimpleNamespace(health_document=lambda version: {}))
    assert status["cash_shadow"]["state"] == "recent_observation"
    assert "281.58" not in str(status)
    controller._capture_cash([], None, cash.CashObservation(observed, "request_failed", 1))
    assert cash.validate_shadow(cash.load_json_state(controller.cash_shadow_file)).amount == "281.58"
    old = datetime.now(timezone.utc) + timedelta(hours=26)
    assert cash.shadow_summary(controller.cash_shadow_file, old)["state"] == "old_observation"
    controller.configure_product_id("B" * 25)
    assert cash.shadow_summary(controller.cash_shadow_file)["state"] == "absent"


def test_private_cash_observation_schema_rejects_amount_or_account_in_status(tmp_path: Path):
    controller = DKBProbeController(tmp_path)
    value = cash.CashObservation(datetime.now(timezone.utc).isoformat(timespec="seconds"), "retrieved", 1)
    cash.save_json_state(controller.cash_research_file, value.as_dict())
    assert controller.cash_observation().outcome == "retrieved"
    raw = cash.load_json_state(controller.cash_research_file)
    raw["account_number"] = "private"
    cash.save_json_state(controller.cash_research_file, raw)
    with pytest.raises(RuntimeError, match="invalid"):
        controller.cash_observation()
