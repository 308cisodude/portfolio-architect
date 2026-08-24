"""Provider-specific CSV adapters producing canonical portfolio positions.

The import layer is deliberately independent from Home Assistant.  Every adapter
returns the same validated ``Position`` model; allocation, policy, and dashboard
logic therefore remain provider-neutral.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any, Final

from .models import Position

D = Decimal

PROVIDER_GENERIC_CSV: Final = "generic_csv"
SUPPORTED_PROVIDERS: Final = (PROVIDER_GENERIC_CSV,)

CSV_ENCODING_AUTO: Final = "auto"
CSV_ENCODINGS: Final = (
    CSV_ENCODING_AUTO,
    "utf-8-sig",
    "utf-8",
    "iso-8859-1",
)
CSV_DELIMITER_AUTO: Final = "auto"
CSV_DELIMITERS: Final = (
    CSV_DELIMITER_AUTO,
    "semicolon",
    "comma",
    "tab",
)
DECIMAL_FORMAT_AUTO: Final = "auto"
DECIMAL_FORMATS: Final = (
    DECIMAL_FORMAT_AUTO,
    "comma_decimal",
    "dot_decimal",
)

DEFAULT_GENERIC_ENCODING: Final = CSV_ENCODING_AUTO
DEFAULT_GENERIC_DELIMITER: Final = CSV_DELIMITER_AUTO
DEFAULT_GENERIC_HEADER_ROW: Final = 1
DEFAULT_GENERIC_DECIMAL_FORMAT: Final = DECIMAL_FORMAT_AUTO
MAX_GENERIC_HEADER_ROW: Final = 50

_MAX_CSV_ROWS = 4096
_MAX_CSV_FILE_SIZE = 10 * 1024 * 1024
_MAX_POSITIONS = 512
_MAX_NAME_LENGTH = 160
_MAX_SOURCE_TYPE_LENGTH = 64
_MAX_HEADER_LENGTH = 160
_MAX_POSITION_VALUE_EUR = D("1000000000")
_IDENTIFIER_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:/+-]{3,15}$")
_WKN_RE = re.compile(r"^[A-Z0-9]{5,16}$")
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

_INSTRUMENT_TYPE_MAP = {
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

_DELIMITER_CHARS = {
    "semicolon": ";",
    "comma": ",",
    "tab": "\t",
}


@dataclass(frozen=True, slots=True)
class CsvSourceConfig:
    """Validated provider and generic CSV mapping configuration."""

    provider: str = PROVIDER_GENERIC_CSV
    encoding: str = DEFAULT_GENERIC_ENCODING
    delimiter: str = DEFAULT_GENERIC_DELIMITER
    header_row: int = DEFAULT_GENERIC_HEADER_ROW
    decimal_format: str = DEFAULT_GENERIC_DECIMAL_FORMAT
    identifier_column: str | None = None
    name_column: str | None = None
    value_column: str | None = None
    isin_column: str | None = None
    type_column: str | None = None
    currency_column: str | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> CsvSourceConfig:
        """Build one strict source config from persisted integration data."""
        values = raw or {}
        provider = str(values.get("source_provider", PROVIDER_GENERIC_CSV))
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError("Unsupported portfolio source provider")
        encoding = str(values.get("csv_encoding", DEFAULT_GENERIC_ENCODING))
        delimiter = str(values.get("csv_delimiter", DEFAULT_GENERIC_DELIMITER))
        decimal_format = str(
            values.get("csv_decimal_format", DEFAULT_GENERIC_DECIMAL_FORMAT)
        )
        if encoding not in CSV_ENCODINGS:
            raise ValueError("Unsupported CSV encoding")
        if delimiter not in CSV_DELIMITERS:
            raise ValueError("Unsupported CSV delimiter")
        if decimal_format not in DECIMAL_FORMATS:
            raise ValueError("Unsupported CSV number format")
        header_row = _bounded_header_row(values.get("csv_header_row"))
        required = {
            "identifier_column": values.get("csv_column_identifier"),
            "name_column": values.get("csv_column_name"),
            "value_column": values.get("csv_column_value"),
        }
        cleaned_required = {
            key: _column_name(value, required=True) for key, value in required.items()
        }
        optional = {
            "isin_column": values.get("csv_column_isin"),
            "type_column": values.get("csv_column_type"),
            "currency_column": values.get("csv_column_currency"),
        }
        cleaned_optional = {
            key: _column_name(value, required=False) for key, value in optional.items()
        }
        return cls(
            provider=provider,
            encoding=encoding,
            delimiter=delimiter,
            header_row=header_row,
            decimal_format=decimal_format,
            **cleaned_required,
            **cleaned_optional,
        )

    def as_public_dict(self) -> dict[str, Any]:
        """Return privacy-safe adapter settings for diagnostics and calculation."""
        result: dict[str, Any] = {"source_provider": self.provider}
        if self.provider == PROVIDER_GENERIC_CSV:
            result.update(
                {
                    "csv_encoding": self.encoding,
                    "csv_delimiter": self.delimiter,
                    "csv_header_row": self.header_row,
                    "csv_decimal_format": self.decimal_format,
                    "csv_column_identifier": self.identifier_column,
                    "csv_column_name": self.name_column,
                    "csv_column_value": self.value_column,
                    "csv_column_isin": self.isin_column,
                    "csv_column_type": self.type_column,
                    "csv_column_currency": self.currency_column,
                }
            )
        return result


def read_positions(csv_path: Path, config: CsvSourceConfig) -> dict[str, Position]:
    """Dispatch one CSV file to its explicit provider adapter."""
    if config.provider == PROVIDER_GENERIC_CSV:
        return read_generic_positions(csv_path, config)
    raise ValueError("Unsupported portfolio source provider")


def inspect_csv_headers(csv_path: Path, config: CsvSourceConfig) -> tuple[str, ...]:
    """Return the bounded unique header row for a generic CSV mapping flow."""
    if config.provider != PROVIDER_GENERIC_CSV:
        raise ValueError("Header inspection is only available for generic CSV")
    rows = _read_rows(csv_path, config)
    if config.header_row > len(rows):
        raise ValueError("Configured CSV header row does not exist")
    headers = tuple(
        _clean_text(
            value,
            field="CSV header",
            maximum=_MAX_HEADER_LENGTH,
            required=True,
        )
        for value in rows[config.header_row - 1]
    )
    if len(headers) < 2:
        raise ValueError("Generic CSV must contain at least two columns")
    if len(set(headers)) != len(headers):
        raise ValueError("Generic CSV header names must be unique")
    return headers


def read_generic_positions(
    csv_path: Path,
    config: CsvSourceConfig,
) -> dict[str, Position]:
    """Read a user-mapped generic CSV containing EUR market values."""
    headers = inspect_csv_headers(csv_path, config)
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
        raise ValueError("Configured generic CSV columns are missing from the header")

    rows = _read_rows(csv_path, config)
    result: dict[str, Position] = {}
    for row_number, row in enumerate(rows[config.header_row :], start=config.header_row + 1):
        if not row or all(not str(value).strip() for value in row):
            continue
        if len(row) < len(headers):
            row = [*row, *([""] * (len(headers) - len(row)))]
        record = dict(zip(headers, row, strict=False))
        identifier = str(record.get(config.identifier_column or "", "")).strip().upper()
        name_raw = str(record.get(config.name_column or "", "")).strip()
        value_raw = str(record.get(config.value_column or "", "")).strip()
        if not identifier and not name_raw and not value_raw:
            continue
        _validate_identifier(identifier, row_number=row_number)

        isin = ""
        if config.isin_column:
            isin = str(record.get(config.isin_column, "")).strip().upper()
        elif _ISIN_RE.fullmatch(identifier):
            isin = identifier
        _validate_isin(isin, row_number=row_number)

        if config.currency_column:
            currency = str(record.get(config.currency_column, "")).strip().upper()
            if currency not in {"EUR", "€"}:
                raise ValueError(
                    f"CSV row {row_number} is not denominated in EUR; currency conversion is not supported"
                )

        source_type = (
            str(record.get(config.type_column, "")).strip()
            if config.type_column
            else "Other"
        )
        if not source_type:
            source_type = "Other"
        name = _clean_text(
            name_raw,
            field=f"CSV row {row_number} name",
            maximum=_MAX_NAME_LENGTH,
            required=True,
        )
        source_type = _clean_text(
            source_type,
            field=f"CSV row {row_number} instrument type",
            maximum=_MAX_SOURCE_TYPE_LENGTH,
            required=True,
        )
        value_eur = parse_number(value_raw, config.decimal_format)
        _add_position(
            result,
            identifier=identifier,
            isin=isin,
            name=name,
            source_type=source_type,
            value_eur=value_eur,
            row_number=row_number,
        )
    if not result:
        raise ValueError("No valid securities positions found in generic CSV")
    return result


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
        raise ValueError("Unsupported CSV number format")
    if decimal_format == "comma_decimal":
        normalised = cleaned.replace(".", "").replace(",", ".")
    elif decimal_format == "dot_decimal":
        normalised = cleaned.replace(",", "")
    else:
        normalised = _auto_normalise_number(cleaned)
    try:
        number = D(normalised)
    except InvalidOperation as err:
        raise ValueError(f"Invalid portfolio value: {value!r}") from err
    if not number.is_finite():
        raise ValueError("Position values must be finite")
    return number


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


def _read_rows(csv_path: Path, config: CsvSourceConfig) -> list[list[str]]:
    encoding = _detect_encoding(csv_path, config.encoding)
    delimiter = _detect_delimiter(csv_path, encoding, config.delimiter)
    return _read_csv_with_encoding(csv_path, encoding, delimiter)


def _read_csv_with_encoding(csv_path: Path, encoding: str, delimiter: str) -> list[list[str]]:
    if not csv_path.is_file():
        raise ValueError(f"Portfolio CSV does not exist: {csv_path.name}")
    if csv_path.stat().st_size > _MAX_CSV_FILE_SIZE:
        raise ValueError("Portfolio CSV exceeds the 10 MiB size limit")
    with csv_path.open("r", encoding=encoding, newline="") as handle:
        rows = list(csv.reader(handle, delimiter=delimiter, quotechar='"'))
    if len(rows) > _MAX_CSV_ROWS:
        raise ValueError(f"CSV may contain at most {_MAX_CSV_ROWS} rows")
    return rows


def _detect_encoding(csv_path: Path, configured: str) -> str:
    if configured != CSV_ENCODING_AUTO:
        return configured
    sample = csv_path.read_bytes()[:64 * 1024]
    for encoding in ("utf-8-sig", "utf-8", "iso-8859-1"):
        try:
            sample.decode(encoding)
        except UnicodeDecodeError:
            continue
        return encoding
    raise ValueError("Could not detect a supported CSV encoding")


def _detect_delimiter(csv_path: Path, encoding: str, configured: str) -> str:
    if configured != CSV_DELIMITER_AUTO:
        return _DELIMITER_CHARS[configured]
    sample = csv_path.read_bytes()[:64 * 1024].decode(encoding)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        counts = {delimiter: first_line.count(delimiter) for delimiter in ";,\t"}
        delimiter = max(counts, key=counts.get)
        if counts[delimiter] == 0:
            raise ValueError("Could not detect the CSV delimiter")
        return delimiter
    return dialect.delimiter


def _add_position(
    result: dict[str, Position],
    *,
    identifier: str,
    isin: str,
    name: str,
    source_type: str,
    value_eur: Decimal,
    row_number: int,
) -> None:
    if identifier in result:
        raise ValueError(f"CSV contains duplicate instrument identifier {identifier}")
    if len(result) >= _MAX_POSITIONS:
        raise ValueError(f"CSV may contain at most {_MAX_POSITIONS} positions")
    if value_eur < 0 or value_eur > _MAX_POSITION_VALUE_EUR:
        raise ValueError(f"CSV row {row_number} position value is outside the allowed range")
    result[identifier] = Position(
        wkn=identifier,
        isin=isin,
        name=name,
        instrument_type=_instrument_type(source_type),
        source_type=source_type,
        value_eur=value_eur,
    )


def _validate_identifier(value: str, *, row_number: int) -> None:
    if not value or _IDENTIFIER_RE.fullmatch(value) is None:
        raise ValueError(f"CSV row {row_number} contains an invalid instrument identifier")


def _validate_isin(value: str, *, row_number: int) -> None:
    if value and _ISIN_RE.fullmatch(value) is None:
        raise ValueError(f"CSV row {row_number} contains an invalid ISIN")


def _instrument_type(source_type: str) -> str:
    return _INSTRUMENT_TYPE_MAP.get(source_type.strip().casefold(), "other")


def _clean_text(value: str, *, field: str, maximum: int, required: bool) -> str:
    cleaned = str(value or "").strip()
    if required and not cleaned:
        raise ValueError(f"{field} is required")
    if len(cleaned) > maximum or any(ord(char) < 32 for char in cleaned):
        raise ValueError(f"{field} is too long or contains control characters")
    return cleaned


def _column_name(value: object, *, required: bool) -> str | None:
    if value is None or value == "":
        if required:
            raise ValueError("Required generic CSV mapping is missing")
        return None
    return _clean_text(
        str(value), field="CSV column name", maximum=_MAX_HEADER_LENGTH, required=True
    )


def _bounded_header_row(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("CSV header row must be an integer")
    try:
        parsed = int(value if value is not None else DEFAULT_GENERIC_HEADER_ROW)
    except (TypeError, ValueError) as err:
        raise ValueError("CSV header row must be an integer") from err
    if not 1 <= parsed <= MAX_GENERIC_HEADER_ROW:
        raise ValueError("CSV header row is outside the allowed range")
    return parsed
