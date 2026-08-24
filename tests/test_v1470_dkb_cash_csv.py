"""v1.48.0 adds independent DKB Girokonto CSV cash evidence inside the DKB Gateway."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib
import importlib.util
from pathlib import Path
import stat
import sys

import pytest

ROOT = Path(__file__).parents[1]
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb"
PACKAGE = APP / "src" / "portfolio_architect_gateway"
TEST_PACKAGE = "portfolio_architect_gateway_dkb_v1470_test"


def _load_modules():
    if TEST_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            TEST_PACKAGE,
            PACKAGE / "__init__.py",
            submodule_search_locations=[str(PACKAGE)],
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[TEST_PACKAGE] = module
        spec.loader.exec_module(module)
    return (
        importlib.import_module(f"{TEST_PACKAGE}.dkb_cash_csv"),
        importlib.import_module(f"{TEST_PACKAGE}.dkb_csv"),
        importlib.import_module(f"{TEST_PACKAGE}.store"),
    )


def _cash_csv(*, balance_date: str = "23.08.2026", balance: str = "267,08\u00a0€") -> bytes:
    return (
        '\ufeff"Girokonto";"DE00123456789012345678"\n\n'
        f'"Kontostand vom {balance_date}:";"{balance}"\n'
        '""\n'
        '"Buchungsdatum";"Wertstellung";"Status";"Zahlungspflichtige*r";'
        '"Zahlungsempfänger*in";"Verwendungszweck";"Umsatztyp";"IBAN";'
        '"Betrag (€)";"Gläubiger-ID";"Mandatsreferenz";"Kundenreferenz"\n'
        '"22.08.26";"22.08.26";"Gebucht";"Synthetic Payer";"Synthetic Merchant";'
        '"Synthetic reference";"Ausgang";"DE00999999999999999999";"-1,23";"";"";"SYNTHETIC"\n'
    ).encode("utf-8")


def _holdings_csv(*, date: str = "23.08.2026", price: str = "138,28") -> bytes:
    return (
        "Datum der Erstellung;Depotnummer;Wertpapierbezeichnung;WKN;ISIN;"
        "Bewertungskurs;Stückzahl;Assetklasse\n"
        f"{date};SYNTHETIC-DEPOT;Synthetic World ETF;A1XB5U;IE00BJ0KDQ92;{price};2;ETF\n"
    ).encode("utf-8")


def test_dkb_girokonto_csv_extracts_only_explicit_eur_balance_conservatively() -> None:
    cash, _dkb_csv, _store = _load_modules()
    snapshot = cash.parse_dkb_cash_csv(
        _cash_csv(),
        now=datetime(2026, 8, 23, 14, 0, tzinfo=timezone.utc),
    )

    assert snapshot.account_balance_eur == Decimal("267.08")
    assert snapshot.eligible_eur == Decimal("267.08")
    # DKB supplies a date but no trustworthy creation time. The deterministic
    # evidence timestamp is local Berlin midnight, i.e. 22:00 UTC during CEST.
    assert snapshot.as_of == datetime(2026, 8, 22, 22, 0, tzinfo=timezone.utc)
    assert snapshot.generated_at == snapshot.as_of
    investment_cash = snapshot.investment_cash()
    assert investment_cash.authorized_eur == Decimal("267.08")
    assert investment_cash.policy == "all_available"


def test_negative_dkb_balance_never_becomes_credit_funded_investment_cash() -> None:
    cash, _dkb_csv, _store = _load_modules()
    snapshot = cash.parse_dkb_cash_csv(
        _cash_csv(balance="-125,40 €"),
        now=datetime(2026, 8, 23, 14, 0, tzinfo=timezone.utc),
    )
    assert snapshot.account_balance_eur == Decimal("-125.40")
    assert snapshot.eligible_eur == Decimal("0")
    assert snapshot.investment_cash().authorized_eur == Decimal("0")


def test_cash_parser_fails_closed_on_wrong_currency_future_date_and_structure() -> None:
    cash, _dkb_csv, _store = _load_modules()
    now = datetime(2026, 8, 23, 14, 0, tzinfo=timezone.utc)
    with pytest.raises(cash.DkbCashCsvImportError, match="denominated in EUR"):
        cash.parse_dkb_cash_csv(_cash_csv(balance="267,08 USD"), now=now)
    with pytest.raises(cash.DkbCashCsvImportError, match="date is in the future"):
        cash.parse_dkb_cash_csv(_cash_csv(balance_date="24.08.2026"), now=now)
    malformed = _cash_csv().replace(b'"Kundenreferenz"', b'"Unexpected"', 1)
    with pytest.raises(cash.DkbCashCsvImportError, match="transaction header"):
        cash.parse_dkb_cash_csv(malformed, now=now)


def test_dkb_holdings_and_cash_evidence_compose_without_refreshing_each_other(tmp_path: Path) -> None:
    cash, dkb_csv, store = _load_modules()
    holdings, _summary = dkb_csv.parse_dkb_csv_batch((_holdings_csv(),))
    cash_snapshot = cash.parse_dkb_cash_csv(
        _cash_csv(), now=datetime(2026, 8, 23, 14, 0, tzinfo=timezone.utc)
    )

    snapshot_file = tmp_path / "portfolio.json"
    store.save_snapshot(snapshot_file, holdings)
    provider = dkb_csv.DkbCsvProvider(snapshot_file)
    provider.replace_cash_snapshot(cash_snapshot)
    provider.persist_cash_snapshot(cash_snapshot)
    composed = provider.snapshot
    assert composed is not None
    assert composed.generated_at == holdings.generated_at
    assert composed.investment_reserve_eur == Decimal("267.08")
    assert composed.investment_reserve_as_of == cash_snapshot.as_of
    assert composed.investment_cash is not None
    assert composed.investment_cash.account_balance_eur == Decimal("267.08")

    newer_holdings, _ = dkb_csv.parse_dkb_csv_batch((_holdings_csv(date="24.08.2026", price="139,00"),))
    provider.replace_snapshot(newer_holdings)
    recomposed = provider.snapshot
    assert recomposed is not None
    assert recomposed.generated_at == datetime(2026, 8, 24, tzinfo=timezone.utc)
    assert recomposed.investment_reserve_as_of == cash_snapshot.as_of


def test_only_normalized_cash_state_persists_and_survives_composed_snapshot_reload(tmp_path: Path) -> None:
    cash, dkb_csv, store = _load_modules()
    holdings, _summary = dkb_csv.parse_dkb_csv_batch((_holdings_csv(),))
    cash_snapshot = cash.parse_dkb_cash_csv(
        _cash_csv(), now=datetime(2026, 8, 23, 14, 0, tzinfo=timezone.utc)
    )
    snapshot_file = tmp_path / "portfolio.json"
    store.save_snapshot(snapshot_file, holdings)
    provider = dkb_csv.DkbCsvProvider(snapshot_file)
    provider.replace_cash_snapshot(cash_snapshot)
    provider.persist_cash_snapshot(cash_snapshot)
    assert provider.snapshot is not None
    store.save_snapshot(snapshot_file, provider.snapshot)

    cash_text = provider.cash_file.read_text(encoding="utf-8")
    for forbidden in (
        "Girokonto",
        "DE00123456789012345678",
        "Synthetic Merchant",
        "Synthetic reference",
        "Buchungsdatum",
    ):
        assert forbidden not in cash_text
    assert '"account_balance_eur":"267.08"' in cash_text.replace(" ", "")
    assert stat.S_IMODE(provider.cash_file.stat().st_mode) == 0o600

    restored = dkb_csv.DkbCsvProvider(snapshot_file)
    assert restored.cash_snapshot is not None
    assert restored.snapshot is not None
    assert restored.snapshot.investment_reserve_eur == Decimal("267.08")
    assert restored.snapshot.generated_at == holdings.generated_at


def test_dkb_ingress_exposes_separate_cash_import_without_fints_fallback() -> None:
    app = (PACKAGE / "dkb_app.py").read_text(encoding="utf-8")
    assert 'path == "/import-cash"' in app
    assert "parse_dkb_cash_csv" in app
    assert "DKB Girokonto Umsatzliste CSV" in app
    assert "Importing cash does not refresh holdings evidence" in app
    assert "no overdraft or credit facility is inferred" in app
    assert "FinTS cannot replace or silently fall back to CSV evidence" in app


def test_real_private_dkb_cash_export_is_not_a_repository_fixture() -> None:
    # The implementation was designed from private live evidence, but public source
    # must retain only synthetic examples/tests and never the user's actual export.
    names = {path.name for path in ROOT.rglob("*") if path.is_file()}
    assert "23-08-2026_Umsatzliste_Girokonto_DKB.csv" not in names


def test_dkb_cash_uses_imported_statement_freshness_without_reclassifying_holdings() -> None:
    component = ROOT / "custom_components" / "portfolio_architect"
    freshness_path = component / "freshness.py"
    spec = importlib.util.spec_from_file_location("portfolio_architect_freshness_v1470_test", freshness_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.evidence_kind("dkb") == "gateway_snapshot"
    assert module.cash_evidence_kind("dkb") == "imported_statement"
    assert module.cash_evidence_kind("trade_republic") == "imported_statement"
    assert module.cash_evidence_kind("comdirect") == "live_api"
