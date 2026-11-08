"""Bounded statement dispatch; combined statements retain only brokerage and cash."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import re
from zoneinfo import ZoneInfo

from .trade_republic_pdf import extract_bounded_pdf_text, TradeRepublicPdfError
from .trade_republic_statement import (
    StatementImportError, parse_statement_text, _unique_creation_timestamp,
    _parse_german_decimal, _unique_summary,
)
from .trade_republic_cash_statement import (
    TradeRepublicCashSnapshot, parse_cash_statement_text, MAX_CASH_EUR,
)
from .models import PortfolioSnapshot


@dataclass(frozen=True)
class StatementEvidence:
    holdings: PortfolioSnapshot | None = None
    cash: TradeRepublicCashSnapshot | None = None


def parse_import_pdf(data: bytes, *, now: datetime | None = None) -> StatementEvidence:
    try:
        text = extract_bounded_pdf_text(data)
    except TradeRepublicPdfError as err:
        raise StatementImportError(str(err)) from err
    if re.search(r"\bVERMÖGENSÜBERSICHT\b", text):
        return parse_net_worth_text(text, now=now)
    if re.search(r"\bDEPOTAUSZUG\b", text):
        return StatementEvidence(holdings=parse_statement_text(text, now=now))
    return StatementEvidence(cash=parse_cash_statement_text(text, now=now))


def parse_net_worth_text(text: str, *, now: datetime | None = None) -> StatementEvidence:
    def reject():
        raise StatementImportError("Combined statement sections do not reconcile")
    text = text.replace("\u00a0", " ").replace("\r", "")
    # Explicit section boundaries, including a crypto section continued over a page.
    headings = list(re.finditer(r"(?m)^\s*(VERMÖGENSÜBERSICHT|BROKERAGE|CRYPTO WALLET|CASH)\s*$", text))
    if [m.group(1) for m in headings] != ["VERMÖGENSÜBERSICHT", "BROKERAGE", "CRYPTO WALLET", "CASH"]:
        reject()
    if re.search(r"\b(?:DEPOTAUSZUG|KONTOÜBERSICHT|BARMITTELÜBERSICHT)\b", text):
        reject()
    overview = text[headings[0].end():headings[1].start()]
    brokerage = text[headings[1].end():headings[2].start()]
    crypto = text[headings[2].end():headings[3].start()]
    cash = text[headings[3].end():]
    dates = re.findall(r"\bzum\s+(\d{2}\.\d{2}\.\d{4})\.", brokerage + crypto + cash)
    main_dates = re.findall(r"^\s*zum\s+(\d{2}\.\d{2}\.\d{4})\s*$", overview, re.M)
    if len(dates) != 3 or len(main_dates) != 1 or set(dates) != set(main_dates):
        reject()
    stamp = _unique_creation_timestamp(text)
    # Date-only evidence is conservatively dated at the beginning of that local day.
    try:
        observed = datetime.strptime(main_dates[0], "%d.%m.%Y").replace(tzinfo=ZoneInfo("Europe/Berlin")).astimezone(timezone.utc)
    except ValueError:
        reject()
    creation = re.search(r"Erstellt\s+am[^\n]+", text)
    if creation is None:
        reject()
    holdings = parse_statement_text(
        "TRADE REPUBLIC BANK GMBH\nDEPOTAUSZUG zum " + main_dates[0] + "\n" + brokerage + "\n" + creation.group(), now=now
    )
    if "TRADE REPUBLIC BANK GMBH" not in text.upper() or stamp.date() != datetime.strptime(main_dates[0], "%d.%m.%Y").date():
        reject()
    number = r"(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+),[0-9]{2}"
    def amount(label, section, currency=False):
        matches = re.findall(r"(?m)^\s*" + label + r"\s+(" + number + r")" + (r"\s+EUR" if currency else "") + r"\s*$", section)
        if len(matches) != 1:
            reject()
        return _parse_german_decimal(matches[0], field="portfolio total")
    b = amount("Brokerage", overview)
    c = amount("Cash", overview)
    k = amount("Crypto Wallet", overview)
    total = amount("GESAMT", overview, True)
    balance = amount("Cashkonto", cash, True)
    _, brokerage_total = _unique_summary(brokerage)
    crypto_summaries = re.findall(r"ANZAHL\s+POSITIONEN:\s*([0-9]+)\s+(" + number + r")\s+EUR", crypto)
    if len(crypto_summaries) != 1:
        reject()
    crypto_total = _parse_german_decimal(crypto_summaries[0][1], field="portfolio total")
    if b != brokerage_total or k != crypto_total or c != balance or b + c + k != total or c > MAX_CASH_EUR:
        reject()
    return StatementEvidence(
        holdings=replace(holdings, generated_at=observed),
        cash=TradeRepublicCashSnapshot(balance, observed, stamp.astimezone(timezone.utc)),
    )
