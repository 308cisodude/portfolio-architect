"""Regression contracts for v1.62.3 Trade Republic cash-statement month labels."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
TR_SRC = ROOT / "home_assistant_app" / "portfolio_architect_gateway_trade_republic" / "src"
_PACKAGE_NAME = "portfolio_architect_gateway_tr_v1623_test"
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

from portfolio_architect_gateway_tr_v1623_test.trade_republic_cash_statement import (  # type: ignore[import-not-found]  # noqa: E402
    CashStatementImportError,
    parse_cash_statement_text,
)

_BERLIN = ZoneInfo("Europe/Berlin")

# German abbreviated month labels from the locale family used by provider documents.
_CANONICAL_GERMAN_MONTHS = (
    (1, "Jan."),
    (2, "Feb."),
    (3, "März"),
    (4, "Apr."),
    (5, "Mai"),
    (6, "Juni"),
    (7, "Juli"),
    (8, "Aug."),
    (9, "Sept."),
    (10, "Okt."),
    (11, "Nov."),
    (12, "Dez."),
)

# Compatibility aliases accepted before v1.62.3 must remain valid.
_LEGACY_ALIASES = (
    (3, "Mär."),
    (3, "Mar."),
    (5, "Mai."),
    (5, "May."),
    (6, "Jun."),
    (7, "Jul."),
    (9, "Sep."),
    (10, "Oct."),
    (12, "Dec."),
)


def _utc_offset_token(local_dt: datetime) -> str:
    raw = local_dt.strftime("%z")
    return f"{raw[:3]}:{raw[3:]}"


def _layout(month: int, token: str) -> tuple[str, datetime]:
    created_local = datetime(2026, month, 16, 12, 0, 0, tzinfo=_BERLIN)
    offset = _utc_offset_token(created_local)
    text = "\n".join(
        [
            "TRADE REPUBLIC BANK GMBH BRUNNENSTRASSE 19-21 10119 BERLIN",
            f"DATUM 01 {token} 2026 - 15 {token} 2026",
            "SYNTHETIC PERSON",
            "KONTOÜBERSICHT",
            "PRODUKT ANFANGSSALDO ZAHLUNGSEINGANG ZAHLUNGSAUSGANG ENDSALDO",
            "Cashkonto 100,00 € 50,00 € 0,00 € 150,00 €",
            "UMSATZÜBERSICHT",
            "SYNTHETIC TRANSACTION ROWS ARE IRRELEVANT TO THE BOUNDED CASH RESULT",
            "BARMITTELÜBERSICHT",
            f"Zum 15 {token} 2026",
            "TREUHANDKONTEN SALDO",
            "Synthetic Trust Bank 150,00 €",
            "Trade Republic Bank GmbH",
            "GELDMARKTFONDS ISIN STK. / NOMINALE KURS PRO STÜCK KURSWERT IN EUR",
            "Synthetic Liquidity Fund LU3041245716 0,00 1,00 € 0,00 €",
            "HINWEISE ZUM KONTOAUSZUG",
            "Synthetic legal text",
            f"Erstellt am 2026-{month:02d}-16 12:00:00 Europe/Berlin (UTC{offset}) Seite 1 von 1",
        ]
    )
    return text, created_local.astimezone(timezone.utc)


@pytest.mark.parametrize("month, token", _CANONICAL_GERMAN_MONTHS)
def test_complete_german_provider_month_matrix_is_accepted(month: int, token: str) -> None:
    text, generated_at = _layout(month, token)
    snapshot = parse_cash_statement_text(text, now=generated_at + timedelta(hours=1))
    assert snapshot.account_balance_eur == Decimal("150.00")
    assert snapshot.generated_at == generated_at
    assert snapshot.as_of.astimezone(_BERLIN).date() == date(2026, month, 15)
    assert snapshot.as_of.astimezone(_BERLIN).time().isoformat() == "23:59:59"


@pytest.mark.parametrize("month, token", _LEGACY_ALIASES)
def test_preexisting_month_aliases_remain_accepted(month: int, token: str) -> None:
    text, generated_at = _layout(month, token)
    snapshot = parse_cash_statement_text(text, now=generated_at + timedelta(hours=1))
    assert snapshot.as_of.astimezone(_BERLIN).date() == date(2026, month, 15)


def test_live_observed_sept_statement_shape_is_accepted() -> None:
    text, generated_at = _layout(9, "Sept.")
    text = text.replace("DATUM 01 Sept. 2026 - 15 Sept. 2026", "DATUM 01 Sept. 2026 - 02 Sept. 2026")
    text = text.replace("Zum 15 Sept. 2026", "Zum 02 Sept. 2026")
    snapshot = parse_cash_statement_text(text, now=generated_at + timedelta(hours=1))
    assert snapshot.as_of == datetime(2026, 9, 2, 21, 59, 59, tzinfo=timezone.utc)


@pytest.mark.parametrize("unsupported", ("Janu.", "Febr.", "März.", "Juni.", "Juli.", "September"))
def test_unbounded_or_noncanonical_month_spellings_remain_unsupported(unsupported: str) -> None:
    text, generated_at = _layout(1, "Jan.")
    text = text.replace("Zum 15 Jan. 2026", f"Zum 15 {unsupported} 2026")
    with pytest.raises(CashStatementImportError, match="missing or unsupported"):
        parse_cash_statement_text(text, now=generated_at + timedelta(hours=1))


def test_missing_and_ambiguous_cash_dates_have_distinct_bounded_errors() -> None:
    text, generated_at = _layout(9, "Sept.")
    missing = text.replace("Zum 15 Sept. 2026", "As of 15 September 2026")
    with pytest.raises(CashStatementImportError, match="missing or unsupported"):
        parse_cash_statement_text(missing, now=generated_at + timedelta(hours=1))

    ambiguous = text.replace(
        "BARMITTELÜBERSICHT\nZum 15 Sept. 2026",
        "BARMITTELÜBERSICHT\nZum 15 Sept. 2026\nBARMITTELÜBERSICHT\nZum 14 Sept. 2026",
    )
    with pytest.raises(CashStatementImportError, match="ambiguous cash as-of date"):
        parse_cash_statement_text(ambiguous, now=generated_at + timedelta(hours=1))


def test_ingress_safe_error_allowlist_contains_the_new_missing_date_reason() -> None:
    app_source = (TR_SRC / "portfolio_architect_gateway" / "trade_republic_app.py").read_text(encoding="utf-8")
    assert '"Statement cash as-of date is missing or unsupported"' in app_source
    assert '"Statement contains an ambiguous cash as-of date"' in app_source
