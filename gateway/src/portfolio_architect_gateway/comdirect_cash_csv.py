"""Bounded provider-local parser for Comdirect Girokonto transaction CSV cash evidence."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import io
from pathlib import Path
import re
from typing import Final

from .cash_policy import InvestmentCashPolicy
from .errors import ProtocolError
from .models import InvestmentCash, MAX_POSITION_VALUE_EUR, canonical_signed_decimal
from .store import load_json_state, save_json_state

MAX_CASH_CSV_BYTES: Final = 2 * 1024 * 1024
MAX_CASH_CSV_ROWS: Final = 8192
_EXPECTED_HEADER: Final = (
    "Buchungstag",
    "Wertstellung (Valuta)",
    "Vorgang",
    "Buchungstext",
    "Umsatz in EUR",
)
_CLOSING_BALANCE_LABELS: Final = frozenset({"kontostand neu", "neuer kontostand"})
_OPENING_BALANCE_LABELS: Final = frozenset({"kontostand alt", "alter kontostand"})
_GERMAN_MONEY_RE: Final = re.compile(r"^-?(?:[0-9]{1,3}(?:\.[0-9]{3})*|[0-9]+)(?:,[0-9]{1,2})?$")
CASH_STATE_FILE_NAME: Final = "comdirect-csv-cash.json"


class ComdirectCashCsvImportError(ValueError):
    """Privacy-safe reason for rejecting one Comdirect cash export."""


@dataclass(frozen=True, slots=True)
class ComdirectCashSnapshot:
    account_balance_eur: Decimal
    as_of: datetime

    def investment_cash(self, policy: InvestmentCashPolicy) -> InvestmentCash:
        eligible = max(Decimal("0"), self.account_balance_eur)
        authorized = policy.authorize(eligible)
        return InvestmentCash(
            account_balance_eur=self.account_balance_eur,
            eligible_eur=eligible,
            authorized_eur=authorized,
            policy=policy.mode,
            as_of=self.as_of,
            cap_eur=policy.cap_eur,
            retain_eur=policy.retain_eur,
        )


def parse_comdirect_cash_csv(
    data: bytes, *, now: datetime | None = None
) -> ComdirectCashSnapshot:
    """Accept only an explicit closing balance; never reconstruct cash from transactions."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_CASH_CSV_BYTES:
        raise ComdirectCashCsvImportError(
            "Comdirect cash CSV is empty or exceeds the 2 MiB safety limit"
        )
    text = _decode(data)
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=";", quotechar='"'))
    except csv.Error as err:
        raise ComdirectCashCsvImportError("Comdirect cash CSV could not be parsed safely") from err
    if not rows or len(rows) > MAX_CASH_CSV_ROWS:
        raise ComdirectCashCsvImportError("Comdirect cash CSV contains too many rows")

    normalized_rows = [tuple(str(value).strip() for value in row) for row in rows]
    header_indexes = [
        index for index, row in enumerate(normalized_rows) if _trim_trailing_empty(row) == _EXPECTED_HEADER
    ]
    if len(header_indexes) != 1:
        raise ComdirectCashCsvImportError(
            "Comdirect cash CSV must contain exactly one supported transaction table"
        )
    header_index = header_indexes[0]

    closing_matches = _balance_matches(
        normalized_rows[:header_index],
        labels=_CLOSING_BALANCE_LABELS,
        kind="closing",
    )
    if len(closing_matches) != 1:
        raise ComdirectCashCsvImportError(
            "Comdirect cash CSV does not contain exactly one explicit closing balance"
        )

    footer_indexes: list[int] = []
    opening_matches: list[Decimal] = []
    for index, row in enumerate(normalized_rows[header_index + 1 :], start=header_index + 1):
        matches = _balance_matches((row,), labels=_OPENING_BALANCE_LABELS, kind="opening")
        if not matches:
            continue
        footer_indexes.append(index)
        opening_matches.extend(matches)
    if len(footer_indexes) != 1 or len(opening_matches) != 1:
        raise ComdirectCashCsvImportError(
            "Comdirect cash CSV does not contain exactly one explicit opening balance"
        )
    footer_index = footer_indexes[0]

    expected_row = _EXPECTED_HEADER
    transaction_total = Decimal("0")
    for row in normalized_rows[header_index + 1 : footer_index]:
        trimmed = _trim_trailing_empty(row)
        if not trimmed:
            continue
        # Read only bounded dates/amount for structural and arithmetic integrity; free-text
        # transaction fields remain transient and are never persisted or returned.
        if len(trimmed) != len(expected_row):
            raise ComdirectCashCsvImportError("Comdirect cash CSV contains a malformed transaction row")
        _validate_booking_date(trimmed[0])
        _validate_booking_date(trimmed[1])
        transaction_total += _parse_money(trimmed[4])

    for row in normalized_rows[footer_index + 1 :]:
        if _trim_trailing_empty(row):
            raise ComdirectCashCsvImportError(
                "Comdirect cash CSV contains unexpected data after the opening balance"
            )

    closing_balance = closing_matches[0]
    if opening_matches[0] + transaction_total != closing_balance:
        raise ComdirectCashCsvImportError(
            "Comdirect cash CSV opening balance and transactions do not reconcile to the closing balance"
        )

    imported_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return ComdirectCashSnapshot(account_balance_eur=closing_balance, as_of=imported_at)


def save_cash_snapshot(path: Path, snapshot: ComdirectCashSnapshot | None) -> None:
    if snapshot is None:
        Path(path).unlink(missing_ok=True)
        return
    save_json_state(
        Path(path),
        {
            "schema_version": 1,
            "account_balance_eur": canonical_signed_decimal(snapshot.account_balance_eur),
            "as_of": snapshot.as_of.astimezone(timezone.utc).isoformat(),
        },
    )


def load_cash_snapshot(path: Path) -> ComdirectCashSnapshot | None:
    raw = load_json_state(Path(path))
    if raw is None:
        return None
    if set(raw) != {"schema_version", "account_balance_eur", "as_of"} or raw.get("schema_version") != 1:
        raise ProtocolError("Stored Comdirect CSV cash snapshot has an unexpected schema")
    try:
        amount = Decimal(str(raw["account_balance_eur"]))
        as_of = datetime.fromisoformat(str(raw["as_of"]))
    except (InvalidOperation, ValueError) as err:
        raise ProtocolError("Stored Comdirect CSV cash snapshot is invalid") from err
    if not amount.is_finite() or abs(amount) > MAX_POSITION_VALUE_EUR:
        raise ProtocolError("Stored Comdirect CSV cash amount is invalid")
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ProtocolError("Stored Comdirect CSV cash timestamp is invalid")
    return ComdirectCashSnapshot(amount, as_of.astimezone(timezone.utc))



def _balance_matches(
    rows: tuple[tuple[str, ...], ...] | list[tuple[str, ...]],
    *,
    labels: frozenset[str],
    kind: str,
) -> list[Decimal]:
    matches: list[Decimal] = []
    for row in rows:
        if not row or not any(row):
            continue
        for index, value in enumerate(row):
            if _normalize_label(value) not in labels:
                continue
            amount_tokens = [token for token in row[index + 1 :] if token]
            if len(amount_tokens) != 1:
                raise ComdirectCashCsvImportError(
                    f"Comdirect cash CSV {kind}-balance row is ambiguous"
                )
            matches.append(_parse_money(amount_tokens[0]))
    return matches


def _validate_booking_date(value: str) -> None:
    try:
        datetime.strptime(str(value).strip(), "%d.%m.%Y")
    except ValueError as err:
        raise ComdirectCashCsvImportError(
            "Comdirect cash CSV contains an invalid transaction date"
        ) from err

def _decode(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError as err:
            raise ComdirectCashCsvImportError("Comdirect cash CSV encoding is invalid") from err
    return data.decode("iso-8859-1")


def _trim_trailing_empty(row: tuple[str, ...]) -> tuple[str, ...]:
    values = list(row)
    while values and not values[-1]:
        values.pop()
    return tuple(values)


def _normalize_label(value: str) -> str:
    return " ".join(value.strip().rstrip(":").casefold().split())


def _parse_money(value: str) -> Decimal:
    token = str(value).replace("\u00a0", " ").strip()
    for suffix in ("EUR", "€"):
        if token.upper().endswith(suffix if suffix == "EUR" else "€"):
            token = token[: -len(suffix)].strip()
            break
    token = token.replace(" ", "")
    if _GERMAN_MONEY_RE.fullmatch(token) is None:
        raise ComdirectCashCsvImportError("Comdirect cash CSV closing balance is invalid")
    try:
        amount = Decimal(token.replace(".", "").replace(",", "."))
    except InvalidOperation as err:
        raise ComdirectCashCsvImportError("Comdirect cash CSV closing balance is invalid") from err
    if not amount.is_finite() or abs(amount) > MAX_POSITION_VALUE_EUR:
        raise ComdirectCashCsvImportError("Comdirect cash CSV closing balance is outside the allowed range")
    return amount
