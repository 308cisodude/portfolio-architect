"""v1.12 DKB supersession semantics retained inside the DKB Gateway."""

from pathlib import Path
import importlib
import importlib.util
import sys

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
PACKAGE = ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb" / "src" / "portfolio_architect_gateway"
TEST_PACKAGE = "portfolio_architect_gateway_dkb_v1122_test"


def _load_dkb_csv():
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
    return importlib.import_module(f"{TEST_PACKAGE}.dkb_csv")


def _dkb(*, date: str, depot: str, price: str = "100,00") -> bytes:
    return (
        "Datum der Erstellung;Depotnummer;Wertpapierbezeichnung;WKN;ISIN;"
        "Einstiegskurs;Bewertungskurs;Stückzahl;Absoluter Gewinn;Relativer Gewinn;Assetklasse\n"
        f'{date};{depot};X(IE)-MSCI WORLD 1C;A1XB5U;IE00BJ0KDQ92;"141,76 €";'
        f'"{price} €";2;-,--; -;ETFs\n'
    ).encode("utf-8")


def test_newest_export_for_same_dkb_depot_supersedes_older() -> None:
    dkb_csv = _load_dkb_csv()
    snapshot, summary = dkb_csv.parse_dkb_csv_batch(
        (
            _dkb(date="31.07.2026", depot="DEPOT-1"),
            _dkb(date="01.08.2026", depot="DEPOT-1"),
            _dkb(date="31.07.2026", depot="DEPOT-2"),
        )
    )
    assert summary.input_file_count == 3
    assert summary.selected_depot_count == 2
    assert len(snapshot.positions) == 1


def test_same_depot_same_date_conflict_fails_closed() -> None:
    dkb_csv = _load_dkb_csv()
    with pytest.raises(dkb_csv.DkbCsvImportError, match="same depot and date"):
        dkb_csv.parse_dkb_csv_batch(
            (
                _dkb(date="31.07.2026", depot="DEPOT-1", price="100,00"),
                _dkb(date="31.07.2026", depot="DEPOT-1", price="101,00"),
            )
        )


def test_provenance_uses_friendly_provider_labels() -> None:
    sensor = (COMPONENT / "sensor.py").read_text()
    coordinator = (COMPONENT / "coordinator.py").read_text()
    assert 'return "Comdirect REST"' in coordinator
    assert 'display_name = "Comdirect"' in sensor
    assert '"dkb": "DKB"' in coordinator
    assert "_compact_source_summary" in sensor
    assert "local-portfolio-architect-gateway/api" not in sensor


def test_outside_scope_holdings_use_bounded_native_dynamic_list() -> None:
    dashboard = yaml.safe_load((ROOT / "dashboard" / "allocation-stack.yaml").read_text())
    cards = dashboard["cards"]
    outside = next(
        item for item in cards
        if isinstance(item, dict)
        and item.get("type") == "entity-filter"
        and any((candidate.get("entity") if isinstance(candidate, dict) else candidate) == "sensor.portfolio_architect_presentation_outside_001_holding_value" for candidate in item.get("entities", []))
    )
    assert len(outside["entities"]) == 512
    assert outside["entities"][-1]["entity"] == "sensor.portfolio_architect_presentation_outside_512_holding_value"
    assert outside["card"]["type"] == "glance"
    assert outside["grid_options"]["columns"] == "full"
    assert outside["show_empty"] is False
