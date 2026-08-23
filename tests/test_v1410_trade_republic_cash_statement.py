"""Regression coverage for v1.41.1 Trade Republic cash-statement acquisition."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import importlib.util
import sys

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
if str(COMPONENT) not in sys.path:
    sys.path.insert(0, str(COMPONENT))
TR_SRC = ROOT / "home_assistant_app" / "portfolio_architect_gateway_trade_republic" / "src"
_PACKAGE_NAME = "portfolio_architect_gateway_tr_v1410_test"
_PACKAGE_DIR = TR_SRC / "portfolio_architect_gateway"
_spec = importlib.util.spec_from_file_location(
    _PACKAGE_NAME,
    _PACKAGE_DIR / "__init__.py",
    submodule_search_locations=[str(_PACKAGE_DIR)],
)
assert _spec is not None and _spec.loader is not None
_pkg = importlib.util.module_from_spec(_spec)
sys.modules[_PACKAGE_NAME] = _pkg
_spec.loader.exec_module(_pkg)

from portfolio_architect_gateway_tr_v1410_test.models import PortfolioSnapshot, Position  # type: ignore[import-not-found]  # noqa: E402
from portfolio_architect_gateway_tr_v1410_test.trade_republic_cash_statement import (  # type: ignore[import-not-found]  # noqa: E402
    CashStatementImportError,
    TradeRepublicCashSnapshot,
    load_cash_snapshot,
    parse_cash_statement_text,
    save_cash_snapshot,
)
from portfolio_architect_gateway_tr_v1410_test.trade_republic_statement import TradeRepublicStatementProvider  # type: ignore[import-not-found]  # noqa: E402

from engine.rest import parse_rest_snapshot


def _cash_layout(*, ending: str = "4.321,09", trust: str = "4.321,09", qmmf: str = "0,00") -> str:
    return "\n".join(
        [
            "TRADE REPUBLIC BANK GMBH BRUNNENSTRASSE 19-21 10119 BERLIN",
            "SYNTHETIC PERSON DATUM 01 Aug. 2026 - 20 Aug. 2026",
            "KONTOÜBERSICHT",
            "PRODUKT ANFANGSSALDO ZAHLUNGSEINGANG ZAHLUNGSAUSGANG ENDSALDO",
            f"Cashkonto 1.234,56 € 4.086,53 € 1.000,00 € {ending} €",
            "UMSATZÜBERSICHT",
            "SYNTHETIC TRANSACTION ROWS ARE IRRELEVANT TO THE BOUNDED CASH RESULT",
            "BARMITTELÜBERSICHT",
            "Zum 20 Aug. 2026",
            "TREUHANDKONTEN SALDO",
            f"Synthetic Trust Bank {trust} €",
            "Trade Republic Bank GmbH",
            "GELDMARKTFONDS ISIN STK. / NOMINALE KURS PRO STÜCK KURSWERT IN EUR",
            f"Synthetic Liquidity Fund LU3041245716 0,00 1,00 € {qmmf} €",
            "HINWEISE ZUM KONTOAUSZUG",
            "Synthetic legal text",
            "Erstellt am 2026-08-21 12:30:34 Europe/Berlin (UTC+02:00) Seite 1 von 1",
        ]
    )


def _holdings_snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        generated_at=datetime(2026, 8, 19, 9, 17, 29, tzinfo=timezone.utc),
        positions=(
            Position(
                identifier="IE00BYZK4552",
                name="Synthetic ETF",
                market_value_eur=Decimal("5000"),
                quantity=Decimal("270.5"),
                isin="IE00BYZK4552",
                instrument_type="ETF",
            ),
        ),
    )


def test_cash_statement_parses_only_reconciled_provider_cash() -> None:
    cash = parse_cash_statement_text(
        _cash_layout(),
        now=datetime(2026, 8, 21, 12, 45, tzinfo=timezone.utc),
    )
    assert cash.account_balance_eur == Decimal("4321.09")
    assert cash.eligible_eur == Decimal("4321.09")
    assert cash.as_of == datetime(2026, 8, 20, 21, 59, 59, tzinfo=timezone.utc)
    assert cash.generated_at == datetime(2026, 8, 21, 10, 30, 34, tzinfo=timezone.utc)
    public = cash.investment_cash().as_dict()
    assert public == {
        "account_balance_eur": "4321.09",
        "eligible_eur": "4321.09",
        "authorized_eur": "4321.09",
        "policy": "all_available",
        "as_of": "2026-08-20T21:59:59Z",
    }
    serialized = repr(public)
    assert "SYNTHETIC PERSON" not in serialized
    assert "TRANSACTION" not in serialized


@pytest.mark.parametrize(
    "text, message",
    [
        (_cash_layout(ending="4.321,08"), "arithmetic"),
        (_cash_layout(trust="4.321,08"), "custody components"),
        (_cash_layout().replace("KONTOÜBERSICHT", "DEPOTAUSZUG"), "Unsupported"),
        (_cash_layout().replace("Zum 20 Aug. 2026", "Zum 22 Aug. 2026"), "newer than document creation"),
    ],
)
def test_cash_statement_inconsistency_fails_closed(text: str, message: str) -> None:
    with pytest.raises(CashStatementImportError, match=message):
        parse_cash_statement_text(
            text,
            now=datetime(2026, 8, 21, 12, 45, tzinfo=timezone.utc),
        )


def test_cash_state_is_bounded_and_independent_from_holdings(tmp_path: Path) -> None:
    cash = parse_cash_statement_text(
        _cash_layout(),
        now=datetime(2026, 8, 21, 12, 45, tzinfo=timezone.utc),
    )
    path = tmp_path / "trade-republic-cash.json"
    save_cash_snapshot(path, cash)
    loaded = load_cash_snapshot(path)
    assert loaded == cash
    text = path.read_text(encoding="utf-8")
    assert "4321.09" in text
    assert "SYNTHETIC" not in text
    assert "IBAN" not in text


def test_provider_composes_independent_cash_without_refreshing_holdings_timestamp(tmp_path: Path) -> None:
    provider = TradeRepublicStatementProvider(tmp_path / "portfolio.json")
    provider.replace_snapshot(_holdings_snapshot())
    cash = TradeRepublicCashSnapshot(
        account_balance_eur=Decimal("4321.09"),
        as_of=datetime(2026, 8, 20, 21, 59, 59, tzinfo=timezone.utc),
        generated_at=datetime(2026, 8, 21, 10, 30, 34, tzinfo=timezone.utc),
    )
    provider.replace_cash_snapshot(cash)
    composed = provider.fetch_snapshot()
    assert composed.generated_at == datetime(2026, 8, 19, 9, 17, 29, tzinfo=timezone.utc)
    assert composed.investment_reserve_eur == Decimal("4321.09")
    assert composed.investment_reserve_as_of == cash.as_of
    assert composed.investment_cash is not None
    assert composed.investment_cash.authorized_eur == Decimal("4321.09")


def test_rest_schema_allows_cash_evidence_newer_than_holdings_evidence() -> None:
    payload = {
        "schema_version": 1,
        "generated_at": "2026-08-19T09:17:29Z",
        "currency": "EUR",
        "positions": [
            {
                "identifier": "IE00BYZK4552",
                "isin": "IE00BYZK4552",
                "name": "Synthetic ETF",
                "market_value_eur": "5000",
                "quantity": "270.5",
                "instrument_type": "ETF",
            }
        ],
        "investment_reserve": {
            "available_eur": "4321.09",
            "as_of": "2026-08-20T21:59:59Z",
        },
        "investment_cash": {
            "account_balance_eur": "4321.09",
            "eligible_eur": "4321.09",
            "authorized_eur": "4321.09",
            "policy": "all_available",
            "as_of": "2026-08-20T21:59:59Z",
        },
    }
    snapshot = parse_rest_snapshot(
        payload,
        now=datetime(2026, 8, 21, 12, 45, tzinfo=timezone.utc),
    )
    assert snapshot.generated_at == datetime(2026, 8, 19, 9, 17, 29, tzinfo=timezone.utc)
    assert snapshot.investment_reserve_eur == Decimal("4321.09")


def test_tr_app_exposes_separate_bounded_statement_families() -> None:
    source = (TR_SRC / "portfolio_architect_gateway" / "trade_republic_app.py").read_text(encoding="utf-8")
    assert '"/import", "/import-cash"' in source
    assert "DEPOTAUSZUG" in source
    assert "KONTOAUSZUG" in source
    assert "Uploaded PDFs are parsed in memory and are not stored" in source
    for forbidden in ("transaction_history", "submit_order", "place_order", "create_order", "transfer_money"):
        assert forbidden not in source


def test_home_assistant_gates_cash_freshness_separately_from_holdings() -> None:
    coordinator = (ROOT / "custom_components" / "portfolio_architect" / "coordinator.py").read_text(encoding="utf-8")
    assert "def _cash_timestamp_is_fresh" in coordinator
    assert "cash_evidence_kind(provider_id)" in coordinator
    assert "cash_freshness_threshold_hours_by_kind=self.freshness_threshold_hours_by_kind" in coordinator
    assert "investment_reserve_eur = None" in coordinator
    rest = (ROOT / "custom_components" / "portfolio_architect" / "engine" / "rest.py").read_text(encoding="utf-8")
    assert "REST investment reserve timestamp is newer than the snapshot" not in rest
    assert "REST investment cash timestamp is newer than the snapshot" not in rest
