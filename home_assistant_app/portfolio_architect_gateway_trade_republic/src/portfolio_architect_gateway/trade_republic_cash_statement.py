"""Strict local Trade Republic KONTOAUSZUG cash-statement importer.

Only the bounded provider-scoped cash result is retained. Transaction rows, account
identifiers, counterparties, identity data, and the uploaded PDF never persist.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any, Final
from zoneinfo import ZoneInfo

from .errors import ProtocolError
from .models import InvestmentCash, canonical_signed_decimal
from .store import load_json_state, save_json_state
from .trade_republic_pdf import MAX_EXTRACTED_TEXT_CHARS, TradeRepublicPdfError, extract_bounded_pdf_text

MAX_CASH_EUR: Final = Decimal("1000000000")
MAX_CLOCK_SKEW: Final = timedelta(minutes=5)
CASH_STATE_FILE_NAME: Final = "trade-republic-cash.json"
_BERLIN: Final = ZoneInfo("Europe/Berlin")

_ISSUER = "TRADE REPUBLIC BANK GMBH"
_CREATED_RE = re.compile(
    r"Erstellt\s+am\s+(\d{4}-\d{2}-\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2})\s+Europe/Berlin\s+\(UTC([+-]\d{2}:\d{2})\)",
    re.IGNORECASE,
)
_CASH_ROW_RE = re.compile(
    r"^\s*Cashkonto\s+"
    r"(?P<opening>-?(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2})\s*€\s+"
    r"(?P<incoming>-?(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2})\s*€\s+"
    r"(?P<outgoing>-?(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2})\s*€\s+"
    r"(?P<ending>-?(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2})\s*€\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_CASH_AS_OF_RE = re.compile(
    r"BARMITTELÜBERSICHT\s+Zum\s+(\d{1,2})\s+([A-Za-zÄÖÜäöü]{3})\.\s+(\d{4})",
    re.IGNORECASE,
)
_TRUST_SECTION_RE = re.compile(
    r"TREUHANDKONTEN\s+SALDO(?P<body>.*?)Trade Republic Bank GmbH",
    re.IGNORECASE | re.DOTALL,
)
_TRUST_VALUE_RE = re.compile(r"(?:^|\n)\s*[^\n€]{1,120}?\s+(-?(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2})\s*€\s*(?:$|\n)", re.MULTILINE)
_QMMF_SECTION_RE = re.compile(r"GELDMARKTFONDS(?P<body>.*?)HINWEISE ZUM KONTOAUSZUG", re.IGNORECASE | re.DOTALL)
_QMMF_LINE_RE = re.compile(
    r"^\s*[^\n]{1,160}?\s+[A-Z]{2}[A-Z0-9]{9}[0-9]\s+"
    r"(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]+\s+"
    r"(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2}\s*€\s+"
    r"((?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2})\s*€\s*$",
    re.MULTILINE,
)
_MONTHS: Final = {
    "jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4, "mai": 5, "may": 5,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "dez": 12,
}


class CashStatementImportError(ValueError):
    """A bounded privacy-safe reason for rejecting a cash statement."""


@dataclass(frozen=True, slots=True)
class TradeRepublicCashSnapshot:
    account_balance_eur: Decimal
    as_of: datetime
    generated_at: datetime

    @property
    def eligible_eur(self) -> Decimal:
        return max(Decimal("0"), self.account_balance_eur)

    def investment_cash(self) -> InvestmentCash:
        eligible = self.eligible_eur
        return InvestmentCash(
            account_balance_eur=self.account_balance_eur,
            eligible_eur=eligible,
            authorized_eur=eligible,
            policy="all_available",
            as_of=self.as_of,
        )


def parse_cash_statement_pdf(data: bytes, *, now: datetime | None = None) -> TradeRepublicCashSnapshot:
    try:
        text = extract_bounded_pdf_text(data)
    except TradeRepublicPdfError as err:
        raise CashStatementImportError(str(err)) from err
    return parse_cash_statement_text(text, now=now)


def parse_cash_statement_text(text: str, *, now: datetime | None = None) -> TradeRepublicCashSnapshot:
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_EXTRACTED_TEXT_CHARS:
        raise CashStatementImportError("Statement text is empty or too large")
    normalized = text.replace("\u00a0", " ").replace("\r", "")
    upper = normalized.upper()
    if "KONTOÜBERSICHT" not in upper or "BARMITTELÜBERSICHT" not in upper:
        raise CashStatementImportError("Unsupported Trade Republic document type")
    if _ISSUER not in upper:
        raise CashStatementImportError("Document issuer is not the supported Trade Republic statement format")

    generated_at = _unique_creation_timestamp(normalized)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if generated_at.astimezone(timezone.utc) > current + MAX_CLOCK_SKEW:
        raise CashStatementImportError("Statement creation timestamp is in the future")

    cash_rows = list(_CASH_ROW_RE.finditer(normalized))
    if len(cash_rows) != 1:
        raise CashStatementImportError("Statement contains an ambiguous Cashkonto summary")
    row = cash_rows[0]
    opening = _money(row.group("opening"), field="opening balance", signed=True)
    incoming = _money(row.group("incoming"), field="incoming payments", signed=False)
    outgoing = _money(row.group("outgoing"), field="outgoing payments", signed=False)
    ending = _money(row.group("ending"), field="ending balance", signed=True)
    if opening + incoming - outgoing != ending:
        raise CashStatementImportError("Cashkonto arithmetic does not reconcile")

    as_of_date = _unique_cash_as_of_date(normalized)
    if as_of_date > generated_at.astimezone(_BERLIN).date():
        raise CashStatementImportError("Cash statement as-of date is newer than document creation")
    as_of = datetime.combine(as_of_date, time(23, 59, 59), tzinfo=_BERLIN).astimezone(timezone.utc)

    trust_values = _trust_values(normalized)
    qmmf_values = _qmmf_values(normalized)
    custody_total = sum(trust_values, Decimal("0")) + sum(qmmf_values, Decimal("0"))
    if custody_total != ending:
        raise CashStatementImportError("Cash custody components do not reconcile with Cashkonto ending balance")

    return TradeRepublicCashSnapshot(
        account_balance_eur=ending,
        as_of=as_of,
        generated_at=generated_at.astimezone(timezone.utc),
    )


def save_cash_snapshot(path: Path, snapshot: TradeRepublicCashSnapshot | None) -> None:
    path = Path(path)
    if snapshot is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    save_json_state(
        path,
        {
            "schema_version": 1,
            "account_balance_eur": canonical_signed_decimal(snapshot.account_balance_eur),
            "as_of": snapshot.as_of.astimezone(timezone.utc).isoformat(),
            "generated_at": snapshot.generated_at.astimezone(timezone.utc).isoformat(),
        },
    )


def load_cash_snapshot(path: Path) -> TradeRepublicCashSnapshot | None:
    raw = load_json_state(Path(path))
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "account_balance_eur", "as_of", "generated_at"}:
        raise ProtocolError("Stored Trade Republic cash snapshot has an unexpected schema")
    if raw.get("schema_version") != 1:
        raise ProtocolError("Stored Trade Republic cash snapshot version is unsupported")
    try:
        amount = Decimal(str(raw["account_balance_eur"]))
        as_of = datetime.fromisoformat(str(raw["as_of"]))
        generated_at = datetime.fromisoformat(str(raw["generated_at"]))
    except (InvalidOperation, ValueError) as err:
        raise ProtocolError("Stored Trade Republic cash snapshot is invalid") from err
    if not amount.is_finite() or abs(amount) > MAX_CASH_EUR:
        raise ProtocolError("Stored Trade Republic cash snapshot amount is invalid")
    if as_of.tzinfo is None or generated_at.tzinfo is None:
        raise ProtocolError("Stored Trade Republic cash snapshot timestamp is invalid")
    return TradeRepublicCashSnapshot(amount, as_of.astimezone(timezone.utc), generated_at.astimezone(timezone.utc))


def _unique_creation_timestamp(text: str) -> datetime:
    matches = tuple(dict.fromkeys(_CREATED_RE.findall(text)))
    if len(matches) != 1:
        raise CashStatementImportError("Statement contains an ambiguous creation timestamp")
    date_token, time_token, offset_token = matches[0]
    try:
        offset_sign = 1 if offset_token[0] == "+" else -1
        hours, minutes = (int(part) for part in offset_token[1:].split(":"))
        if hours > 23 or minutes > 59:
            raise ValueError
        offset = timezone(offset_sign * timedelta(hours=hours, minutes=minutes))
        return datetime.fromisoformat(f"{date_token}T{time_token}").replace(tzinfo=offset)
    except ValueError as err:
        raise CashStatementImportError("Statement creation timestamp is invalid") from err


def _unique_cash_as_of_date(text: str) -> date:
    matches = tuple(dict.fromkeys(_CASH_AS_OF_RE.findall(text)))
    if len(matches) != 1:
        raise CashStatementImportError("Statement contains an ambiguous cash as-of date")
    day_token, month_token, year_token = matches[0]
    month = _MONTHS.get(month_token.casefold())
    if month is None:
        raise CashStatementImportError("Cash statement as-of date is invalid")
    try:
        return date(int(year_token), month, int(day_token))
    except ValueError as err:
        raise CashStatementImportError("Cash statement as-of date is invalid") from err


def _trust_values(text: str) -> tuple[Decimal, ...]:
    match = _TRUST_SECTION_RE.search(text)
    if match is None:
        raise CashStatementImportError("Cash statement trust-account section is missing")
    values = tuple(_money(token, field="trust-account balance", signed=True) for token in _TRUST_VALUE_RE.findall(match.group("body")))
    if not values or len(values) > 16:
        raise CashStatementImportError("Cash statement trust-account section is ambiguous")
    return values


def _qmmf_values(text: str) -> tuple[Decimal, ...]:
    match = _QMMF_SECTION_RE.search(text)
    if match is None:
        raise CashStatementImportError("Cash statement money-market-fund section is missing")
    values = tuple(_money(token, field="money-market-fund value", signed=False) for token in _QMMF_LINE_RE.findall(match.group("body")))
    if len(values) > 32:
        raise CashStatementImportError("Cash statement money-market-fund section is ambiguous")
    return values


def _money(token: str, *, field: str, signed: bool) -> Decimal:
    try:
        value = Decimal(token.replace(".", "").replace(",", "."))
    except InvalidOperation as err:
        raise CashStatementImportError(f"Statement {field} is invalid") from err
    if not value.is_finite() or abs(value) > MAX_CASH_EUR or (not signed and value < 0):
        raise CashStatementImportError(f"Statement {field} is outside the supported range")
    if -value.as_tuple().exponent > 2:
        raise CashStatementImportError(f"Statement {field} has unsupported precision")
    return value
