"""Strict in-memory DKB depot-CSV acquisition for the provider Gateway.

Raw exports and depot identifiers are transient.  The only persistent holdings state is
one provider-neutral canonical :class:`PortfolioSnapshot` written by the common Gateway
store after a successful import activation.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import re
from pathlib import Path
from typing import Final, Iterable

from .dkb_cash_csv import (
    CASH_STATE_FILE_NAME,
    DkbCashSnapshot,
    load_cash_snapshot,
    save_cash_snapshot,
)
from .errors import ConfigurationError, ProtocolError
from .models import PortfolioSnapshot, Position, validate_snapshot
from .store import load_snapshot

D = Decimal
PROVIDER_ID: Final = "dkb"
MAX_CSV_FILES: Final = 8
MAX_CSV_FILE_BYTES: Final = 10 * 1024 * 1024
MAX_CSV_BATCH_BYTES: Final = 20 * 1024 * 1024
MAX_CSV_ROWS: Final = 4096
MAX_POSITIONS: Final = 512
MAX_POSITION_VALUE_EUR: Final = D("1000000000")
MAX_NAME_LENGTH: Final = 160
MAX_SOURCE_TYPE_LENGTH: Final = 64

_IDENTIFIER_RE: Final = re.compile(r"^[A-Z0-9][A-Z0-9._:/+-]{3,15}$")
_ISIN_RE: Final = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_REQUIRED_COLUMNS: Final = frozenset(
    {
        "Datum der Erstellung",
        "Depotnummer",
        "Wertpapierbezeichnung",
        "WKN",
        "ISIN",
        "Bewertungskurs",
        "Stückzahl",
        "Assetklasse",
    }
)
_INSTRUMENT_TYPE_MAP: Final = {
    "etf": "etf",
    "etfs": "etf",
    "exchange traded fund": "etf",
    "aktie": "stock",
    "aktien": "stock",
    "stock": "stock",
    "share": "stock",
    "fonds": "fund",
    "funds": "fund",
    "fund": "fund",
    "investmentfonds": "fund",
    "mutual fund": "fund",
    "anleihe": "bond",
    "anleihen": "bond",
    "bond": "bond",
    "zertifikat": "certificate",
    "certificate": "certificate",
    "optionsschein": "warrant",
    "warrant": "warrant",
    "etc": "commodity",
    "commodity": "commodity",
    "etn": "note",
    "note": "note",
}


class DkbCsvImportError(ValueError):
    """Privacy-safe rejection reason for one DKB CSV import batch."""


@dataclass(frozen=True, slots=True)
class DkbCsvDocument:
    """One validated transient export before newest-per-depot selection."""

    generated_at: datetime
    depot_key: str
    sha256: str
    positions: tuple[Position, ...]


@dataclass(frozen=True, slots=True)
class DkbCsvImportSummary:
    """Non-identifying import metadata safe for the admin-only UI."""

    input_file_count: int
    selected_depot_count: int
    position_count: int
    generated_at: datetime


class DkbCsvProvider:
    """Static DKB provider with independent holdings and Girokonto cash evidence."""

    def __init__(self, snapshot_file: Path) -> None:
        self._snapshot_file = Path(snapshot_file)
        self._cash_file = self._snapshot_file.parent / CASH_STATE_FILE_NAME
        try:
            loaded = load_snapshot(self._snapshot_file)
            self._holdings_snapshot = _holdings_only(loaded) if loaded is not None else None
            self._cash_snapshot = load_cash_snapshot(self._cash_file)
            if self._cash_snapshot is None and loaded is not None and loaded.investment_cash is not None:
                # Recovery compatibility: retain only the bounded normalized cash facts
                # if the composed canonical snapshot survived but sibling cash state did not.
                self._cash_snapshot = DkbCashSnapshot(
                    account_balance_eur=loaded.investment_cash.account_balance_eur,
                    as_of=loaded.investment_cash.as_of,
                    generated_at=loaded.investment_cash.as_of,
                )
        except ProtocolError as err:
            raise ConfigurationError("Stored DKB private snapshot is invalid") from err

    @property
    def provider_id(self) -> str:
        return PROVIDER_ID

    @property
    def acquisition_mode(self) -> str:
        return "csv"

    @property
    def poll_interval_seconds(self) -> int:
        # CSV imports are explicit user actions; no bank or filesystem polling occurs.
        return 86400

    def fetch_snapshot(self) -> PortfolioSnapshot:
        snapshot = self.snapshot
        if snapshot is None:
            raise ConfigurationError("No supported DKB depot CSV batch has been imported")
        return snapshot

    @property
    def holdings_snapshot(self) -> PortfolioSnapshot | None:
        return self._holdings_snapshot

    @property
    def cash_snapshot(self) -> DkbCashSnapshot | None:
        return self._cash_snapshot

    @property
    def snapshot(self) -> PortfolioSnapshot | None:
        if self._holdings_snapshot is None:
            return None
        if self._cash_snapshot is None:
            return self._holdings_snapshot
        cash = self._cash_snapshot.investment_cash()
        return validate_snapshot(
            PortfolioSnapshot(
                generated_at=self._holdings_snapshot.generated_at,
                positions=self._holdings_snapshot.positions,
                investment_reserve_eur=cash.authorized_eur,
                investment_reserve_as_of=cash.as_of,
                investment_cash=cash,
            )
        )

    @property
    def snapshot_file(self) -> Path:
        return self._snapshot_file

    @property
    def cash_file(self) -> Path:
        return self._cash_file

    def replace_snapshot(self, snapshot: PortfolioSnapshot | None) -> None:
        self._holdings_snapshot = _holdings_only(snapshot) if snapshot is not None else None

    def replace_cash_snapshot(self, snapshot: DkbCashSnapshot | None) -> None:
        self._cash_snapshot = snapshot

    def persist_cash_snapshot(self, snapshot: DkbCashSnapshot | None) -> None:
        save_cash_snapshot(self._cash_file, snapshot)


def _holdings_only(snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
    """Strip optional cash from a loaded/composed canonical snapshot."""
    return validate_snapshot(
        PortfolioSnapshot(
            generated_at=snapshot.generated_at,
            positions=snapshot.positions,
        )
    )


def parse_dkb_csv_batch(documents: Iterable[bytes]) -> tuple[PortfolioSnapshot, DkbCsvImportSummary]:
    """Parse a bounded authoritative DKB export batch into one canonical snapshot."""
    raw_documents = tuple(documents)
    if not 1 <= len(raw_documents) <= MAX_CSV_FILES:
        raise DkbCsvImportError(f"Import must contain between 1 and {MAX_CSV_FILES} DKB CSV files")
    if sum(len(item) for item in raw_documents) > MAX_CSV_BATCH_BYTES:
        raise DkbCsvImportError("DKB CSV import batch exceeds the 20 MiB safety limit")

    parsed = tuple(_parse_document(item) for item in raw_documents)
    selected = _select_latest_per_depot(parsed)
    snapshot = _aggregate_selected(selected)
    return snapshot, DkbCsvImportSummary(
        input_file_count=len(parsed),
        selected_depot_count=len(selected),
        position_count=len(snapshot.positions),
        generated_at=snapshot.generated_at,
    )


def _parse_document(data: bytes) -> DkbCsvDocument:
    if not isinstance(data, bytes) or not data or len(data) > MAX_CSV_FILE_BYTES:
        raise DkbCsvImportError("DKB CSV is empty or exceeds the 10 MiB per-file limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as err:
        raise DkbCsvImportError("DKB CSV must use UTF-8 encoding") from err

    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=";", quotechar='"'))
    except csv.Error as err:
        raise DkbCsvImportError("DKB CSV could not be parsed safely") from err
    if not rows:
        raise DkbCsvImportError("DKB CSV is empty")
    if len(rows) > MAX_CSV_ROWS:
        raise DkbCsvImportError(f"DKB CSV may contain at most {MAX_CSV_ROWS} rows")

    header = rows[0]
    if len(set(header)) != len(header):
        raise DkbCsvImportError("DKB CSV contains duplicate header names")
    if not _REQUIRED_COLUMNS.issubset(set(header)):
        raise DkbCsvImportError("DKB CSV does not contain the required depot-export columns")

    date_index = header.index("Datum der Erstellung")
    depot_index = header.index("Depotnummer")
    dates: set[str] = set()
    depots: set[str] = set()
    positions: dict[str, Position] = {}

    for row_number, raw_row in enumerate(rows[1:], start=2):
        if not raw_row or all(not str(value).strip() for value in raw_row):
            continue
        row = list(raw_row)
        if len(row) < len(header):
            row.extend([""] * (len(header) - len(row)))
        if len(row) > len(header):
            raise DkbCsvImportError("DKB CSV row contains more fields than the header")
        if row[date_index].strip():
            dates.add(row[date_index].strip())
        if row[depot_index].strip():
            depots.add(row[depot_index].strip())
        record = dict(zip(header, row, strict=True))

        identifier = str(record.get("WKN", "")).strip().upper()
        if not identifier:
            continue
        if _IDENTIFIER_RE.fullmatch(identifier) is None:
            raise DkbCsvImportError(f"DKB CSV row {row_number} contains an invalid instrument identifier")
        isin = str(record.get("ISIN", "")).strip().upper()
        if isin and _ISIN_RE.fullmatch(isin) is None:
            raise DkbCsvImportError(f"DKB CSV row {row_number} contains an invalid ISIN")
        name = _clean_text(record.get("Wertpapierbezeichnung", ""), field="position name", maximum=MAX_NAME_LENGTH)
        source_type = _clean_text(record.get("Assetklasse", "Other") or "Other", field="instrument type", maximum=MAX_SOURCE_TYPE_LENGTH)
        price = _parse_german_decimal(record.get("Bewertungskurs", "0"), field="valuation price")
        quantity = _parse_german_decimal(record.get("Stückzahl", "0"), field="quantity")
        if price < 0 or quantity < 0:
            raise DkbCsvImportError(f"DKB CSV row {row_number} contains a negative price or quantity")
        value_eur = price * quantity
        if value_eur > MAX_POSITION_VALUE_EUR:
            raise DkbCsvImportError(f"DKB CSV row {row_number} position value is outside the allowed range")
        candidate = Position(
            identifier=identifier,
            isin=isin,
            name=name,
            instrument_type=_INSTRUMENT_TYPE_MAP.get(source_type.strip().casefold(), "other"),
            market_value_eur=value_eur,
            quantity=quantity,
        )
        existing = positions.get(identifier)
        if existing is None:
            if len(positions) >= MAX_POSITIONS:
                raise DkbCsvImportError(f"DKB CSV may contain at most {MAX_POSITIONS} positions")
            positions[identifier] = candidate
            continue
        if existing.isin != candidate.isin or existing.instrument_type != candidate.instrument_type:
            raise DkbCsvImportError("DKB CSV contains conflicting rows for one instrument identifier")
        merged_value = existing.market_value_eur + candidate.market_value_eur
        if merged_value > MAX_POSITION_VALUE_EUR:
            raise DkbCsvImportError(f"DKB CSV row {row_number} position value is outside the allowed range")
        positions[identifier] = Position(
            identifier=existing.identifier,
            isin=existing.isin,
            name=existing.name,
            instrument_type=existing.instrument_type,
            market_value_eur=merged_value,
            quantity=(existing.quantity or D("0")) + (candidate.quantity or D("0")),
        )

    if len(dates) != 1 or len(depots) != 1:
        raise DkbCsvImportError("DKB CSV must describe exactly one depot and one export date")
    if not positions:
        raise DkbCsvImportError("No valid securities positions found in DKB export")
    date_token = next(iter(dates))
    try:
        generated_date = datetime.strptime(date_token, "%d.%m.%Y").date()
    except ValueError as err:
        raise DkbCsvImportError("DKB CSV contains an invalid export date") from err
    generated_at = datetime.combine(generated_date, time.min, tzinfo=timezone.utc)

    return DkbCsvDocument(
        generated_at=generated_at,
        depot_key=next(iter(depots)),
        sha256=hashlib.sha256(data).hexdigest(),
        positions=tuple(positions.values()),
    )


def _select_latest_per_depot(documents: tuple[DkbCsvDocument, ...]) -> tuple[DkbCsvDocument, ...]:
    selected: dict[str, DkbCsvDocument] = {}
    for document in documents:
        existing = selected.get(document.depot_key)
        if existing is None or document.generated_at > existing.generated_at:
            selected[document.depot_key] = document
            continue
        if document.generated_at < existing.generated_at:
            continue
        if document.sha256 != existing.sha256:
            raise DkbCsvImportError("Multiple DKB exports for the same depot and date contain different data")
        # Identical duplicate: retain the first document deterministically.
    return tuple(selected.values())


def _aggregate_selected(documents: tuple[DkbCsvDocument, ...]) -> PortfolioSnapshot:
    if not documents:
        raise DkbCsvImportError("DKB CSV import selected no usable exports")

    groups: dict[str, list[Position]] = {}
    for document in documents:
        for position in document.positions:
            identity = position.isin or position.identifier
            groups.setdefault(identity, []).append(position)

    aggregate: list[Position] = []
    for identity in sorted(groups):
        members = groups[identity]
        identifiers = tuple(dict.fromkeys(item.identifier for item in members if item.identifier))
        isins = tuple(dict.fromkeys(item.isin for item in members if item.isin))
        if len(identifiers) > 1 or len(isins) > 1:
            raise DkbCsvImportError("DKB exports contain conflicting instrument identity across depots")
        total = sum((item.market_value_eur for item in members), D("0"))
        if total > MAX_POSITION_VALUE_EUR:
            raise DkbCsvImportError("Aggregated DKB position value is outside the allowed range")
        quantities = tuple(item.quantity for item in members)
        quantity = (
            sum((item for item in quantities if item is not None), D("0"))
            if all(item is not None for item in quantities)
            else None
        )
        types = tuple(dict.fromkeys(item.instrument_type for item in members))
        primary = members[0]
        aggregate.append(
            Position(
                identifier=identifiers[0] if identifiers else (isins[0] if isins else identity),
                isin=isins[0] if isins else "",
                name=primary.name,
                instrument_type=types[0] if len(types) == 1 else "other",
                market_value_eur=total,
                quantity=quantity,
            )
        )
    if len(aggregate) > MAX_POSITIONS:
        raise DkbCsvImportError(f"DKB snapshot may contain at most {MAX_POSITIONS} positions")

    try:
        return validate_snapshot(
            PortfolioSnapshot(
                generated_at=min(item.generated_at for item in documents),
                positions=tuple(aggregate),
            )
        )
    except ProtocolError as err:
        raise DkbCsvImportError("Parsed DKB CSV batch violates the canonical snapshot contract") from err


def _parse_german_decimal(value: object, *, field: str) -> Decimal:
    cleaned = (
        str(value or "")
        .strip()
        .replace("\u00a0", "")
        .replace(" ", "")
        .replace("EUR", "")
        .replace("€", "")
    )
    if not cleaned or cleaned == "--":
        return D("0")
    normalized = cleaned.replace(".", "").replace(",", ".")
    try:
        result = D(normalized)
    except InvalidOperation as err:
        raise DkbCsvImportError(f"DKB CSV {field} is invalid") from err
    if not result.is_finite():
        raise DkbCsvImportError(f"DKB CSV {field} must be finite")
    return result


def _clean_text(value: object, *, field: str, maximum: int) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise DkbCsvImportError(f"DKB CSV {field} is required")
    if len(cleaned) > maximum or any(ord(char) < 32 for char in cleaned):
        raise DkbCsvImportError(f"DKB CSV {field} is too long or contains control characters")
    return cleaned
