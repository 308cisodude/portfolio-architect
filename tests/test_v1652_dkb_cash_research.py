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
system_id = importlib.import_module(f"{NAME}.dkb_system_id")
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


def test_system_id_trial_survives_restart_without_extending_age(monkeypatch, fake_fints, tmp_path: Path):
    """A bank ID survives a cold backup restart, but no-approval reads do not renew it."""
    class Challenge(fake_fints.NeedTANResponse):
        decoupled = True

    class Client:
        seen = []
        def __init__(self, *args, **kwargs):
            self.seen.append(kwargs.copy())
            self.system_id = "BANK-SYSTEM_123"
            self.init_tan_response = None if kwargs.get("system_id") else Challenge()
        def fetch_tan_mechanisms(self): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def send_tan(self, challenge, tan): return None
        def get_information(self):
            return {"accounts": [{"iban": "DE00000000000000001234", "currency": "EUR",
                    "supported_operations": {fake_fints.FinTSOperations.GET_BALANCE: True},
                    "bank_identifier": SimpleNamespace(bank_code=cash.DKB_BANK_CODE),
                    "account_number": "111111"}]}
        def get_balance(self, account): return _balance()

    monkeypatch.setattr(fake_fints, "FinTS3PinTanClient", Client, raising=False)
    controller = DKBProbeController(tmp_path)
    controller.configure_product_id("A" * 25)
    assert controller.run_cash_observation("user", "password", "1234").outcome == "approval_pending"
    assert controller.continue_cash_observation().outcome == "retrieved"
    assert controller.cash_system_trial() == (False, True)
    diagnostic = controller.cash_system_diagnostic()
    assert diagnostic["load"] == "missing"
    assert diagnostic["capture"] == "valid" and diagnostic["save"] == "succeeded"
    assert diagnostic["capture_reason"] == "valid"
    fingerprint = diagnostic["fingerprint"]
    assert len(fingerprint) == 16 and fingerprint != "BANK-SYSTEM_123"
    assert controller.cash_fingerprint_key_file.stat().st_mode & 0o777 == 0o600
    assert len(controller.cash_fingerprint_key_file.read_bytes()) == 32
    path = controller.cash_system_id_file
    assert path.stat().st_mode & 0o777 == 0o600
    identity = system_id.binding("A" * 25, "user")
    seeded = system_id.load(path, identity).seeded_at
    restarted = DKBProbeController(tmp_path)
    assert restarted.run_cash_observation("user", "password", "1234").outcome == "retrieved"
    assert restarted.cash_system_trial() == (True, False)
    assert restarted.cash_system_diagnostic() == {
        "load": "loaded", "capture": "valid", "capture_reason": "valid",
        "save": "succeeded", "fingerprint": fingerprint}
    assert Client.seen[1]["system_id"] == "BANK-SYSTEM_123"
    assert system_id.load(path, identity).seeded_at == seeded
    assert "BANK-SYSTEM_123" not in str(restarted.status_document(
        SimpleNamespace(health_document=lambda version: {})))
    assert "BANK-SYSTEM_123" not in "".join(
        p.read_text(errors="replace") for p in tmp_path.iterdir() if p != path)
    assert restarted.run_cash_observation("other_user", "password", "1234").outcome == "approval_pending"
    assert restarted.cash_system_diagnostic()["load"] == "different_user"
    assert "system_id" not in Client.seen[2]
    assert restarted.continue_cash_observation().outcome == "retrieved"
    assert system_id.load(path, identity) is None
    assert system_id.load(path, system_id.binding("A" * 25, "other_user")) is not None
    system_id.save(path, identity, "BANK-SYSTEM_123", datetime.now(timezone.utc) - timedelta(hours=73))
    assert system_id.load(path, identity) is None and not path.exists()
    restarted.configure_product_id("B" * 25)
    assert not path.exists()


def test_system_id_is_bounded_and_excluded_from_cold_backup(tmp_path: Path):
    from fnmatch import fnmatchcase
    import yaml
    config = yaml.safe_load((PACKAGE.parents[1] / "config.yaml").read_text())
    assert config["backup"] == "cold"
    assert config["backup_exclude"] == [f"gateway/{system_id.FILE_NAME}",
                                        f"gateway/.{system_id.FILE_NAME}.*",
                                        f"gateway/{system_id.KEY_FILE_NAME}",
                                        f"gateway/.{system_id.KEY_FILE_NAME}.*"]
    assert all(any(fnmatchcase(name, pattern) for pattern in config["backup_exclude"])
               for name in (f"gateway/{system_id.FILE_NAME}",
                            f"gateway/.{system_id.FILE_NAME}.orphan"))
    path = tmp_path / system_id.FILE_NAME
    binding = system_id.binding("A" * 25, "user")
    now = datetime.now(timezone.utc)
    system_id.save(path, binding, "BANKSYSTEM123", now)
    assert system_id.load(path, binding, now + timedelta(hours=71)) is not None
    assert system_id.load(path, binding, now + timedelta(hours=72)) is None
    path.write_text('{"schema_version":1,"system_id":"secret"}')
    path.chmod(0o600)
    assert system_id.load(path, binding) is None and not path.exists()
    path.write_text('not json')
    path.chmod(0o600)
    assert system_id.load(path, binding) is None and not path.exists()
    system_id.save(path, binding, "BANKSYSTEM123", now)
    path.chmod(0o644)
    assert system_id.load(path, binding) is None and not path.exists()
    path.symlink_to(tmp_path / "unrelated")
    assert system_id.load(path, binding) is None and not path.exists()


@pytest.mark.parametrize(("value", "category"), [
    (None, "absent"), (0, "non_string"), (b"BANK", "non_string"),
    ("0", "zero_sentinel"), ("", "empty"), ("A" * 31, "over_limit"),
    ("ABC-123", "valid"), ("A_B.C:?'\"+@\\", "valid"),
    ("ÄBC-123", "valid"), ("\nPRIVATE", "non_printable"),
    ("A\x00B", "non_printable"), ("A\x7fB", "non_printable"),
    ("BANKSYSTEM123", "valid"),
])
def test_system_id_capture_categories_are_bounded(value: object, category: str) -> None:
    assert system_id.capture_category(value) == category
    assert category == "valid" or not value or str(value) not in category


def test_invalid_capture_does_not_persist_or_fingerprint_id(tmp_path: Path) -> None:
    controller = DKBProbeController(tmp_path)
    controller._cash_diagnostic = {"load": "missing", "capture": "absent",
                                   "capture_reason": "not_observed", "save": "skipped",
                                   "fingerprint": "unavailable"}
    ids: list[str] = []
    controller._record_cash_system_id_capture("ABC\n123", ids)
    assert ids == []
    assert controller.cash_system_diagnostic()["capture_reason"] == "non_printable"
    assert not controller.cash_system_id_file.exists()
    assert not controller.cash_fingerprint_key_file.exists()
    controller._record_cash_system_id_capture("BANKSYSTEM123", ids)
    controller._record_cash_system_id_capture("0", ids)
    assert ids == ["BANKSYSTEM123"]
    assert controller.cash_system_diagnostic()["capture_reason"] == "valid"


def test_system_id_private_json_roundtrip_and_fingerprint_with_special_characters(tmp_path: Path) -> None:
    identity = system_id.binding("A" * 25, "user")
    path = tmp_path / system_id.FILE_NAME
    key_path = tmp_path / system_id.KEY_FILE_NAME
    value = "Ä:?'\"+@\\_"
    system_id.save(path, identity, value, datetime.now(timezone.utc))
    assert system_id.load(path, identity).system_id == value
    assert path.stat().st_mode & 0o777 == 0o600
    assert len(system_id.fingerprint(key_path, value)) == 16
    assert value not in path.read_text(encoding="ascii")
    assert "\\u00c4" in path.read_text(encoding="ascii")
    for rejected in ("A\nB", "A\x00B", "A" * 31, "0"):
        with pytest.raises(ValueError):
            system_id.save(path, identity, rejected, datetime.now(timezone.utc))
        assert system_id.fingerprint(key_path, rejected) is None
