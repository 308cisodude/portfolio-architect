"""Bounded provider-local parser for Comdirect depot CSV exports."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import io
import re
from typing import Final

from .models import MAX_POSITIONS, MAX_POSITION_VALUE_EUR, PortfolioSnapshot, Position, validate_snapshot

MAX_CSV_FILE_BYTES: Final = 10 * 1024 * 1024
MAX_CSV_ROWS: Final = 4096
_MAX_NAME_LENGTH: Final = 160
_MAX_SOURCE_TYPE_LENGTH: Final = 64
_IDENTIFIER_RE: Final = re.compile(r"^[A-Z0-9][A-Z0-9._:/+-]{3,15}$")
_ISIN_RE: Final = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_GERMAN_NUMBER_RE: Final = re.compile(r"^(?:[0-9]{1,3}(?:\.[0-9]{3})*|[0-9]+)(?:,[0-9]+)?$")
_INSTRUMENT_TYPE_MAP: Final = {
    "etf": "ETF",
    "etfs": "ETF",
    "exchange traded fund": "ETF",
    "aktie": "Stock",
    "aktien": "Stock",
    "stock": "Stock",
    "share": "Stock",
    "fonds": "Fund",
    "funds": "Fund",
    "fund": "Fund",
    "investmentfonds": "Fund",
    "mutual fund": "Fund",
    "anleihe": "Bond",
    "anleihen": "Bond",
    "bond": "Bond",
    "zertifikat": "Certificate",
    "certificate": "Certificate",
    "optionsschein": "Warrant",
    "warrant": "Warrant",
    "etc": "Commodity",
    "commodity": "Commodity",
    "etn": "Note",
    "note": "Note",
}


class ComdirectCsvImportError(ValueError):
    """Privacy-safe reason for rejecting one Comdirect depot export."""


def parse_comdirect_holdings_csv(
    data: bytes, *, now: datetime | None = None
) -> PortfolioSnapshot:
    """Parse one authoritative Comdirect depot CSV entirely in memory.

    The historical Portfolio Architect adapter used the local file mtime as a
    freshness proxy. A Gateway upload has no bank-issued export timestamp in the
    supported CSV table, so the explicit import time is the evidence timestamp.
    """
    if not isinstance(data, bytes) or not data or len(data) > MAX_CSV_FILE_BYTES:
        raise ComdirectCsvImportError(
            "Comdirect depot CSV is empty or exceeds the 10 MiB safety limit"
        )
    try:
        text = data.decode("iso-8859-1")
    except UnicodeDecodeError as err:  # pragma: no cover - codec is total for bytes
        raise ComdirectCsvImportError("Comdirect depot CSV encoding is invalid") from err
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=";", quotechar='"'))
    except csv.Error as err:
        raise ComdirectCsvImportError("Comdirect depot CSV could not be parsed safely") from err
    if not rows or len(rows) > MAX_CSV_ROWS:
        raise ComdirectCsvImportError("Comdirect depot CSV contains too many rows")

    header_indexes = [
        index
        for index, row in enumerate(rows)
        if "WKN" in row and "Wert in EUR" in row
    ]
    if len(header_indexes) != 1:
        raise ComdirectCsvImportError(
            "Comdirect depot CSV must contain exactly one supported securities table"
        )
    header_index = header_indexes[0]
    header = tuple(str(value).strip() for value in rows[header_index])
    if len(set(header)) != len(header):
        raise ComdirectCsvImportError("Comdirect depot CSV contains duplicate header names")

    positions: list[Position] = []
    identifiers: set[str] = set()
    isins: set[str] = set()
    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not row or all(not str(value).strip() for value in row):
            continue
        if len(row) < len(header):
            continue
        record = dict(zip(header, row, strict=False))
        identifier = str(record.get("WKN") or "").strip().upper()
        if not identifier:
            continue
        if _IDENTIFIER_RE.fullmatch(identifier) is None:
            raise ComdirectCsvImportError(
                f"Comdirect depot CSV row {row_number} contains an invalid WKN"
            )
        if identifier in identifiers:
            raise ComdirectCsvImportError("Comdirect depot CSV contains a duplicate WKN")
        isin = str(record.get("ISIN") or "").strip().upper()
        if isin and _ISIN_RE.fullmatch(isin) is None:
            raise ComdirectCsvImportError(
                f"Comdirect depot CSV row {row_number} contains an invalid ISIN"
            )
        if isin and isin in isins:
            raise ComdirectCsvImportError("Comdirect depot CSV contains a duplicate ISIN")
        name = _bounded_text(
            record.get("Bezeichnung", ""),
            maximum=_MAX_NAME_LENGTH,
            label=f"Comdirect depot CSV row {row_number} name",
        )
        source_type = _bounded_text(
            record.get("Typ", ""),
            maximum=_MAX_SOURCE_TYPE_LENGTH,
            label=f"Comdirect depot CSV row {row_number} instrument type",
        )
        market_value = _parse_german_eur(record.get("Wert in EUR", ""), row_number)
        positions.append(
            Position(
                identifier=identifier,
                isin=isin,
                name=name,
                instrument_type=_INSTRUMENT_TYPE_MAP.get(source_type.casefold(), "Other"),
                market_value_eur=market_value,
            )
        )
        identifiers.add(identifier)
        if isin:
            isins.add(isin)
        if len(positions) > MAX_POSITIONS:
            raise ComdirectCsvImportError(
                f"Comdirect depot CSV may contain at most {MAX_POSITIONS} positions"
            )

    if not positions:
        raise ComdirectCsvImportError("No valid securities positions found in Comdirect depot CSV")
    imported_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return validate_snapshot(
        PortfolioSnapshot(generated_at=imported_at, positions=tuple(positions))
    )


def _parse_german_eur(value: object, row_number: int) -> Decimal:
    token = str(value or "").replace("\u00a0", " ").strip().replace(" ", "")
    if token.endswith("EUR"):
        token = token[:-3].strip()
    elif token.endswith("€"):
        token = token[:-1].strip()
    if _GERMAN_NUMBER_RE.fullmatch(token) is None:
        raise ComdirectCsvImportError(
            f"Comdirect depot CSV row {row_number} contains an invalid EUR market value"
        )
    try:
        amount = Decimal(token.replace(".", "").replace(",", "."))
    except InvalidOperation as err:
        raise ComdirectCsvImportError(
            f"Comdirect depot CSV row {row_number} contains an invalid EUR market value"
        ) from err
    if not amount.is_finite() or amount < 0 or amount > MAX_POSITION_VALUE_EUR:
        raise ComdirectCsvImportError(
            f"Comdirect depot CSV row {row_number} market value is outside the allowed range"
        )
    return amount


def _bounded_text(value: object, *, maximum: int, label: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ComdirectCsvImportError(f"{label} is required")
    if len(cleaned) > maximum or any(ord(char) < 32 for char in cleaned):
        raise ComdirectCsvImportError(f"{label} is invalid")
    return cleaned
