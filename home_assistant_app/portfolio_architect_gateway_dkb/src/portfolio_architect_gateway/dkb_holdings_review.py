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
_ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_MAX_NUMBER = Decimal("1000000000")


@dataclass(frozen=True, slots=True)
class ReviewRow:
    isin: str
    quantity: str
    value: str
    currency: str
    price_date: str


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


def project_fints(holdings: list[Any] | tuple[Any, ...]) -> tuple[ReviewRow, ...] | None:
    """Project only fixed bounded fields; never retain PyFinTS objects."""
    if len(holdings) > MAX_REVIEW_ROWS:
        return None
    rows = []
    for item in holdings:
        identifier = getattr(item, "ISIN", None)
        isin = identifier.upper() if isinstance(identifier, str) and _ISIN.fullmatch(identifier.upper()) else "unavailable"
        price_date = getattr(item, "valuation_date", None)
        rows.append(ReviewRow(
            isin=isin,
            quantity=_number(getattr(item, "pieces", None)),
            value=_number(getattr(item, "total_value", None)),
            # PyFinTS's value_symbol belongs to the unit market price, not
            # necessarily the total holding value. Never infer its currency.
            currency="unavailable",
            price_date=price_date.isoformat() if type(price_date) is date else "unavailable",
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
            "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in (
                row.isin, row.quantity, row.value, row.currency, row.price_date,
            )) + "</tr>" for row in rows
        )
        return (heading + '<div style="overflow-x:auto"><table><thead><tr><th>ISIN</th><th>Quantity</th>'
                '<th>Value</th><th>Currency</th><th>Price date</th></tr></thead><tbody>'
                + body + '</tbody></table></div>')

    return ('<h3>Transient holdings evidence</h3><p>Review the two observations yourself. '
            'Different timestamps, trades or valuation methods can explain differences. '
            'The CSV snapshot may aggregate several depot exports; FinTS reads one authorized depot. '
            'The FinTS total-value currency is not exposed by the parser. '
            'This detail expires five minutes after retrieval and is never saved.</p>'
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(20rem,1fr));gap:1rem">'
            + '<div>' + table('DKB CSV (authoritative)', 'Export date (date only)',
                              review.csv_as_of or 'unavailable', review.csv_rows) + '</div>'
            + '<div>' + table('DKB FinTS (research only)', 'Observed UTC',
                              review.fints_observed_at, review.fints_rows) + '</div></div>')
