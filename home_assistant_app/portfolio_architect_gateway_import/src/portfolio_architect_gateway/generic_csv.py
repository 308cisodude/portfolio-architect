"""Strict provider-neutral mapped CSV acquisition for the Generic Import Gateway.

Raw CSV bytes are transient.  Only a validated canonical :class:`PortfolioSnapshot`
and one bounded mapping configuration are persisted by the App shell.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import io
import re
from pathlib import Path
from typing import Any, Final

from .acquisition_control import AcquisitionControl, single_method_control
from .errors import ConfigurationError, ProtocolError
from .models import PortfolioSnapshot, Position, validate_snapshot
from .store import load_snapshot

D = Decimal
PROVIDER_ID: Final = "generic_csv"
CSV_ENCODING_AUTO: Final = "auto"
CSV_ENCODINGS: Final = (CSV_ENCODING_AUTO, "utf-8-sig", "utf-8", "iso-8859-1")
CSV_DELIMITER_AUTO: Final = "auto"
CSV_DELIMITERS: Final = (CSV_DELIMITER_AUTO, "semicolon", "comma", "tab")
DECIMAL_FORMAT_AUTO: Final = "auto"
DECIMAL_FORMATS: Final = (DECIMAL_FORMAT_AUTO, "comma_decimal", "dot_decimal")
DEFAULT_HEADER_ROW: Final = 1
MAX_HEADER_ROW: Final = 50
MAX_CSV_ROWS: Final = 4096
MAX_CSV_FILE_BYTES: Final = 10 * 1024 * 1024
MAX_NAME_LENGTH: Final = 160
MAX_SOURCE_TYPE_LENGTH: Final = 64
MAX_HEADER_LENGTH: Final = 160
MAX_POSITION_VALUE_EUR: Final = D("1000000000")

_IDENTIFIER_RE: Final = re.compile(r"^[A-Z0-9][A-Z0-9._:/+-]{3,15}$")
_ISIN_RE: Final = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_DELIMITER_CHARS: Final = {"semicolon": ";", "comma": ",", "tab": "\t"}
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


class GenericCsvImportError(ValueError):
    """Privacy-safe rejection reason for one mapped generic CSV import."""


@dataclass(frozen=True, slots=True)
class GenericCsvConfig:
    """Strict bounded CSV format and column mapping."""

    encoding: str = CSV_ENCODING_AUTO
    delimiter: str = CSV_DELIMITER_AUTO
    header_row: int = DEFAULT_HEADER_ROW
    decimal_format: str = DECIMAL_FORMAT_AUTO
    identifier_column: str = "Identifier"
    name_column: str = "Security"
    value_column: str = "Market Value"
    isin_column: str | None = "ISIN"
    type_column: str | None = "Asset Type"
    currency_column: str | None = "Currency"

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> "GenericCsvConfig":
        values = raw or {}
        allowed = {
            "encoding",
            "delimiter",
            "header_row",
            "decimal_format",
            "identifier_column",
            "name_column",
            "value_column",
            "isin_column",
            "type_column",
            "currency_column",
        }
        if set(values) - allowed:
            raise GenericCsvImportError("CSV mapping contains unsupported fields")
        encoding = str(values.get("encoding", CSV_ENCODING_AUTO))
        delimiter = str(values.get("delimiter", CSV_DELIMITER_AUTO))
        decimal_format = str(values.get("decimal_format", DECIMAL_FORMAT_AUTO))
        if encoding not in CSV_ENCODINGS:
            raise GenericCsvImportError("Unsupported CSV encoding")
        if delimiter not in CSV_DELIMITERS:
            raise GenericCsvImportError("Unsupported CSV delimiter")
        if decimal_format not in DECIMAL_FORMATS:
            raise GenericCsvImportError("Unsupported CSV number format")
        header_row = _bounded_header_row(values.get("header_row"))
        return cls(
            encoding=encoding,
            delimiter=delimiter,
            header_row=header_row,
            decimal_format=decimal_format,
            identifier_column=_column_name(
                values.get("identifier_column", "Identifier"), required=True
            ) or "Identifier",
            name_column=_column_name(
                values.get("name_column", "Security"), required=True
            ) or "Security",
            value_column=_column_name(
                values.get("value_column", "Market Value"), required=True
            ) or "Market Value",
            isin_column=_column_name(values.get("isin_column", "ISIN"), required=False),
            type_column=_column_name(
                values.get("type_column", "Asset Type"), required=False
            ),
            currency_column=_column_name(
                values.get("currency_column", "Currency"), required=False
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "encoding": self.encoding,
            "delimiter": self.delimiter,
            "header_row": self.header_row,
            "decimal_format": self.decimal_format,
            "identifier_column": self.identifier_column,
            "name_column": self.name_column,
            "value_column": self.value_column,
            "isin_column": self.isin_column,
            "type_column": self.type_column,
            "currency_column": self.currency_column,
        }


@dataclass(frozen=True, slots=True)
class GenericCsvImportSummary:
    """Privacy-safe facts about one successful import."""

    position_count: int
    generated_at: datetime


class GenericCsvProvider:
    """Static provider publishing only the latest canonical generic snapshot."""

    def __init__(
        self,
        snapshot_file: Path,
        *,
        provider_id: str = PROVIDER_ID,
        provider_name: str = "Generic Import",
    ) -> None:
        self._snapshot_file = Path(snapshot_file)
        self._provider_id = provider_id
        self._provider_name = provider_name
        try:
            self._snapshot = load_snapshot(self._snapshot_file)
        except ProtocolError as err:
            raise ConfigurationError("Stored Generic Import snapshot is invalid") from err

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def acquisition_mode(self) -> str:
        return "csv"

    @property
    def acquisition_control(self) -> AcquisitionControl:
        return single_method_control("csv", cash=True)

    @property
    def poll_interval_seconds(self) -> int:
        # Imports are explicit user actions; no filesystem or upstream polling occurs.
        return 86400

    def fetch_snapshot(self) -> PortfolioSnapshot:
        if self._snapshot is None:
            raise ConfigurationError("No mapped generic CSV has been imported")
        return self._snapshot

    @property
    def snapshot(self) -> PortfolioSnapshot | None:
        return self._snapshot

    @property
    def snapshot_file(self) -> Path:
        return self._snapshot_file

    def replace_snapshot(self, snapshot: PortfolioSnapshot | None) -> None:
        self._snapshot = snapshot


def inspect_csv_headers(data: bytes, config: GenericCsvConfig) -> tuple[str, ...]:
    """Return one bounded unique header row without persisting the raw CSV."""
    rows = _read_rows(data, config)
    if config.header_row > len(rows):
        raise GenericCsvImportError("Configured CSV header row does not exist")
    headers = tuple(
        _clean_text(
            value,
            field="CSV header",
            maximum=MAX_HEADER_LENGTH,
            required=True,
        )
        for value in rows[config.header_row - 1]
    )
    if len(headers) < 2:
        raise GenericCsvImportError("Generic CSV must contain at least two columns")
    if len(set(headers)) != len(headers):
        raise GenericCsvImportError("Generic CSV header names must be unique")
    return headers


def parse_generic_csv(
    data: bytes,
    config: GenericCsvConfig,
    *,
    generated_at: datetime | None = None,
) -> tuple[PortfolioSnapshot, GenericCsvImportSummary]:
    """Parse one explicitly mapped generic CSV into a canonical schema-1 snapshot."""
    headers = inspect_csv_headers(data, config)
    configured_columns = {
        config.identifier_column,
        config.name_column,
        config.value_column,
        config.isin_column,
        config.type_column,
        config.currency_column,
    }
    missing = {value for value in configured_columns if value and value not in headers}
    if missing:
        raise GenericCsvImportError(
            "Configured generic CSV columns are missing from the header"
        )

    rows = _read_rows(data, config)
    positions: list[Position] = []
    identifiers: set[str] = set()
    isins: set[str] = set()
    for row_number, row in enumerate(
        rows[config.header_row :], start=config.header_row + 1
    ):
        if not row or all(not str(value).strip() for value in row):
            continue
        if len(row) < len(headers):
            row = [*row, *([""] * (len(headers) - len(row)))]
        record = dict(zip(headers, row, strict=False))
        identifier = str(record.get(config.identifier_column, "")).strip().upper()
        name_raw = str(record.get(config.name_column, "")).strip()
        value_raw = str(record.get(config.value_column, "")).strip()
        if not identifier and not name_raw and not value_raw:
            continue
        if _IDENTIFIER_RE.fullmatch(identifier) is None:
            raise GenericCsvImportError(
                f"CSV row {row_number} contains an invalid instrument identifier"
            )
        if identifier in identifiers:
            raise GenericCsvImportError("CSV contains a duplicate instrument identifier")
        identifiers.add(identifier)

        isin = ""
        if config.isin_column:
            isin = str(record.get(config.isin_column, "")).strip().upper()
        elif _ISIN_RE.fullmatch(identifier):
            isin = identifier
        if isin and _ISIN_RE.fullmatch(isin) is None:
            raise GenericCsvImportError(f"CSV row {row_number} contains an invalid ISIN")
        if isin and isin in isins:
            raise GenericCsvImportError("CSV contains a duplicate ISIN")
        if isin:
            isins.add(isin)

        if config.currency_column:
            currency = str(record.get(config.currency_column, "")).strip().upper()
            if currency not in {"EUR", "€"}:
                raise GenericCsvImportError(
                    f"CSV row {row_number} is not denominated in EUR; currency conversion is not supported"
                )

        source_type = (
            str(record.get(config.type_column, "")).strip()
            if config.type_column
            else "Other"
        ) or "Other"
        name = _clean_text(
            name_raw,
            field=f"CSV row {row_number} name",
            maximum=MAX_NAME_LENGTH,
            required=True,
        )
        source_type = _clean_text(
            source_type,
            field=f"CSV row {row_number} instrument type",
            maximum=MAX_SOURCE_TYPE_LENGTH,
            required=True,
        )
        value_eur = parse_number(value_raw, config.decimal_format)
        if value_eur < 0 or value_eur > MAX_POSITION_VALUE_EUR:
            raise GenericCsvImportError(
                f"CSV row {row_number} position value is outside the allowed range"
            )
        if len(positions) >= 512:
            raise GenericCsvImportError("CSV may contain at most 512 positions")
        positions.append(
            Position(
                identifier=identifier,
                name=name,
                market_value_eur=value_eur,
                isin=isin,
                instrument_type=_instrument_type(source_type),
            )
        )

    if not positions:
        raise GenericCsvImportError("No valid securities positions found in generic CSV")
    evidence_time = generated_at or datetime.now(timezone.utc)
    if evidence_time.tzinfo is None or evidence_time.utcoffset() is None:
        raise GenericCsvImportError("Import evidence timestamp must include a timezone")
    snapshot = validate_snapshot(
        PortfolioSnapshot(
            generated_at=evidence_time.astimezone(timezone.utc),
            positions=tuple(positions),
        )
    )
    return snapshot, GenericCsvImportSummary(
        position_count=len(snapshot.positions), generated_at=snapshot.generated_at
    )


def parse_number(value: str, decimal_format: str) -> Decimal:
    """Parse one bounded locale-aware number without evaluating expressions."""
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
    if decimal_format not in DECIMAL_FORMATS:
        raise GenericCsvImportError("Unsupported CSV number format")
    if decimal_format == "comma_decimal":
        normalised = cleaned.replace(".", "").replace(",", ".")
    elif decimal_format == "dot_decimal":
        normalised = cleaned.replace(",", "")
    else:
        normalised = _auto_normalise_number(cleaned)
    try:
        number = D(normalised)
    except InvalidOperation as err:
        raise GenericCsvImportError("Portfolio value is not a supported decimal") from err
    if not number.is_finite():
        raise GenericCsvImportError("Position values must be finite")
    return number


def _read_rows(data: bytes, config: GenericCsvConfig) -> list[list[str]]:
    if not isinstance(data, bytes) or not data or len(data) > MAX_CSV_FILE_BYTES:
        raise GenericCsvImportError("CSV is empty or exceeds the 10 MiB import limit")
    encoding = _detect_encoding(data, config.encoding)
    delimiter = _detect_delimiter(data, encoding, config.delimiter)
    try:
        text = data.decode(encoding)
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, quotechar='"'))
    except (UnicodeDecodeError, csv.Error) as err:
        raise GenericCsvImportError("CSV could not be parsed safely") from err
    if len(rows) > MAX_CSV_ROWS:
        raise GenericCsvImportError(f"CSV may contain at most {MAX_CSV_ROWS} rows")
    return rows


def _detect_encoding(data: bytes, configured: str) -> str:
    if configured != CSV_ENCODING_AUTO:
        try:
            data[: 64 * 1024].decode(configured)
        except UnicodeDecodeError as err:
            raise GenericCsvImportError("CSV does not match the configured encoding") from err
        return configured
    sample = data[: 64 * 1024]
    for encoding in ("utf-8-sig", "utf-8", "iso-8859-1"):
        try:
            sample.decode(encoding)
        except UnicodeDecodeError:
            continue
        return encoding
    raise GenericCsvImportError("Could not detect a supported CSV encoding")


def _detect_delimiter(data: bytes, encoding: str, configured: str) -> str:
    if configured != CSV_DELIMITER_AUTO:
        return _DELIMITER_CHARS[configured]
    try:
        sample = data[: 64 * 1024].decode(encoding)
    except UnicodeDecodeError as err:
        raise GenericCsvImportError("CSV could not be decoded for delimiter detection") from err
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        counts = {delimiter: first_line.count(delimiter) for delimiter in ";,\t"}
        delimiter = max(counts, key=counts.get)
        if counts[delimiter] == 0:
            raise GenericCsvImportError("Could not detect the CSV delimiter")
        return delimiter
    return dialect.delimiter


def _auto_normalise_number(value: str) -> str:
    comma = value.rfind(",")
    dot = value.rfind(".")
    if comma >= 0 and dot >= 0:
        if comma > dot:
            return value.replace(".", "").replace(",", ".")
        return value.replace(",", "")
    if comma >= 0:
        decimals = len(value) - comma - 1
        return value.replace(",", ".") if 1 <= decimals <= 4 else value.replace(",", "")
    if dot >= 0:
        decimals = len(value) - dot - 1
        return value if 1 <= decimals <= 4 else value.replace(".", "")
    return value


def _instrument_type(source_type: str) -> str:
    return _INSTRUMENT_TYPE_MAP.get(source_type.strip().casefold(), "other")


def _clean_text(value: str, *, field: str, maximum: int, required: bool) -> str:
    cleaned = str(value or "").strip()
    if required and not cleaned:
        raise GenericCsvImportError(f"{field} is required")
    if len(cleaned) > maximum or any(ord(char) < 32 for char in cleaned):
        raise GenericCsvImportError(f"{field} is too long or contains control characters")
    return cleaned


def _column_name(value: object, *, required: bool) -> str | None:
    if value is None or value == "":
        if required:
            raise GenericCsvImportError("Required generic CSV mapping is missing")
        return None
    return _clean_text(
        str(value), field="CSV column name", maximum=MAX_HEADER_LENGTH, required=True
    )


def _bounded_header_row(value: object) -> int:
    if isinstance(value, bool):
        raise GenericCsvImportError("CSV header row must be an integer")
    try:
        parsed = int(value if value is not None else DEFAULT_HEADER_ROW)
    except (TypeError, ValueError) as err:
        raise GenericCsvImportError("CSV header row must be an integer") from err
    if not 1 <= parsed <= MAX_HEADER_ROW:
        raise GenericCsvImportError("CSV header row is outside the allowed range")
    return parsed
