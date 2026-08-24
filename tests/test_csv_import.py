"""Generic Import Gateway mapped-CSV security and instrument-scope tests."""

from __future__ import annotations

from decimal import Decimal
import importlib
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
PACKAGE = (
    ROOT
    / "home_assistant_app"
    / "portfolio_architect_gateway_import"
    / "src"
    / "portfolio_architect_gateway"
)
TEST_PACKAGE = "portfolio_architect_gateway_generic_import_csv_test"


def _modules():
    if TEST_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            TEST_PACKAGE,
            PACKAGE / "__init__.py",
            submodule_search_locations=[str(PACKAGE)],
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[TEST_PACKAGE] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f"{TEST_PACKAGE}.generic_csv")


def _config():
    generic = _modules()
    return generic.GenericCsvConfig(
        encoding="iso-8859-1",
        delimiter="semicolon",
        header_row=1,
        decimal_format="comma_decimal",
        identifier_column="WKN",
        name_column="Bezeichnung",
        value_column="Wert in EUR",
        isin_column="ISIN",
        type_column="Typ",
        currency_column=None,
    )


def test_all_security_types_are_imported() -> None:
    generic = _modules()
    body = (
        "Bezeichnung;WKN;Typ;Wert in EUR;ISIN\n"
        "ETF One;A1XB5U;ETF;100,00;IE00BJ0KDQ92\n"
        "Stock One;555750;Aktie;200,00;DE0005557508\n"
    ).encode("iso-8859-1")
    snapshot, _summary = generic.parse_generic_csv(body, _config())
    positions = {item.identifier: item for item in snapshot.positions}
    assert set(positions) == {"A1XB5U", "555750"}
    assert positions["A1XB5U"].instrument_type == "etf"
    assert positions["555750"].instrument_type == "stock"
    assert positions["A1XB5U"].market_value_eur == Decimal("100.00")


def test_duplicate_identifier_is_rejected() -> None:
    generic = _modules()
    body = (
        "Bezeichnung;WKN;Typ;Wert in EUR;ISIN\n"
        "One;555750;Aktie;100,00;DE0005557508\n"
        "Two;555750;Aktie;200,00;DE0005557508\n"
    ).encode("iso-8859-1")
    with pytest.raises(generic.GenericCsvImportError, match="duplicate instrument identifier"):
        generic.parse_generic_csv(body, _config())
