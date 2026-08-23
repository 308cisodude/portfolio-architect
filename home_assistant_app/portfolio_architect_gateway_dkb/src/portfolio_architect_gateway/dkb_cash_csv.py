"""Strict local DKB Girokonto cash-evidence CSV importer.

Only the bounded provider-scoped balance result is retained. Account identifiers,
transaction rows, counterparties, references, and the uploaded CSV never persist.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import io
from pathlib import Path
import re
from typing import Final
from zoneinfo import ZoneInfo

from .errors import ProtocolError
from .models import InvestmentCash, canonical_signed_decimal
from .store import load_json_state, save_json_state

MAX_CASH_CSV_BYTES: Final = 2 * 1024 * 1024
MAX_CASH_CSV_ROWS: Final = 8192
MAX_CASH_EUR: Final = Decimal("1000000000")
MAX_CLOCK_SKEW: Final = timedelta(minutes=5)
CASH_STATE_FILE_NAME: Final = "dkb-cash.json"
_BERLIN: Final = ZoneInfo("Europe/Berlin")
_ACCOUNT_ROW_LABEL: Final = "Girokonto"
_ACCOUNT_ID_RE: Final = re.compile(r"^DE[0-9]{20}$")
_BALANCE_LABEL_RE: Final = re.compile(r"^Kontostand vom (\d{2}\.\d{2}\.\d{4}):$")
_GERMAN_MONEY_RE: Final = re.compile(r"^-?(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)(?:,[0-9]{1,2})?$")
_EXPECTED_HEADER: Final = (
    "Buchungsdatum",
    "Wertstellung",
    "Status",
    "Zahlungspflichtige*r",
    "Zahlungsempfänger*in",
    "Verwendungszweck",
    "Umsatztyp",
    "IBAN",
    "Betrag (€)",
    "Gläubiger-ID",
    "Mandatsreferenz",
    "Kundenreferenz",
)


class DkbCashCsvImportError(ValueError):
    """A bounded privacy-safe reason for rejecting one DKB cash export."""


@dataclass(frozen=True, slots=True)
class DkbCashSnapshot:
    """One normalized DKB current-account balance evidence item."""

    account_balance_eur: Decimal
    as_of: datetime
    generated_at: datetime

    @property
    def eligible_eur(self) -> Decimal:
        """Never turn a negative account balance or overdraft into investment cash."""
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


def parse_dkb_cash_csv(data: bytes, *, now: datetime | None = None) -> DkbCashSnapshot:
    """Parse one bounded DKB Girokonto Umsatzliste CSV without retaining transaction data."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_CASH_CSV_BYTES:
        raise DkbCashCsvImportError("DKB cash CSV is empty or exceeds the 2 MiB safety limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as err:
        raise DkbCashCsvImportError("DKB cash CSV must use UTF-8 encoding") from err

    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=";", quotechar='"'))
    except csv.Error as err:
        raise DkbCashCsvImportError("DKB cash CSV could not be parsed safely") from err
    if not rows or len(rows) > MAX_CASH_CSV_ROWS:
        raise DkbCashCsvImportError("DKB cash CSV is empty or contains too many rows")

    nonempty = [
        (index, row)
        for index, row in enumerate(rows)
        if row and any(str(value).strip() for value in row)
    ]
    if len(nonempty) < 3:
        raise DkbCashCsvImportError(
            "DKB cash CSV does not contain the required account, balance, and transaction-header rows"
        )

    account_rows = [
        (index, row)
        for index, row in nonempty
        if row and str(row[0]).strip() == _ACCOUNT_ROW_LABEL
    ]
    if len(account_rows) != 1:
        raise DkbCashCsvImportError("DKB cash CSV contains an ambiguous Girokonto account row")
    account_index, account_row = account_rows[0]
    if len(account_row) != 2 or _ACCOUNT_ID_RE.fullmatch(str(account_row[1]).strip()) is None:
        raise DkbCashCsvImportError("DKB cash CSV account row is invalid")

    balance_rows: list[tuple[int, list[str], str]] = []
    for index, row in nonempty:
        match = _BALANCE_LABEL_RE.fullmatch(str(row[0]).strip())
        if match is not None:
            balance_rows.append((index, row, match.group(1)))
    if len(balance_rows) != 1:
        raise DkbCashCsvImportError("DKB cash CSV contains an ambiguous current-balance row")
    balance_index, balance_row, balance_date_token = balance_rows[0]
    if len(balance_row) != 2:
        raise DkbCashCsvImportError("DKB cash CSV current-balance row is invalid")
    balance = _parse_money(balance_row[1])

    header_rows = [
        (index, tuple(str(value).strip() for value in row))
        for index, row in nonempty
        if tuple(str(value).strip() for value in row) == _EXPECTED_HEADER
    ]
    if len(header_rows) != 1:
        raise DkbCashCsvImportError(
            "DKB cash CSV does not contain exactly one supported transaction header"
        )
    header_index, _header = header_rows[0]
    if not account_index < balance_index < header_index:
        raise DkbCashCsvImportError("DKB cash CSV structural row order is invalid")

    # Transaction values are deliberately not interpreted. Structural validation is
    # enough to establish the supported export family without retaining private rows.
    for row in rows[header_index + 1 :]:
        if not row or not any(str(value).strip() for value in row):
            continue
        if len(row) != len(_EXPECTED_HEADER):
            raise DkbCashCsvImportError("DKB cash CSV contains a malformed transaction row")

    try:
        balance_date = datetime.strptime(balance_date_token, "%d.%m.%Y").date()
    except ValueError as err:
        raise DkbCashCsvImportError("DKB cash CSV contains an invalid balance date") from err

    current_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    current_local = current_utc.astimezone(_BERLIN)
    if balance_date > current_local.date():
        raise DkbCashCsvImportError("DKB cash CSV balance date is in the future")

    # The export has a date but no trustworthy creation time. Local midnight is a
    # deterministic conservative evidence timestamp, so re-importing an old file
    # cannot make it fresh merely by changing upload time.
    as_of = datetime.combine(balance_date, time.min, tzinfo=_BERLIN).astimezone(timezone.utc)
    if as_of > current_utc + MAX_CLOCK_SKEW:
        raise DkbCashCsvImportError("DKB cash CSV balance timestamp is in the future")

    return DkbCashSnapshot(
        account_balance_eur=balance,
        as_of=as_of,
        generated_at=as_of,
    )


def save_cash_snapshot(path: Path, snapshot: DkbCashSnapshot | None) -> None:
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


def load_cash_snapshot(path: Path) -> DkbCashSnapshot | None:
    raw = load_json_state(Path(path))
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "account_balance_eur",
        "as_of",
        "generated_at",
    }:
        raise ProtocolError("Stored DKB cash snapshot has an unexpected schema")
    if raw.get("schema_version") != 1:
        raise ProtocolError("Stored DKB cash snapshot version is unsupported")
    try:
        amount = Decimal(str(raw["account_balance_eur"]))
        as_of = datetime.fromisoformat(str(raw["as_of"]))
        generated_at = datetime.fromisoformat(str(raw["generated_at"]))
    except (InvalidOperation, ValueError) as err:
        raise ProtocolError("Stored DKB cash snapshot is invalid") from err
    if not amount.is_finite() or abs(amount) > MAX_CASH_EUR:
        raise ProtocolError("Stored DKB cash snapshot amount is invalid")
    if as_of.tzinfo is None or generated_at.tzinfo is None:
        raise ProtocolError("Stored DKB cash snapshot timestamp is invalid")
    return DkbCashSnapshot(
        account_balance_eur=amount,
        as_of=as_of.astimezone(timezone.utc),
        generated_at=generated_at.astimezone(timezone.utc),
    )


def _parse_money(value: str) -> Decimal:
    token = str(value).replace("\u00a0", " ").strip()
    if not token.endswith("€"):
        raise DkbCashCsvImportError("DKB cash CSV current balance must be denominated in EUR")
    number = token[:-1].strip().replace(" ", "")
    if _GERMAN_MONEY_RE.fullmatch(number) is None:
        raise DkbCashCsvImportError("DKB cash CSV current balance is invalid")
    try:
        amount = Decimal(number.replace(".", "").replace(",", "."))
    except InvalidOperation as err:
        raise DkbCashCsvImportError("DKB cash CSV current balance is invalid") from err
    if not amount.is_finite() or abs(amount) > MAX_CASH_EUR:
        raise DkbCashCsvImportError("DKB cash CSV current balance is outside the allowed range")
    return amount
