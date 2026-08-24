"""Test-only loader for the historical sanitized reference portfolio.

The fixture retains the long-established Comdirect-shaped columns because many
engine regressions predate the provider-Gateway architecture.  Production code
no longer contains a Comdirect CSV adapter; tests read the sanitized fixture
through the provider-neutral generic mapped-CSV adapter instead.
"""

from __future__ import annotations

from pathlib import Path

from engine.importers import CsvSourceConfig, PROVIDER_GENERIC_CSV, read_positions

ROOT = Path(__file__).parents[1]
REFERENCE_CSV = ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv"
REFERENCE_PROVIDER = PROVIDER_GENERIC_CSV
REFERENCE_LABEL = "Mapped generic CSV"


def reference_source_config() -> CsvSourceConfig:
    """Return the explicit generic mapping for the sanitized historical fixture."""
    return CsvSourceConfig(
        provider=PROVIDER_GENERIC_CSV,
        encoding="iso-8859-1",
        delimiter="semicolon",
        header_row=1,
        decimal_format="comma_decimal",
        identifier_column="WKN",
        name_column="Bezeichnung",
        value_column="Wert in EUR",
        isin_column="ISIN",
        type_column="Typ",
    )


def read_reference_positions():
    """Read the sanitized reference holdings through only current production code."""
    return read_positions(REFERENCE_CSV, reference_source_config())
