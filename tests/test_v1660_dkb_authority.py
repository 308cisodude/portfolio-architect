"""Explicit DKB FinTS promotion and expiry without a bank connection."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway"
NAME = "portfolio_architect_gateway_dkb_v1660_test"
spec = importlib.util.spec_from_file_location(NAME, PACKAGE / "__init__.py", submodule_search_locations=[str(PACKAGE)])
module = importlib.util.module_from_spec(spec)
sys.modules[NAME] = module
spec.loader.exec_module(module)
selection = importlib.import_module(f"{NAME}.dkb_account_selection")
authority = importlib.import_module(f"{NAME}.dkb_fints_authority")
cash_csv = importlib.import_module(f"{NAME}.dkb_cash_csv")
bank_code = importlib.import_module(f"{NAME}.dkb_fints").DKB_BANK_CODE
csv = importlib.import_module(f"{NAME}.dkb_csv")
server = importlib.import_module(f"{NAME}.server")
pending = importlib.import_module(f"{NAME}.pending_app")
store = importlib.import_module(f"{NAME}.store")
freshness_spec = importlib.util.spec_from_file_location("pa_v1660_freshness", ROOT / "custom_components/portfolio_architect/freshness.py")
freshness = importlib.util.module_from_spec(freshness_spec)
freshness_spec.loader.exec_module(freshness)


def _setup(tmp_path):
    selected = selection.select(
        tmp_path / selection.SELECTION_FILE_NAME, tmp_path / selection.KEY_FILE_NAME,
        product_id="A" * 25, user_id="banking-user",
        account={"iban": "DE" + "0" * 16 + "1234", "account_number": "ACCOUNT-7", "bank_code": bank_code},
    )
    provider = authority.DkbAcquisitionProvider(tmp_path / "portfolio.json")
    csv_snapshot, _ = csv.parse_dkb_csv_batch(((ROOT / "tests/fixtures/dkb-depot.csv").read_bytes(),))
    provider.replace_snapshot(csv_snapshot)
    now = datetime.now(timezone.utc)
    provider.replace_cash_snapshot(cash_csv.DkbCashSnapshot(Decimal("50"), now, now))
    return selected, provider


def _evidence(selected, *, holdings_at=None, cash_at=None, amount="125.95"):
    current = datetime.now(timezone.utc)
    holdings_at = holdings_at or current
    cash_at = cash_at or current
    return {
        "schema_version": 1,
        "account_binding": selected.binding,
        "user_binding": selected.user_binding,
        "holdings": {
            "schema_version": 1, "observed_at": holdings_at.isoformat(timespec="seconds"),
            "positions": [{"isin": "IE00BJ0KDQ92", "quantity": "2", "total_value": "280.50", "currency": "EUR"}],
        },
        "cash": {"schema_version": 1, "amount": amount, "currency": "EUR",
                 "bank_date": current.date().isoformat(), "observed_at": cash_at.isoformat(timespec="seconds")},
    }


def test_default_csv_and_legacy_shadows_cannot_be_promoted(tmp_path):
    selected, provider = _setup(tmp_path)
    assert provider.acquisition_mode == "csv"
    assert provider.fetch_snapshot().investment_cash.account_balance_eur == Decimal("50")
    store.save_json_state(tmp_path / "dkb-fints-holdings-shadow.json", _evidence(selected)["holdings"])
    store.save_json_state(tmp_path / "dkb-fints-cash-shadow.json", _evidence(selected)["cash"])
    with pytest.raises(authority.ConfigurationError):
        provider.activate_mode("fints", lambda: True)
    assert provider.acquisition_mode == "csv"


def test_explicit_switch_provenance_policy_and_fail_closed_cache(tmp_path):
    selected, provider = _setup(tmp_path)
    evidence = _evidence(selected)
    authority.stage_evidence(provider.evidence_file, selected, evidence["holdings"], evidence["cash"])
    assert provider.evidence_file.stat().st_mode & 0o777 == 0o600
    serialized = provider.evidence_file.read_text()
    assert "banking-user" not in serialized and "DE000" not in serialized
    state = server.GatewayState(pending.build_server_config(pending.PendingAppOptions(), tmp_path), provider)
    assert state.refresh(trigger="startup")
    assert state.snapshot_view() is not None
    csv_bytes = (tmp_path / "portfolio.json").read_bytes()
    provider.activate_mode("fints", lambda: state.refresh(trigger="manual"))
    assert provider.acquisition_mode == "fints"
    assert provider.fetch_snapshot().investment_cash.account_balance_eur == Decimal("125.95")
    assert provider.fetch_snapshot().positions[0].name == "ISIN IE00BJ0KDQ92"
    assert state.health_document(version=9)["active_acquisition_method"] == "fints"
    assert state.snapshot_view() is not None
    assert (tmp_path / "portfolio.json").read_bytes() == csv_bytes
    assert (tmp_path / authority.FINTS_CANONICAL_FILE_NAME).is_file()
    restarted = authority.DkbAcquisitionProvider(tmp_path / "portfolio.json")
    assert restarted.acquisition_mode == "fints"
    assert restarted.holdings_snapshot.positions[0].identifier == provider.holdings_snapshot.positions[0].identifier
    provider.evidence_file.unlink()
    assert state.snapshot_view() is None
    health = state.health_document(version=9)
    assert health["snapshot_available"] is False
    assert health["acquisition_capabilities"][0]["authoritative_method"] == "fints"
    assert restarted.snapshot_is_current(store.load_snapshot(restarted.canonical_snapshot_file)) is False
    provider.activate_mode("csv", lambda: state.refresh(trigger="manual"))
    assert state.snapshot_view() is not None
    assert provider.fetch_snapshot().investment_cash.account_balance_eur == Decimal("50")


def test_independent_clocks_have_hard_expiry_and_binding(tmp_path):
    selected, provider = _setup(tmp_path)
    now = datetime.now(timezone.utc)
    for key in ("holdings", "cash"):
        raw = _evidence(selected)
        raw[key]["observed_at"] = (now - timedelta(days=14, seconds=1)).isoformat(timespec="seconds")
        store.save_json_state(provider.evidence_file, raw)
        with pytest.raises(authority.ConfigurationError, match="older than 14 days"):
            provider._fints_snapshot()
    raw = _evidence(selected)
    raw["account_binding"] = "0" * 64
    store.save_json_state(provider.evidence_file, raw)
    with pytest.raises(authority.ConfigurationError, match="binding"):
        provider._fints_snapshot()
    raw = _evidence(selected)
    raw["holdings"]["positions"][0]["currency"] = "USD"
    store.save_json_state(provider.evidence_file, raw)
    with pytest.raises(authority.ConfigurationError, match="EUR"):
        provider._fints_snapshot()


def test_switch_failure_rolls_back_and_interrupted_switch_discards_cache(tmp_path):
    selected, provider = _setup(tmp_path)
    raw = _evidence(selected)
    authority.stage_evidence(provider.evidence_file, selected, raw["holdings"], raw["cash"])
    attempts = iter((False, True))
    with pytest.raises(authority.ConfigurationError):
        provider.activate_mode("fints", lambda: next(attempts))
    assert provider.acquisition_mode == "csv"
    assert not provider._pending_file.exists()
    store.save_json_state(provider._pending_file, {"schema_version": 1,
                                                   "previous_state": {"schema_version": 1, "mode": "csv"},
                                                   "previous_state_persisted": False})
    store.save_json_state(provider._mode_file, {"schema_version": 1, "mode": "fints"})
    store.save_snapshot(provider._snapshot_file, provider.fetch_snapshot())
    restored = authority.DkbAcquisitionProvider(provider._snapshot_file)
    assert restored.acquisition_mode == "csv"
    assert not provider._snapshot_file.exists() and not provider._pending_file.exists()


def test_dkb_fints_freshness_kind_is_fixed_at_fourteen_days():
    assert freshness.evidence_kind("dkb", "fints") == "fints"
    assert freshness.cash_evidence_kind("dkb", "fints") == "fints"
    assert freshness.evidence_kind("dkb", "csv") == "csv"
    now = datetime.now(timezone.utc)
    source = [{"source_id": "dkb", "provider": "dkb", "label": "DKB", "acquisition_mode": "fints",
               "generated_at": (now - timedelta(days=14, seconds=1)).isoformat()}]
    row = freshness.source_freshness_rows(source, now=now, threshold_hours=744,
                                          threshold_hours_by_kind={"fints": 744})[0]
    assert row["threshold_hours"] == 336 and row["within_age_threshold"] is False
