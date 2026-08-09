"""Provider-specific CSV adapters producing canonical portfolio positions.

The import layer is deliberately independent from Home Assistant.  Every adapter
returns the same validated ``Position`` model; allocation, policy, and dashboard
logic therefore remain provider-neutral.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime, time, timezone
from pathlib import Path
import re
from typing import Any, Final

from .models import Position

D = Decimal

PROVIDER_COMDIRECT: Final = "comdirect_csv"
PROVIDER_DKB: Final = "dkb_csv"
PROVIDER_GENERIC_CSV: Final = "generic_csv"
SUPPORTED_PROVIDERS: Final = (PROVIDER_COMDIRECT, PROVIDER_DKB, PROVIDER_GENERIC_CSV)

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

    provider: str = PROVIDER_COMDIRECT
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
        provider = str(values.get("source_provider", PROVIDER_COMDIRECT))
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError("Unsupported portfolio source provider")
        if provider in {PROVIDER_COMDIRECT, PROVIDER_DKB}:
            return cls(provider=provider)

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
    if config.provider == PROVIDER_COMDIRECT:
        return read_comdirect_positions(csv_path)
    if config.provider == PROVIDER_DKB:
        return read_dkb_positions(csv_path)
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


def read_comdirect_positions(csv_path: Path) -> dict[str, Position]:
    """Read every valid security position from a Comdirect depot export."""
    rows = _read_csv_with_encoding(csv_path, "iso-8859-1", ";")
    header_idx = next(
        (i for i, row in enumerate(rows) if "WKN" in row and "Wert in EUR" in row),
        None,
    )
    if header_idx is None:
        raise ValueError("Could not locate Comdirect securities table header")
    header = rows[header_idx]
    if len(set(header)) != len(header):
        raise ValueError("Comdirect CSV contains duplicate header names")

    result: dict[str, Position] = {}
    for row_number, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        if not row or len(row) < len(header):
            continue
        record = dict(zip(header, row, strict=False))
        identifier = (record.get("WKN") or "").strip().upper()
        if not identifier:
            continue
        _validate_identifier(identifier, row_number=row_number)
        if identifier in result:
            raise ValueError(f"CSV contains duplicate WKN {identifier}")
        isin = (record.get("ISIN") or "").strip().upper()
        _validate_isin(isin, row_number=row_number)
        name = _clean_text(
            record.get("Bezeichnung", ""),
            field=f"CSV row {row_number} name",
            maximum=_MAX_NAME_LENGTH,
            required=True,
        )
        source_type = _clean_text(
            record.get("Typ", ""),
            field=f"CSV row {row_number} instrument type",
            maximum=_MAX_SOURCE_TYPE_LENGTH,
            required=True,
        )
        value_eur = parse_number(record.get("Wert in EUR", "0"), "comma_decimal")
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
        raise ValueError("No valid securities positions found in Comdirect export")
    return result


def read_dkb_positions(csv_path: Path) -> dict[str, Position]:
    """Read a DKB depot export and derive exact EUR market values.

    DKB exports valuation price and quantity instead of a market-value column.
    Depot identifiers and performance columns are deliberately ignored.
    """
    rows = _read_csv_with_encoding(csv_path, "utf-8-sig", ";")
    if not rows:
        raise ValueError("DKB CSV is empty")
    header = rows[0]
    required = {
        "Datum der Erstellung",
        "Wertpapierbezeichnung",
        "WKN",
        "ISIN",
        "Bewertungskurs",
        "Stückzahl",
        "Assetklasse",
    }
    if not required.issubset(set(header)):
        raise ValueError("DKB CSV does not contain the required depot-export columns")
    if len(set(header)) != len(header):
        raise ValueError("DKB CSV contains duplicate header names")

    result: dict[str, Position] = {}
    for row_number, row in enumerate(rows[1:], start=2):
        if not row or all(not str(value).strip() for value in row):
            continue
        if len(row) < len(header):
            row = [*row, *( [""] * (len(header) - len(row)) )]
        record = dict(zip(header, row, strict=False))
        identifier = str(record.get("WKN", "")).strip().upper()
        if not identifier:
            continue
        _validate_identifier(identifier, row_number=row_number)
        isin = str(record.get("ISIN", "")).strip().upper()
        _validate_isin(isin, row_number=row_number)
        name = _clean_text(
            record.get("Wertpapierbezeichnung", ""),
            field=f"CSV row {row_number} name",
            maximum=_MAX_NAME_LENGTH,
            required=True,
        )
        source_type = _clean_text(
            record.get("Assetklasse", "Other") or "Other",
            field=f"CSV row {row_number} instrument type",
            maximum=_MAX_SOURCE_TYPE_LENGTH,
            required=True,
        )
        price = parse_number(record.get("Bewertungskurs", "0"), "comma_decimal")
        quantity = parse_number(record.get("Stückzahl", "0"), "comma_decimal")
        if price < 0 or quantity < 0:
            raise ValueError(f"CSV row {row_number} contains a negative price or quantity")
        value_eur = price * quantity
        candidate = Position(
            wkn=identifier,
            isin=isin,
            name=name,
            instrument_type=_instrument_type(source_type),
            source_type=source_type,
            value_eur=value_eur,
            quantity=quantity,
        )
        existing = result.get(identifier)
        if existing is None:
            if len(result) >= _MAX_POSITIONS:
                raise ValueError(f"CSV may contain at most {_MAX_POSITIONS} positions")
            if value_eur > _MAX_POSITION_VALUE_EUR:
                raise ValueError(f"CSV row {row_number} position value is outside the allowed range")
            result[identifier] = candidate
            continue
        if (
            existing.isin != candidate.isin
            or existing.instrument_type != candidate.instrument_type
        ):
            raise ValueError(
                f"DKB CSV contains conflicting rows for instrument identifier {identifier}"
            )
        merged_value = existing.value_eur + candidate.value_eur
        if merged_value > _MAX_POSITION_VALUE_EUR:
            raise ValueError(f"CSV row {row_number} position value is outside the allowed range")
        result[identifier] = Position(
            wkn=existing.wkn,
            isin=existing.isin,
            name=existing.name,
            instrument_type=existing.instrument_type,
            source_type=existing.source_type,
            value_eur=merged_value,
            quantity=(existing.quantity or Decimal("0")) + (candidate.quantity or Decimal("0")),
        )
    if not result:
        raise ValueError("No valid securities positions found in DKB export")
    return result


@dataclass(frozen=True, slots=True)
class _DkbExportMetadata:
    """Private identity and timestamp used only for safe export selection."""

    generated_at: datetime
    portfolio_key: str


def _dkb_export_metadata(csv_path: Path) -> _DkbExportMetadata:
    """Read the export date and depot identity without exposing either identifier."""
    rows = _read_csv_with_encoding(csv_path, "utf-8-sig", ";")
    if len(rows) < 2:
        raise ValueError("DKB CSV is empty")
    header = rows[0]
    required = {"Datum der Erstellung", "Depotnummer"}
    if not required.issubset(set(header)):
        raise ValueError("DKB CSV does not contain export identity metadata")
    date_index = header.index("Datum der Erstellung")
    depot_index = header.index("Depotnummer")
    dates: set[str] = set()
    depots: set[str] = set()
    for row in rows[1:]:
        if not row or all(not str(value).strip() for value in row):
            continue
        if date_index < len(row) and row[date_index].strip():
            dates.add(row[date_index].strip())
        if depot_index < len(row) and row[depot_index].strip():
            depots.add(row[depot_index].strip())
    if len(dates) != 1 or len(depots) != 1:
        raise ValueError("DKB CSV must describe exactly one depot and one export date")
    token = next(iter(dates))
    try:
        parsed = datetime.strptime(token, "%d.%m.%Y").date()
    except ValueError as err:
        raise ValueError("DKB CSV contains an invalid export date") from err
    return _DkbExportMetadata(
        generated_at=datetime.combine(parsed, time.min, tzinfo=timezone.utc),
        portfolio_key=next(iter(depots)),
    )


def dkb_export_timestamp(csv_path: Path) -> datetime:
    """Return the source-owned DKB export date as a UTC timestamp."""
    return _dkb_export_metadata(csv_path).generated_at


def select_latest_dkb_exports(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    """Keep only the newest export for each DKB depot, preserving depot order.

    The depot number is used only as an in-memory comparison key. It is never
    returned, persisted, logged, or included in Portfolio Architect payloads.
    """
    selected: dict[str, tuple[Path, _DkbExportMetadata, str]] = {}
    for path in paths:
        metadata = _dkb_export_metadata(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        existing = selected.get(metadata.portfolio_key)
        if existing is None:
            selected[metadata.portfolio_key] = (path, metadata, digest)
            continue
        existing_path, existing_metadata, existing_digest = existing
        if metadata.generated_at > existing_metadata.generated_at:
            selected[metadata.portfolio_key] = (path, metadata, digest)
            continue
        if metadata.generated_at < existing_metadata.generated_at:
            continue
        if digest != existing_digest:
            raise ValueError(
                "Multiple DKB exports for the same depot and date contain different data"
            )
        # Identical duplicate: retain the first configured path deterministically.
        selected[metadata.portfolio_key] = (
            existing_path, existing_metadata, existing_digest
        )
    return tuple(item[0] for item in selected.values())


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
