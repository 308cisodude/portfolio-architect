"""Strict local Trade Republic depot-statement importer.

The importer accepts only the explicitly supported German text-PDF ``DEPOTAUSZUG``
layout.  Uploaded documents are parsed in memory and converted into the existing
provider-neutral REST snapshot model; the original PDF is never persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
import re
from typing import Final

from pypdf import PdfReader

from .errors import ConfigurationError, ProtocolError
from .models import PortfolioSnapshot, Position, validate_snapshot
from .store import load_snapshot

MAX_PDF_BYTES: Final = 5 * 1024 * 1024
MAX_PDF_PAGES: Final = 32
MAX_PAGE_CONTENT_BYTES: Final = 2 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS: Final = 512 * 1024
MAX_IMPORT_POSITIONS: Final = 512
MAX_POSITION_QUANTITY: Final = Decimal("1000000000000")
MAX_CLOCK_SKEW: Final = timedelta(minutes=5)
PROVIDER_ID: Final = "trade_republic"

_STATEMENT_MARKER_RE = re.compile(r"\bDEPOTAUSZUG\b")
_STATEMENT_DATE_RE = re.compile(r"DEPOTAUSZUG\s+zum\s+(\d{2}\.\d{2}\.\d{4})", re.IGNORECASE)
_CREATED_RE = re.compile(
    r"Erstellt\s+am\s+(\d{4}-\d{2}-\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2})\s+Europe/Berlin\s+\(UTC([+-]\d{2}:\d{2})\)",
    re.IGNORECASE,
)
_SUMMARY_RE = re.compile(
    r"ANZAHL\s+POSITIONEN:\s*(\d{1,3})\s+([0-9][0-9.]*,[0-9]{2})\s+EUR",
    re.IGNORECASE,
)
_ISIN_RE = re.compile(r"\bISIN:\s*([A-Z]{2}[A-Z0-9]{9}[0-9])\b")
_GERMAN_NUMBER_RE = re.compile(r"^(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)(?:,[0-9]+)?$")
_POSITION_LINE_RE = re.compile(
    r"^\s*(?P<quantity>(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)(?:,[0-9]+)?)"
    r"\s+Stk\.\s+(?P<name>\S.*?)\s{2,}"
    r"(?P<price>(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2})\s{2,}"
    r"(?P<value>(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2})\s*$",
    re.IGNORECASE,
)


class StatementImportError(ValueError):
    """A bounded, privacy-safe reason for rejecting one uploaded statement."""


@dataclass(frozen=True, slots=True)
class StatementImportSummary:
    """Non-attributable import metadata safe for the admin-only status page."""

    position_count: int
    generated_at: datetime


class TradeRepublicStatementProvider:
    """Static provider backed by the last accepted private statement snapshot."""

    def __init__(self, snapshot_file) -> None:
        self._snapshot_file = snapshot_file
        try:
            self._snapshot = load_snapshot(snapshot_file)
        except ProtocolError as err:
            raise ConfigurationError("Stored Trade Republic snapshot is invalid") from err

    @property
    def provider_id(self) -> str:
        return PROVIDER_ID

    @property
    def poll_interval_seconds(self) -> int:
        # Imports are explicit user actions; no remote polling is performed.
        return 86400

    def fetch_snapshot(self) -> PortfolioSnapshot:
        if self._snapshot is None:
            raise ConfigurationError("No supported Trade Republic statement has been imported")
        return self._snapshot

    def replace_snapshot(self, snapshot: PortfolioSnapshot | None) -> None:
        self._snapshot = snapshot

    @property
    def snapshot(self) -> PortfolioSnapshot | None:
        return self._snapshot

    @property
    def snapshot_file(self) -> Path:
        """Return the App-private normalized-snapshot path for sibling state files."""
        return Path(self._snapshot_file)


def parse_statement_pdf(data: bytes, *, now: datetime | None = None) -> PortfolioSnapshot:
    """Parse one bounded text-based Trade Republic depot statement PDF."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_PDF_BYTES:
        raise StatementImportError("PDF is empty or exceeds the 5 MiB import limit")
    if not data.startswith(b"%PDF-"):
        raise StatementImportError("Uploaded file is not a PDF document")

    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise StatementImportError("Encrypted PDF statements are not supported")
        page_count = len(reader.pages)
        if not 1 <= page_count <= MAX_PDF_PAGES:
            raise StatementImportError("PDF page count is outside the supported range")

        page_texts: list[str] = []
        total_chars = 0
        for page in reader.pages:
            contents = page.get_contents()
            if contents is not None:
                decoded = contents.get_data()
                if len(decoded) > MAX_PAGE_CONTENT_BYTES:
                    raise StatementImportError("PDF page content exceeds the import safety limit")
            text = page.extract_text(
                extraction_mode="layout",
                layout_mode_space_vertically=False,
            )
            if not isinstance(text, str) or not text.strip():
                raise StatementImportError("PDF does not contain an extractable text layer")
            total_chars += len(text)
            if total_chars > MAX_EXTRACTED_TEXT_CHARS:
                raise StatementImportError("Extracted PDF text exceeds the import safety limit")
            page_texts.append(text)
    except StatementImportError:
        raise
    except Exception as err:
        raise StatementImportError("PDF could not be parsed safely") from err

    return parse_statement_text("\n".join(page_texts), now=now)


def parse_statement_text(text: str, *, now: datetime | None = None) -> PortfolioSnapshot:
    """Parse the supported German ``DEPOTAUSZUG`` text layout fail-closed."""
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_EXTRACTED_TEXT_CHARS:
        raise StatementImportError("Statement text is empty or too large")
    normalized = text.replace("\u00a0", " ").replace("\r", "")
    if _STATEMENT_MARKER_RE.search(normalized) is None:
        raise StatementImportError("Unsupported Trade Republic document type")
    if "TRADE REPUBLIC BANK GMBH" not in normalized.upper():
        raise StatementImportError("Document issuer is not the supported Trade Republic statement format")

    statement_date = _unique_statement_date(normalized)
    generated_at = _unique_creation_timestamp(normalized)
    if generated_at.date() != statement_date.date():
        raise StatementImportError("Statement date and document creation date do not match")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if generated_at.astimezone(timezone.utc) > current + MAX_CLOCK_SKEW:
        raise StatementImportError("Statement creation timestamp is in the future")

    lines = normalized.splitlines()
    starts: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = _POSITION_LINE_RE.match(line)
        if match is not None:
            starts.append((index, match))
    if not starts or len(starts) > MAX_IMPORT_POSITIONS:
        raise StatementImportError("Statement contains no supported positions or too many positions")

    positions: list[Position] = []
    seen_isins: set[str] = set()
    for offset, (line_index, match) in enumerate(starts):
        next_index = starts[offset + 1][0] if offset + 1 < len(starts) else len(lines)
        block_lines = lines[line_index:next_index]
        block = "\n".join(block_lines)
        isin_matches = _ISIN_RE.findall(block)
        if len(isin_matches) != 1:
            raise StatementImportError("Each supported position must contain exactly one ISIN")
        isin = isin_matches[0]
        if isin in seen_isins:
            raise StatementImportError("Statement contains a duplicate ISIN")
        seen_isins.add(isin)

        quantity = _parse_german_decimal(match.group("quantity"), field="quantity")
        if quantity <= 0 or quantity > MAX_POSITION_QUANTITY or -quantity.as_tuple().exponent > 8:
            raise StatementImportError("Position quantity is outside the supported range")
        market_value = _parse_german_decimal(match.group("value"), field="market value")
        name = _clean_name(match.group("name"))
        instrument_type = _instrument_type(" ".join(block_lines))
        positions.append(
            Position(
                identifier=isin,
                name=name,
                market_value_eur=market_value,
                quantity=quantity,
                isin=isin,
                instrument_type=instrument_type,
            )
        )

    expected_count, expected_total = _unique_summary(normalized)
    actual_total = sum((position.market_value_eur for position in positions), Decimal("0"))
    if expected_count != len(positions):
        raise StatementImportError("Statement position count does not match the parsed holdings")
    if expected_total != actual_total:
        raise StatementImportError("Statement portfolio total does not match the parsed holdings")

    try:
        return validate_snapshot(
            PortfolioSnapshot(
                generated_at=generated_at,
                positions=tuple(positions),
            )
        )
    except ProtocolError as err:
        raise StatementImportError("Parsed statement violates the portfolio snapshot contract") from err


def import_summary(snapshot: PortfolioSnapshot) -> StatementImportSummary:
    return StatementImportSummary(
        position_count=len(snapshot.positions),
        generated_at=snapshot.generated_at.astimezone(timezone.utc),
    )


def _unique_statement_date(text: str) -> datetime:
    tokens = tuple(dict.fromkeys(_STATEMENT_DATE_RE.findall(text)))
    if len(tokens) != 1:
        raise StatementImportError("Statement contains an ambiguous as-of date")
    try:
        return datetime.strptime(tokens[0], "%d.%m.%Y").replace(tzinfo=timezone.utc)
    except ValueError as err:
        raise StatementImportError("Statement as-of date is invalid") from err


def _unique_creation_timestamp(text: str) -> datetime:
    matches = tuple(dict.fromkeys(_CREATED_RE.findall(text)))
    if len(matches) != 1:
        raise StatementImportError("Statement contains an ambiguous creation timestamp")
    date_token, time_token, offset_token = matches[0]
    sign = 1 if offset_token[0] == "+" else -1
    hours, minutes = (int(part) for part in offset_token[1:].split(":"))
    if hours > 14 or minutes > 59:
        raise StatementImportError("Statement creation timezone offset is invalid")
    offset = timezone(sign * timedelta(hours=hours, minutes=minutes))
    try:
        return datetime.strptime(
            f"{date_token} {time_token}", "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=offset)
    except ValueError as err:
        raise StatementImportError("Statement creation timestamp is invalid") from err


def _unique_summary(text: str) -> tuple[int, Decimal]:
    raw = _SUMMARY_RE.findall(text)
    summaries: list[tuple[int, Decimal]] = []
    for count_token, value_token in raw:
        summaries.append(
            (int(count_token), _parse_german_decimal(value_token, field="portfolio total"))
        )
    unique = tuple(dict.fromkeys(summaries))
    if len(unique) != 1:
        raise StatementImportError("Statement contains an ambiguous holdings summary")
    count, total = unique[0]
    if not 1 <= count <= MAX_IMPORT_POSITIONS or total <= 0:
        raise StatementImportError("Statement holdings summary is outside the supported range")
    return count, total


def _parse_german_decimal(token: str, *, field: str) -> Decimal:
    cleaned = token.strip()
    if _GERMAN_NUMBER_RE.fullmatch(cleaned) is None:
        raise StatementImportError(f"Statement {field} is not a supported German decimal")
    canonical = cleaned.replace(".", "").replace(",", ".")
    try:
        value = Decimal(canonical)
    except InvalidOperation as err:
        raise StatementImportError(f"Statement {field} is invalid") from err
    if not value.is_finite() or value < 0:
        raise StatementImportError(f"Statement {field} is outside the supported range")
    return value


def _clean_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > 160 or any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise StatementImportError("Statement position name is invalid")
    return cleaned


def _instrument_type(block: str) -> str:
    token = block.casefold()
    if re.search(r"\betf\b", token) or "ucits" in token:
        return "ETF"
    if re.search(r"\betc\b", token):
        return "ETC"
    if re.search(r"\betn\b", token):
        return "ETN"
    if "anleihe" in token or re.search(r"\bbond\b", token):
        return "Bond"
    if "aktie" in token or re.search(r"\bshare\b", token):
        return "Stock"
    return "Other"
