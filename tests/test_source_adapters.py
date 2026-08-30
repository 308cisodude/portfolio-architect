"""v1.51 Generic Import Gateway acquisition-boundary contract tests."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_import"
PACKAGE = APP / "src" / "portfolio_architect_gateway"
TEST_PACKAGE = "portfolio_architect_gateway_generic_import_adapter_test"


def _generic():
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


def test_generic_adapter_is_gateway_only() -> None:
    assert not (COMPONENT / "engine" / "importers.py").exists()
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    assert "async_step_generic_format" not in flow
    assert "async_step_generic_mapping" not in flow
    assert "inspect_csv_headers" not in flow
    assert "CsvSourceConfig" not in flow
    assert "SOURCE_TYPE_LOCAL_FILES" not in flow


def test_generic_csv_mapping_supports_utf8_comma_and_isin_identifier() -> None:
    generic = _generic()
    body = (
        "Identifier,Security,Market Value,Currency,ISIN,Asset Type\n"
        'A1XB5U,ETF One,"1,234.56",EUR,IE00BJ0KDQ92,ETF\n'
        "DE0005557508,Telekom,200.00,EUR,DE0005557508,Stock\n"
    ).encode()
    config = generic.GenericCsvConfig(
        encoding="utf-8",
        delimiter="comma",
        header_row=1,
        decimal_format="dot_decimal",
        identifier_column="Identifier",
        name_column="Security",
        value_column="Market Value",
        isin_column="ISIN",
        type_column="Asset Type",
        currency_column="Currency",
    )
    assert generic.inspect_csv_headers(body, config) == (
        "Identifier", "Security", "Market Value", "Currency", "ISIN", "Asset Type"
    )
    snapshot, summary = generic.parse_generic_csv(
        body, config, generated_at=datetime(2026, 8, 24, 18, 0, tzinfo=timezone.utc)
    )
    positions = {item.identifier: item for item in snapshot.positions}
    assert summary.position_count == 2
    assert positions["A1XB5U"].market_value_eur == Decimal("1234.56")
    assert positions["DE0005557508"].instrument_type == "stock"
    assert snapshot.generated_at == datetime(2026, 8, 24, 18, 0, tzinfo=timezone.utc)


def test_generic_csv_auto_detects_semicolon_and_german_numbers() -> None:
    generic = _generic()
    body = "Kennung;Name;Wert;Währung\nA1XB5U;ETF One;1.234,56;EUR\n".encode()
    config = generic.GenericCsvConfig(
        encoding="auto", delimiter="auto", decimal_format="auto",
        identifier_column="Kennung", name_column="Name", value_column="Wert",
        isin_column=None, type_column=None, currency_column="Währung",
    )
    snapshot, _ = generic.parse_generic_csv(body, config)
    assert snapshot.positions[0].market_value_eur == Decimal("1234.56")


def test_generic_csv_rejects_non_eur_rows() -> None:
    generic = _generic()
    body = b"Identifier,Name,Value,Currency\nA1XB5U,ETF One,100.00,USD\n"
    config = generic.GenericCsvConfig(
        encoding="utf-8", delimiter="comma", decimal_format="dot_decimal",
        identifier_column="Identifier", name_column="Name", value_column="Value",
        isin_column=None, type_column=None, currency_column="Currency",
    )
    with pytest.raises(generic.GenericCsvImportError, match="not denominated in EUR"):
        generic.parse_generic_csv(body, config)


def test_generic_csv_rejects_duplicate_headers_and_identifiers() -> None:
    generic = _generic()
    partial = generic.GenericCsvConfig(
        encoding="utf-8", delimiter="comma", decimal_format="auto",
        identifier_column="ID", name_column="Name", value_column="Value",
        isin_column=None, type_column=None, currency_column=None,
    )
    with pytest.raises(generic.GenericCsvImportError, match="header names must be unique"):
        generic.inspect_csv_headers(b"ID,Name,Name\nA1XB5U,One,100\n", partial)
    with pytest.raises(generic.GenericCsvImportError, match="duplicate instrument identifier"):
        generic.parse_generic_csv(
            b"ID,Name,Value\nA1XB5U,One,100\nA1XB5U,Two,200\n", partial
        )


def test_schema_12_migration_is_fail_closed_for_active_local_csv() -> None:
    setup = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "entry.version < 12" in setup
    assert "Generic Import v1.59.0" in setup
    assert "Cannot migrate Portfolio Architect to schema 12 while local CSV" in setup
    assert "return False" in setup
