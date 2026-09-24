"""Bounded DKB holdings research and privacy boundary."""
from __future__ import annotations

import importlib
import importlib.util
import json
from datetime import datetime, date, timezone
from decimal import Decimal
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
            return [type("Holding", (), {"ISIN": "IE00BJ0KDQ92", "pieces": 1.5,
                                          "total_value": 42.0, "valuation_date": date(2026, 9, 24)})()]
    Operations, Challenge = fake_fints(monkeypatch, Client)
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT)
    models = importlib.import_module(f"{NAME}.models")
    csv = models.PortfolioSnapshot(
        generated_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
        positions=(models.Position("A12345", "Synthetic", Decimal("40"),
                                   Decimal("1.5"), "IE00BJ0KDQ92", "etf"),),
    )
    assert controller.run_holdings_observation("test.user", "PRIVATE-PASSWORD", csv).outcome == "approval_pending"
    assert not controller.holdings_state_file.exists()
    result = controller.continue_holdings_observation(csv_snapshot=csv)
    assert (result.outcome, result.eligible_accounts, result.holding_count) == ("retrieved", 1, 1)
    assert calls == ["created", "approved", "holdings", "closed"]
    persisted = controller.holdings_state_file.read_text()
    for secret in ("PRIVATE-PASSWORD", "test.user", "DE00123456789012345678", "ACCOUNT-123", "IE00BJ0KDQ92"):
        assert secret not in persisted
    assert controller.holdings_observation() == result
    review = controller.holdings_review()
    assert review is not None
    assert review.csv_rows[0].value == "40"
    assert review.fints_rows[0].quantity == "1.5"
    assert review.fints_rows[0].value == "42.0"
    assert review.fints_rows[0].currency == "unavailable"
    assert "IE00BJ0KDQ92" in importlib.import_module(f"{NAME}.dkb_holdings_review").render_review(review)
    assert "IE00BJ0KDQ92" not in json.dumps(controller.holdings_observation().as_dict())
    controller._review_deadline = 0
    assert controller.holdings_review() is None
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


def test_transient_review_rejects_unbounded_and_untrusted_fields():
    review_module = importlib.import_module(f"{NAME}.dkb_holdings_review")
    hostile = type("Holding", (), {"ISIN": "<script>bad</script>", "pieces": float("nan"),
                                   "total_value": float("inf"), "valuation_date": "not a date"})()
    rows = review_module.project_fints([hostile])
    assert rows[0].isin == rows[0].quantity == rows[0].value == "unavailable"
    assert "script" not in review_module.render_review(
        review_module.HoldingsReview(None, "2026-09-24T17:29:55+00:00", None, rows))
    assert review_module.project_fints([hostile] * (review_module.MAX_REVIEW_ROWS + 1)) is None


def test_raw_hiwpd_instrument_and_total_currency_are_transient_and_independent():
    review_module = importlib.import_module(f"{NAME}.dkb_holdings_review")
    payload = ("\r\n:16R:FIN\r\n:35B:/DE/WKN123456|Synthetic ETF\r\n"
               ":19A::HOLD//EUR282,85\r\n:16S:FIN\r\n")
    raw = review_module.project_raw_hiwpd([type("Response", (), {"holdings": payload.encode()})()])
    assert raw == (review_module.RawPositionEvidence("/DE/WKN123456|Synthetic ETF", "EUR"),)
    holding = type("Holding", (), {"ISIN": None, "pieces": 2.0, "total_value": 282.85,
                                   "value_symbol": "USD", "valuation_date": None})()
    rows = review_module.project_fints([holding], raw)
    assert (rows[0].isin, rows[0].instrument_line, rows[0].currency,
            rows[0].unit_price_currency) == ("unavailable", "/DE/WKN123456|Synthetic ETF", "EUR", "USD")
    html = review_module.render_review(review_module.HoldingsReview(None, "2026-09-24T18:29:14+00:00", None, rows))
    assert "/DE/WKN123456|Synthetic ETF" in html
    assert "Unit price currency" in html


def test_raw_hiwpd_bounds_escape_and_unaligned_evidence():
    review_module = importlib.import_module(f"{NAME}.dkb_holdings_review")
    response = type("Response", (), {"holdings": ":16R:FIN\n:35B:<script>alert(1)</script>\n"
                                                ":19A::HOLD//EUR9,00\n:16S:FIN"})()
    raw = review_module.project_raw_hiwpd([response])
    holding = type("Holding", (), {"ISIN": None, "pieces": 1, "total_value": 9,
                                   "value_symbol": "EUR", "valuation_date": None})()
    html = review_module.render_review(review_module.HoldingsReview(
        None, "2026-09-24T18:29:14+00:00", None, review_module.project_fints([holding], raw)))
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert review_module.project_fints([holding, holding], raw)[0].instrument_line == "unavailable"
    wrapped = type("Response", (), {"holdings": ":16R:FIN\n:35B:\n/DE/WKN123456\n"
                                               ":19A::HOLD//EUR9,00\n:16S:FIN"})()
    assert review_module.project_raw_hiwpd([wrapped])[0].instrument_line == "/DE/WKN123456"
    long_marker = type("Response", (), {"holdings": ":16R:FIN\n:35B:" + "X" * 120 + "\n:16S:FIN"})()
    assert review_module.project_raw_hiwpd([long_marker])[0].instrument_line.endswith("…")
    assert len(review_module.project_raw_hiwpd([long_marker])[0].instrument_line) == 97
    too_many = [response] * (review_module.MAX_REVIEW_ROWS + 1)
    assert review_module.project_raw_hiwpd(too_many) is None
    assert review_module.project_raw_hiwpd([type("Response", (), {"holdings": "a" * (review_module.MAX_RAW_RESPONSE_BYTES + 1)})()]) is None


def test_instance_local_hiwpd_hook_observes_only_bank_response(monkeypatch, tmp_path):
    research, app = modules()
    class Client:
        init_tan_response = None
        def __init__(self, *_args, **_kwargs): pass
        def fetch_tan_mechanisms(self): pass
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def _fetch_with_touchdowns(self, dialog, factory, processor, *args):
            assert args == ("HIWPD",)
            payload = "\n:16R:FIN\n:35B:/DE/TESTWKN|Synthetic ETF\n:19A::HOLD//EUR282,85\n:16S:FIN"
            return processor([type("Response", (), {"holdings": payload})()])
        def get_information(self):
            return {"accounts": [{"account_number": "ACCOUNT-123",
                                  "bank_identifier": type("Bank", (), {"bank_code": "12030000"})(),
                                  "supported_operations": {Operations.GET_HOLDINGS: True}}]}
        def get_holdings(self, _account):
            self._fetch_with_touchdowns(None, None, lambda responses: responses, "HIWPD")
            return [type("Holding", (), {"ISIN": None, "pieces": 2.0, "total_value": 282.85,
                                          "value_symbol": "EUR", "valuation_date": None})()]
    Operations, _ = fake_fints(monkeypatch, Client)
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT)
    result = controller.run_holdings_observation("valid", "PRIVATE-PASSWORD")
    assert result.outcome == "retrieved"
    review = controller.holdings_review()
    assert review.fints_rows[0].instrument_line == "/DE/TESTWKN|Synthetic ETF"
    assert review.fints_rows[0].currency == "EUR"
    persisted = controller.holdings_state_file.read_text()
    assert "TESTWKN" not in persisted and "282.85" not in persisted
