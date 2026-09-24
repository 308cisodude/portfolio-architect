"""Bounded DKB holdings research and privacy boundary."""
from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway"
NAME = "portfolio_architect_gateway_dkb_v1641_test"
PRODUCT = "9FA6681DEC0CF3046BFC2F8A6"


def modules():
    if NAME not in sys.modules:
        spec = importlib.util.spec_from_file_location(NAME, PACKAGE / "__init__.py", submodule_search_locations=[str(PACKAGE)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[NAME] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f"{NAME}.dkb_holdings_research"), importlib.import_module(f"{NAME}.dkb_app")


def fake_fints(monkeypatch, client_type):
    package = ModuleType("fints")
    package.__path__ = []
    client = ModuleType("fints.client")
    formals = ModuleType("fints.formals")
    models = ModuleType("fints.models")
    class Operations:
        GET_HOLDINGS = "HKWPD"
    class Challenge:
        decoupled = True
    client.FinTSOperations = Operations
    client.NeedTANResponse = Challenge
    client.FinTS3PinTanClient = client_type
    formals.BankIdentifier = lambda country, code: (country, code)
    models.SEPAAccount = lambda *args: args
    for name, module in (("fints", package), ("fints.client", client), ("fints.formals", formals), ("fints.models", models)):
        monkeypatch.setitem(sys.modules, name, module)
    return Operations, Challenge


def test_login_approval_fetches_one_depot_without_persisting_holdings(monkeypatch, tmp_path):
    research, app = modules()
    calls = []
    class Client:
        _standing_dialog = None
        def __init__(self, _bank, user, pin, endpoint, **kwargs):
            assert (user, pin, kwargs["product_id"]) == ("test.user", "PRIVATE-PASSWORD", PRODUCT)
            calls.append("created")
        def fetch_tan_mechanisms(self): pass
        def __enter__(self):
            self.init_tan_response = Challenge()
            return self
        def __exit__(self, *_args): calls.append("closed")
        def get_current_tan_mechanism(self): return "940"
        def send_tan(self, _challenge, tan):
            assert tan == ""
            calls.append("approved")
            return object()
        def get_information(self):
            return {"accounts": [{"iban": "DE00123456789012345678", "account_number": "ACCOUNT-123",
                                  "bank_identifier": type("Bank", (), {"bank_code": "12030000"})(),
                                  "supported_operations": {Operations.GET_HOLDINGS: True}}]}
        def get_holdings(self, account):
            assert account[2] == "ACCOUNT-123"
            assert account[1] == research.DKB_BIC
            calls.append("holdings")
            return [type("Holding", (), {"ISIN": "PRIVATE-ISIN"})()]
    Operations, Challenge = fake_fints(monkeypatch, Client)
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT)
    assert controller.run_holdings_observation("test.user", "PRIVATE-PASSWORD").outcome == "approval_pending"
    assert not controller.holdings_state_file.exists()
    result = controller.continue_holdings_observation()
    assert (result.outcome, result.eligible_accounts, result.holding_count) == ("retrieved", 1, 1)
    assert calls == ["created", "approved", "holdings", "closed"]
    persisted = controller.holdings_state_file.read_text()
    for secret in ("PRIVATE-PASSWORD", "test.user", "DE00123456789012345678", "ACCOUNT-123", "PRIVATE-ISIN"):
        assert secret not in persisted
    assert controller.holdings_observation() == result


def test_multiple_eligible_depots_stop_before_holdings_request(monkeypatch, tmp_path):
    research, app = modules()
    class Client:
        _standing_dialog = None
        init_tan_response = None
        def __init__(self, *_args, **_kwargs): pass
        def fetch_tan_mechanisms(self): pass
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def get_information(self):
            return {"accounts": [{"supported_operations": {Operations.GET_HOLDINGS: True}}] * 2}
        def get_holdings(self, account):
            pytest.fail("Multiple depots must not trigger HKWPD")
    Operations, _ = fake_fints(monkeypatch, Client)
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT)
    result = controller.run_holdings_observation("valid", "PRIVATE-PASSWORD")
    assert (result.outcome, result.eligible_accounts, result.holding_count) == ("multiple_eligible_accounts", 2, None)


def test_research_source_contains_only_one_business_request():
    source = (PACKAGE / "dkb_holdings_research.py").read_text()
    assert source.count("client.get_holdings(") == 1
    for forbidden in ("get_balance(", "get_transactions(", "sepa_transfer(", "sepa_debit("):
        assert forbidden not in source


@pytest.mark.parametrize("failing_stage,expected_stage,expected_kind", [
    ("approval", "login_approval", "timeout"),
    ("account", "account_discovery", "attribute_error"),
    ("holdings", "holdings_request", "type_error"),
])
def test_failure_stage_is_bounded_and_private(monkeypatch, tmp_path, failing_stage, expected_stage, expected_kind):
    research, app = modules()
    class Client:
        _standing_dialog = None
        def __init__(self, *_args, **_kwargs): pass
        def fetch_tan_mechanisms(self): pass
        def __enter__(self):
            self.init_tan_response = Challenge()
            return self
        def __exit__(self, *_args): pass
        def send_tan(self, *_args):
            if failing_stage == "approval":
                raise TimeoutError("PRIVATE-ACCOUNT")
            return object()
        def get_information(self):
            if failing_stage == "account":
                raise AttributeError("PRIVATE-ACCOUNT")
            return {"accounts": [{"iban": "DE00123456789012345678", "account_number": "ACCOUNT-123",
                                  "bank_identifier": type("Bank", (), {"bank_code": "12030000"})(),
                                  "supported_operations": {Operations.GET_HOLDINGS: True}}]}
        def get_holdings(self, _account):
            raise TypeError("PRIVATE-ISIN")
    Operations, Challenge = fake_fints(monkeypatch, Client)
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT)
    assert controller.run_holdings_observation("valid", "PRIVATE-PASSWORD").outcome == "approval_pending"
    result = controller.continue_holdings_observation()
    assert (result.outcome, result.failure_stage, result.failure_kind) == (
        "request_failed", expected_stage, expected_kind
    )
    assert result.eligible_accounts == (1 if failing_stage == "holdings" else None)
    persisted = controller.holdings_state_file.read_text()
    for secret in ("PRIVATE-PASSWORD", "PRIVATE-ACCOUNT", "ACCOUNT-123", "DE00123456789012345678", "PRIVATE-ISIN"):
        assert secret not in persisted
    assert controller.holdings_observation() == result


def test_legacy_failed_observation_does_not_claim_zero_eligible_depots(tmp_path):
    _, app = modules()
    controller = app.DKBProbeController(tmp_path)
    controller.holdings_state_file.write_text(json.dumps({
        "schema_version": 1, "observed_at": "2026-09-24T16:03:52+00:00",
        "outcome": "request_failed", "eligible_accounts": 0,
        "holding_count": None, "return_codes": [],
    }))
    result = controller.holdings_observation()
    assert result.eligible_accounts is None
    assert result.failure_stage is None


def test_pinned_pyfints_hkwpd_account_conversion_needs_bic():
    """Offline proof of the v1.64.2 failure when PyFinTS is installed."""
    pytest.importorskip("fints")
    from fints.formals import Account2, Account3
    from fints.models import SEPAAccount

    research, _ = modules()
    old = SEPAAccount(None, None, "SYNTHETIC-DEPOT", None, "12030000")
    corrected = old._replace(bic=research.DKB_BIC)
    for account_type in (Account2, Account3):
        with pytest.raises(TypeError):
            account_type.from_sepa_account(old)
        converted = account_type.from_sepa_account(corrected)
        assert converted.account_number == "SYNTHETIC-DEPOT"
