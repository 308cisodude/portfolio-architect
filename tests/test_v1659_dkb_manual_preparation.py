"""DKB account binding, manual refresh and CSV cash authorization contracts."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import importlib
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys

import pytest

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway"
NAME = "portfolio_architect_gateway_dkb_v1659_test"
spec = importlib.util.spec_from_file_location(NAME, PACKAGE / "__init__.py", submodule_search_locations=[str(PACKAGE)])
module = importlib.util.module_from_spec(spec)
sys.modules[NAME] = module
spec.loader.exec_module(module)
selection = importlib.import_module(f"{NAME}.dkb_account_selection")
app = importlib.import_module(f"{NAME}.dkb_app")
cash = importlib.import_module(f"{NAME}.dkb_cash_research")
csv = importlib.import_module(f"{NAME}.dkb_csv")
cash_csv = importlib.import_module(f"{NAME}.dkb_cash_csv")
policy = importlib.import_module(f"{NAME}.dkb_cash_policy")


def _account(n: int) -> dict[str, str]:
    return {"iban": f"DE{n:016d}1234", "account_number": str(n), "bank_code": cash.DKB_BANK_CODE}


def test_fifteen_masked_candidates_bind_one_account_without_persisting_identifiers(tmp_path):
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id("A" * 25)
    controller._account_discovery_user = "banking-login"
    controller._capture_account_candidates(tuple(_account(n) for n in range(1, 16)))
    state, options, _ = controller.account_discovery_view()
    assert state == "ready" and len(options) == 15
    assert len({label.split(" · ")[0] for _, label in options}) == 15
    assert all("DE" not in label for _, label in options)
    chosen = controller.select_account(options[6][0])
    persisted = controller.selected_account_file.read_text()
    assert chosen.suffix == "1234"
    assert "banking-login" not in persisted and "DE" not in persisted
    assert controller.selected_account_file.stat().st_mode & 0o777 == 0o600
    assert controller.account_binding_key_file.stat().st_mode & 0o777 == 0o600
    restored = app.DKBProbeController(tmp_path).selected_account()
    assert restored == chosen
    assert selection.matches(restored, controller.account_binding_key_file,
                             product_id="A" * 25, user_id="banking-login", account=_account(7))
    assert not selection.matches(restored, controller.account_binding_key_file,
                                 product_id="A" * 25, user_id="banking-login", account=_account(8))
    assert not selection.user_matches(restored, controller.account_binding_key_file,
                                      product_id="A" * 25, user_id="another-user")
    assert controller.account_discovery_view()[1] == ()
    controller.configure_product_id("B" * 25)
    assert controller.selected_account() is None


def test_hksal_matches_private_binding_among_colliding_suffixes(monkeypatch, tmp_path):
    package = ModuleType("fints")
    package.__path__ = []
    client = ModuleType("fints.client")
    models = ModuleType("fints.models")
    class Operations:
        GET_BALANCE = "HKSAL"
    class NeedTANResponse:
        pass
    class SEPAAccount:
        def __init__(self, *args):
            self.iban = args[0]
    client.FinTSOperations = Operations
    client.NeedTANResponse = NeedTANResponse
    models.SEPAAccount = SEPAAccount
    for name, value in (("fints", package), ("fints.client", client), ("fints.models", models)):
        monkeypatch.setitem(sys.modules, name, value)
    accounts = [_account(1), _account(2)]
    selected = selection.select(tmp_path / "selection.json", tmp_path / "key", product_id="A" * 25,
                                user_id="login", account=accounts[1])
    def up(a):
        return {**a, "currency": "EUR", "supported_operations": {Operations.GET_BALANCE: True},
                "bank_identifier": SimpleNamespace(bank_code=cash.DKB_BANK_CODE)}
    calls = []
    class Bank:
        def get_information(self): return {"accounts": [up(a) for a in accounts]}
        def get_balance(self, account):
            calls.append(account.iban)
            return SimpleNamespace(amount=SimpleNamespace(amount=Decimal("43.12"), currency="EUR"), date=date.today())
    matcher = lambda a: selection.matches(selected, tmp_path / "key", product_id="A" * 25,
                                          user_id="login", account=a)
    observed, pending = cash._read(Bank(), "1234", None, account_matcher=matcher)
    assert observed.outcome == "retrieved" and pending is None
    assert calls == [accounts[1]["iban"]]


def test_manual_portfolio_refresh_and_timeout(monkeypatch, tmp_path):
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id("A" * 25)
    controller._account_discovery_user = "login"
    controller._capture_account_candidates((_account(1),))
    controller.select_account(next(iter(controller._account_options)))
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    calls = []
    def start_holdings(user, pin, _snapshot):
        calls.append(("holdings", user, pin))
        return app.HoldingsObservation(timestamp, "approval_pending", 1, None)
    def finish_holdings(_tan, _snapshot):
        result = app.HoldingsObservation(timestamp, "retrieved", 1, 1)
        controller._capture_review([(app.ReviewRow("IE00BJ0KDQ92", "2", "281.58", "EUR", "unavailable"),)], None, result)
        return result
    def start_cash(user, pin, suffix, _snapshot):
        calls.append(("cash", user, pin, suffix))
        result = cash.CashObservation(timestamp, "retrieved", 15)
        controller._capture_cash([cash.BookedBalance("430.63", "EUR", date.today().isoformat(), timestamp)], None, result)
        return result
    monkeypatch.setattr(controller, "run_holdings_observation", start_holdings)
    monkeypatch.setattr(controller, "continue_holdings_observation", finish_holdings)
    monkeypatch.setattr(controller, "run_cash_observation", start_cash)
    assert controller.run_portfolio_refresh("login", "secret") == "holdings_pending"
    with pytest.raises(ValueError, match="pending bank refresh"):
        controller.clear_selected_account()
    assert controller.continue_portfolio_refresh() == "complete"
    assert calls == [("holdings", "login", "secret"), ("cash", "login", "secret", "1234")]
    assert controller._portfolio_credentials is None
    assert "secret" not in "".join(p.read_text(errors="ignore") for p in tmp_path.iterdir() if p.is_file())
    assert controller.run_portfolio_refresh("login", "secret") == "holdings_pending"
    controller._expire_portfolio_credentials(controller._portfolio_generation)
    assert controller._portfolio_credentials is None
    assert controller.portfolio_refresh_state() == "expired"


def test_csv_policy_and_gui_without_probe(tmp_path):
    provider = csv.DkbCsvProvider(tmp_path / "portfolio.json")
    snapshot, _ = csv.parse_dkb_csv_batch(((ROOT / "tests/fixtures/dkb-depot.csv").read_bytes(),))
    provider.replace_snapshot(snapshot)
    provider.replace_cash_snapshot(cash_csv.DkbCashSnapshot(Decimal("500"), datetime.now(timezone.utc), datetime.now(timezone.utc)))
    provider.set_investment_cash_policy(policy.InvestmentCashPolicy(mode="capped", cap_eur=Decimal("200")))
    assert provider.snapshot.investment_cash.authorized_eur == Decimal("200")
    controller = app.DKBProbeController(tmp_path)
    gateway = SimpleNamespace(capability_evidence_timestamps=lambda: {"holdings": None, "cash": None})
    handler = object.__new__(app.DKBIngressHandler)
    handler.server = SimpleNamespace(controller=controller, csv_provider=provider,
                                     gateway_state=gateway, api_token="SYNTHETIC", last_import_notice=None)
    body = handler._render_page().decode("utf-8")
    assert "Anonymous BPD capability probe" not in body
    assert "Dedicated investment account" in body
    assert "Refresh portfolio now" in body
    assert "Investment cash authorization" in body
    assert "FinTS preparation never switches authority" in body


def test_selection_does_not_change_during_legacy_cash_challenge(tmp_path):
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id("A" * 25)
    controller._account_discovery_user = "login"
    controller._capture_account_candidates((_account(1),))
    controller._cash_session = object()
    with pytest.raises(ValueError, match="pending bank request"):
        controller.select_account(next(iter(controller._account_options)))
    with pytest.raises(ValueError, match="pending bank request"):
        controller.clear_selected_account()


def test_cash_authorization_modes_keep_negative_balance_at_zero(tmp_path):
    provider = csv.DkbCsvProvider(tmp_path / "portfolio.json")
    snapshot, _ = csv.parse_dkb_csv_batch(((ROOT / "tests/fixtures/dkb-depot.csv").read_bytes(),))
    provider.replace_snapshot(snapshot)
    now = datetime.now(timezone.utc)
    provider.replace_cash_snapshot(cash_csv.DkbCashSnapshot(Decimal("-50"), now, now))
    provider.set_investment_cash_policy(policy.InvestmentCashPolicy(mode="retain", retain_eur=Decimal("200")))
    assert provider.snapshot.investment_cash.authorized_eur == Decimal("0")
    provider.replace_cash_snapshot(cash_csv.DkbCashSnapshot(Decimal("500"), now, now))
    assert provider.snapshot.investment_cash.authorized_eur == Decimal("300")
