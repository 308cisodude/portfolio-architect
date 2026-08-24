"""Provider-neutral mapped CSV import security and instrument-scope tests."""

from pathlib import Path
import sys

import pytest

ENGINE_ROOT = Path(__file__).parents[1] / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(ENGINE_ROOT))

from engine.importers import CsvSourceConfig, PROVIDER_GENERIC_CSV, read_positions  # noqa:E402


def _config() -> CsvSourceConfig:
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


def _write(path: Path, body: str) -> None:
    path.write_bytes(body.encode("iso-8859-1"))


def test_all_security_types_are_imported(tmp_path: Path) -> None:
    path = tmp_path / "mapped.csv"
    _write(
        path,
        "Bezeichnung;WKN;Typ;Wert in EUR;ISIN\n"
        "ETF One;A1XB5U;ETF;100,00;IE00BJ0KDQ92\n"
        "Stock One;555750;Aktie;200,00;DE0005557508\n",
    )
    positions = read_positions(path, _config())
    assert set(positions) == {"A1XB5U", "555750"}
    assert positions["A1XB5U"].instrument_type == "etf"
    assert positions["555750"].instrument_type == "stock"


def test_duplicate_identifier_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "mapped.csv"
    _write(
        path,
        "Bezeichnung;WKN;Typ;Wert in EUR;ISIN\n"
        "One;555750;Aktie;100,00;DE0005557508\n"
        "Two;555750;Aktie;200,00;DE0005557508\n",
    )
    with pytest.raises(ValueError, match="duplicate instrument identifier"):
        read_positions(path, _config())
