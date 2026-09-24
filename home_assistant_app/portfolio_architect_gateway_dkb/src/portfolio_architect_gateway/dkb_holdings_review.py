"""Transient admin-only display of independent CSV and FinTS holdings evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
import re
from typing import Any

from .models import PortfolioSnapshot, canonical_decimal

MAX_REVIEW_ROWS = 64
MAX_RAW_RESPONSE_BYTES = 1_048_576
_ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_TOTAL_CURRENCY = re.compile(r"^:19A::HOLD//([A-Z]{3})[0-9]+,[0-9]+(?:$|[^0-9])")
_SYMBOL = re.compile(r"^[A-Z]{3}$")
_MAX_NUMBER = Decimal("1000000000")


@dataclass(frozen=True, slots=True)
class ReviewRow:
    isin: str
    quantity: str
    value: str
    currency: str
    price_date: str
    instrument_line: str = "unavailable"
    unit_price_currency: str = "unavailable"


@dataclass(frozen=True, slots=True)
class RawPositionEvidence:
    """Short fields from one FIN section, never a retained MT535 response."""
    instrument_line: str = "unavailable"
    total_currency: str = "unavailable"


@dataclass(frozen=True, slots=True)
class HoldingsReview:
    csv_as_of: str | None
    fints_observed_at: str
    csv_rows: tuple[ReviewRow, ...] | None
    fints_rows: tuple[ReviewRow, ...]


def _number(value: Any) -> str:
    if type(value) not in (int, float, Decimal):
        return "unavailable"
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "unavailable"
    if not result.is_finite() or result < 0 or result > _MAX_NUMBER:
        return "unavailable"
    rendered = format(result, "f")
    return rendered if len(rendered) <= 32 else "unavailable"


def project_raw_hiwpd(responses: Any) -> tuple[RawPositionEvidence, ...] | None:
    """Extract bounded 35B and HOLD currency markers before PyFinTS drops them."""
    if not isinstance(responses, (tuple, list)) or len(responses) > MAX_REVIEW_ROWS:
        return None
    rows: list[RawPositionEvidence] = []
    total_bytes = 0
    for response in responses:
        payload = getattr(response, "holdings", None)
        if isinstance(payload, bytes):
            total_bytes += len(payload)
            if total_bytes > MAX_RAW_RESPONSE_BYTES:
                return None
            try:
                content = payload.decode("utf-8")
            except UnicodeDecodeError:
                return None
        elif isinstance(payload, str):
            total_bytes += len(payload)
            if total_bytes > MAX_RAW_RESPONSE_BYTES:
                return None
            content = payload
        else:
            return None
        inside = collecting_identifier = False
        identifier = currency = "unavailable"
        for line in content.splitlines():
            if line.startswith(":16R:FIN"):
                inside = True
                collecting_identifier = False
                identifier = currency = "unavailable"
            elif line.startswith(":16S:FIN") and inside:
                rows.append(RawPositionEvidence(identifier or "unavailable", currency))
                if len(rows) > MAX_REVIEW_ROWS:
                    return None
                inside = False
            elif inside and line.startswith(":35B:"):
                identifier = line[5:]
                collecting_identifier = True
            elif inside and line.startswith(":19A::HOLD//"):
                collecting_identifier = False
                match = _TOTAL_CURRENCY.match(line)
                currency = match.group(1) if match else "unavailable"
            elif inside and line.startswith(":"):
                collecting_identifier = False
            elif inside and collecting_identifier and not line.startswith("-"):
                # MT535 can continue the instrument marker on the next line.
                identifier += ("|" if identifier else "") + line
            if collecting_identifier and identifier != "unavailable":
                # Retain a legible prefix instead of hiding a long marker.
                over_limit = len(identifier) > 96
                identifier = "".join(char if char.isprintable() else "�" for char in identifier[:96])
                if over_limit:
                    collecting_identifier = False
                    identifier += "…"
    return tuple(rows)


def project_fints(holdings: list[Any] | tuple[Any, ...],
                  raw: tuple[RawPositionEvidence, ...] | None = None) -> tuple[ReviewRow, ...] | None:
    """Project only fixed bounded fields; never retain PyFinTS objects."""
    if len(holdings) > MAX_REVIEW_ROWS:
        return None
    rows = []
    # Never attach a raw field to the wrong holding if the two parsers disagree.
    evidence = raw if raw is not None and len(raw) == len(holdings) else None
    for index, item in enumerate(holdings):
        identifier = getattr(item, "ISIN", None)
        isin = identifier.upper() if isinstance(identifier, str) and _ISIN.fullmatch(identifier.upper()) else "unavailable"
        price_date = getattr(item, "valuation_date", None)
        symbol = getattr(item, "value_symbol", None)
        rows.append(ReviewRow(
            isin=isin,
            quantity=_number(getattr(item, "pieces", None)),
            value=_number(getattr(item, "total_value", None)),
            currency=evidence[index].total_currency if evidence is not None else "unavailable",
            price_date=price_date.isoformat() if type(price_date) is date else "unavailable",
            instrument_line=evidence[index].instrument_line if evidence is not None else "unavailable",
            unit_price_currency=symbol if isinstance(symbol, str) and _SYMBOL.fullmatch(symbol) else "unavailable",
        ))
    return tuple(rows)


def build_review(snapshot: PortfolioSnapshot | None, observed_at: str,
                 fints_rows: tuple[ReviewRow, ...]) -> HoldingsReview:
    csv_rows = None
    csv_as_of = None
    if snapshot is not None:
        # The CSV exporter provides a date, not a time of day. The canonical
        # snapshot's midnight UTC is only a storage representation.
        csv_as_of = snapshot.generated_at.date().isoformat()
        if len(snapshot.positions) <= MAX_REVIEW_ROWS:
            csv_rows = tuple(ReviewRow(
                isin=position.isin or "unavailable",
                quantity=canonical_decimal(position.quantity) if position.quantity is not None else "unavailable",
                value=canonical_decimal(position.market_value_eur),
                currency="EUR",
                price_date="unavailable",
            ) for position in snapshot.positions)
    return HoldingsReview(csv_as_of, observed_at, csv_rows, fints_rows)


def render_review(review: HoldingsReview) -> str:
    def table(label: str, time_label: str, as_of: str, rows: tuple[ReviewRow, ...] | None) -> str:
        heading = f"<h4>{escape(label)}</h4><p>{escape(time_label)}: {escape(as_of)}</p>"
        if rows is None:
            return heading + f"<p>Position detail unavailable (missing source or over {MAX_REVIEW_ROWS} rows).</p>"
        body = "".join(
            "<tr>" + "".join(f"<th scope=\"row\">{escape(row.isin)}</th>" if index == 0 else
                                  f"<td>{escape(value)}</td>" for index, value in enumerate((
                row.isin, row.quantity, row.value, row.currency, row.price_date,
                row.instrument_line, row.unit_price_currency,
            ))) + "</tr>" for row in rows
        )
        return (heading + '<div style="overflow-x:auto"><table style="border-collapse:separate;border-spacing:.7rem .4rem;white-space:nowrap">'
                '<thead><tr><th>Parsed ISIN</th><th>Quantity</th><th>Total value</th><th>Total currency</th>'
                '<th>Price date</th><th>Bank instrument field</th><th>Unit price currency</th></tr></thead><tbody>'
                + body + '</tbody></table></div>')

    return ('<h3>Transient holdings evidence</h3><p>Review the two observations yourself. '
            'Different timestamps, trades or valuation methods can explain differences. '
            'The CSV snapshot may aggregate several depot exports; FinTS reads one authorized depot. '
            'The bank instrument field and total-value currency are shown only when a bounded FIN section can be read; '
            'the unit-price currency is a separate field and must not be used as the total-value currency. '
            'This detail expires five minutes after retrieval and is never saved.</p>'
            '<div style="display:grid;grid-template-columns:minmax(0,1fr);gap:1rem">'
            + '<div>' + table('DKB CSV (authoritative)', 'Export date (date only)',
                              review.csv_as_of or 'unavailable', review.csv_rows) + '</div>'
            + '<div>' + table('DKB FinTS (research only)', 'Observed UTC',
                              review.fints_observed_at, review.fints_rows) + '</div></div>')
