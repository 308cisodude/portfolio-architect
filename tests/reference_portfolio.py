"""Test-only loader for the historical sanitized reference portfolio.

The long-established fixture remains intentionally test-only. Production Portfolio
Architect no longer contains any local CSV acquisition/parser; provider-neutral
mapped CSV acquisition lives in the Generic Import Gateway from v1.51 onward.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
if str(COMPONENT) not in sys.path:
    sys.path.insert(0, str(COMPONENT))

from engine.models import Position

REFERENCE_CSV = ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv"
REFERENCE_PROVIDER = "generic_csv"
REFERENCE_LABEL = "Sanitized test fixture"


def _euro(value: str) -> Decimal:
    return Decimal(value.replace(".", "").replace(",", "."))


def read_reference_positions() -> dict[str, Position]:
    """Read the sanitized historical fixture without using production acquisition."""
    result: dict[str, Position] = {}
    with REFERENCE_CSV.open("r", encoding="iso-8859-1", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            wkn = str(row["WKN"]).strip().upper()
            source_type = str(row["Typ"]).strip()
            result[wkn] = Position(
                wkn=wkn,
                isin=str(row["ISIN"]).strip().upper(),
                name=str(row["Bezeichnung"]).strip(),
                instrument_type={"etf": "etf", "aktie": "stock"}.get(
                    source_type.casefold(), "other"
                ),
                source_type=source_type,
                value_eur=_euro(str(row["Wert in EUR"])),
            )
    return result
