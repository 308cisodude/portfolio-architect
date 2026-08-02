"""CSV provider-adapter compatibility contract tests."""

from decimal import Decimal
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.importers import (  # noqa: E402
    CsvSourceConfig,
    PROVIDER_COMDIRECT,
    PROVIDER_GENERIC_CSV,
    inspect_csv_headers,
    read_positions,
)


def test_comdirect_adapter_remains_default_and_reads_reference_export() -> None:
    config = CsvSourceConfig.from_mapping(None)
    assert config.provider == PROVIDER_COMDIRECT
    positions = read_positions(ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv", config)
    assert len(positions) == 13
    assert sum(item.value_eur for item in positions.values()) == Decimal("14053.01")


def test_generic_csv_mapping_supports_utf8_comma_and_isin_identifier(tmp_path: Path) -> None:
    path = tmp_path / "portfolio.csv"
    path.write_text(
        "Identifier,Security,Market Value,Currency,ISIN,Asset Type\n"
        'A1XB5U,ETF One,"1,234.56",EUR,IE00BJ0KDQ92,ETF\n'
        "DE0005557508,Telekom,200.00,EUR,DE0005557508,Stock\n",
        encoding="utf-8",
    )
    config = CsvSourceConfig(
        provider=PROVIDER_GENERIC_CSV,
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
    assert inspect_csv_headers(path, config) == (
        "Identifier",
        "Security",
        "Market Value",
        "Currency",
        "ISIN",
        "Asset Type",
    )
    positions = read_positions(path, config)
    assert positions["A1XB5U"].value_eur == Decimal("1234.56")
    assert positions["DE0005557508"].instrument_type == "stock"


def test_generic_csv_auto_detects_semicolon_and_german_numbers(tmp_path: Path) -> None:
    path = tmp_path / "portfolio.csv"
    path.write_text(
        "Kennung;Name;Wert;Währung\n"
        "A1XB5U;ETF One;1.234,56;EUR\n",
        encoding="utf-8",
    )
    config = CsvSourceConfig(
        provider=PROVIDER_GENERIC_CSV,
        encoding="auto",
        delimiter="auto",
        header_row=1,
        decimal_format="auto",
        identifier_column="Kennung",
        name_column="Name",
        value_column="Wert",
        currency_column="Währung",
    )
    positions = read_positions(path, config)
    assert positions["A1XB5U"].value_eur == Decimal("1234.56")


def test_generic_csv_rejects_non_eur_rows(tmp_path: Path) -> None:
    path = tmp_path / "portfolio.csv"
    path.write_text(
        "Identifier,Name,Value,Currency\nA1XB5U,ETF One,100.00,USD\n",
        encoding="utf-8",
    )
    config = CsvSourceConfig(
        provider=PROVIDER_GENERIC_CSV,
        encoding="utf-8",
        delimiter="comma",
        header_row=1,
        decimal_format="dot_decimal",
        identifier_column="Identifier",
        name_column="Name",
        value_column="Value",
        currency_column="Currency",
    )
    with pytest.raises(ValueError, match="not denominated in EUR"):
        read_positions(path, config)


def test_generic_csv_rejects_duplicate_headers_and_identifiers(tmp_path: Path) -> None:
    duplicate_headers = tmp_path / "headers.csv"
    duplicate_headers.write_text("ID,Name,Name\nA1XB5U,One,100\n", encoding="utf-8")
    partial = CsvSourceConfig(
        provider=PROVIDER_GENERIC_CSV,
        encoding="utf-8",
        delimiter="comma",
        header_row=1,
        decimal_format="auto",
    )
    with pytest.raises(ValueError, match="header names must be unique"):
        inspect_csv_headers(duplicate_headers, partial)

    duplicate_ids = tmp_path / "ids.csv"
    duplicate_ids.write_text(
        "ID,Name,Value\nA1XB5U,One,100\nA1XB5U,Two,200\n",
        encoding="utf-8",
    )
    config = CsvSourceConfig(
        provider=PROVIDER_GENERIC_CSV,
        encoding="utf-8",
        delimiter="comma",
        header_row=1,
        decimal_format="auto",
        identifier_column="ID",
        name_column="Name",
        value_column="Value",
    )
    with pytest.raises(ValueError, match="duplicate instrument identifier"):
        read_positions(duplicate_ids, config)


def test_config_flow_exposes_provider_format_mapping_and_reconfigure() -> None:
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    setup = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "async_step_generic_format" in flow
    assert "async_step_generic_mapping" in flow
    assert "CONF_SOURCE_PROVIDER" in flow
    assert "inspect_csv_headers" in flow
    assert "CsvSourceConfig.from_mapping" in flow
    assert "entry.version < 6" in setup
    assert "entry.version < 7" in setup
    assert "DEFAULT_SOURCE_PROVIDER" in setup


def test_generic_adapter_produces_same_schema_8_calculation(tmp_path: Path) -> None:
    import csv
    from engine import calculate_portfolio_payload

    comdirect = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv", CsvSourceConfig(provider=PROVIDER_COMDIRECT)
    )
    path = tmp_path / "generic.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Identifier", "Name", "Value", "Currency", "ISIN", "Type"])
        for item in comdirect.values():
            writer.writerow(
                [item.wkn, item.name, str(item.value_eur), "EUR", item.isin, item.source_type]
            )
    config = CsvSourceConfig(
        provider=PROVIDER_GENERIC_CSV,
        encoding="utf-8",
        delimiter="comma",
        header_row=1,
        decimal_format="dot_decimal",
        identifier_column="Identifier",
        name_column="Name",
        value_column="Value",
        currency_column="Currency",
        isin_column="ISIN",
        type_column="Type",
    )
    payload = calculate_portfolio_payload(
        path, ROOT / "examples" / "current-plan", source_config=config
    )
    assert payload["schema_version"] == 8
    assert payload["summary"]["payload_schema_version"] == 8
    assert payload["summary"]["source_provider"] == PROVIDER_GENERIC_CSV
    assert payload["summary"]["whole_portfolio_value_eur"] == Decimal("14053.01")
    assert len(payload["holdings"]) == 13
    assert len(payload["recommendations"]) == 7
