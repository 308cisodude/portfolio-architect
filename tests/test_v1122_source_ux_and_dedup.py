"""v1.12.2 source UX and DKB snapshot selection contracts."""

from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.importers import select_latest_dkb_exports  # noqa: E402


def _write_dkb(path: Path, *, date: str, depot: str, price: str = "100,00 €") -> None:
    path.write_text(
        "Datum der Erstellung;Depotnummer;Wertpapierbezeichnung;WKN;ISIN;Einstiegskurs;Bewertungskurs;Stückzahl;Absoluter Gewinn;Relativer Gewinn;Assetklasse\n"
        f"{date};{depot};X(IE)-MSCI WORLD 1C;A1XB5U;IE00BJ0KDQ92;\"141,76 €\";\"{price}\";2;-,--; -;ETFs\n",
        encoding="utf-8",
    )


def test_newest_export_for_same_dkb_depot_supersedes_older(tmp_path: Path) -> None:
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    other = tmp_path / "other.csv"
    _write_dkb(old, date="31.07.2026", depot="111111111")
    _write_dkb(new, date="01.08.2026", depot="111111111")
    _write_dkb(other, date="31.07.2026", depot="222222222")
    assert select_latest_dkb_exports((old, new, other)) == (new, other)


def test_same_depot_same_date_conflict_fails_closed(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write_dkb(first, date="31.07.2026", depot="111111111", price="100,00 €")
    _write_dkb(second, date="31.07.2026", depot="111111111", price="101,00 €")
    try:
        select_latest_dkb_exports((first, second))
    except ValueError as err:
        assert "same depot and date" in str(err)
    else:
        raise AssertionError("ambiguous same-date DKB exports must be rejected")


def test_provenance_uses_friendly_provider_labels() -> None:
    sensor = (COMPONENT / "sensor.py").read_text()
    coordinator = (COMPONENT / "coordinator.py").read_text()
    assert 'return "Comdirect REST"' in coordinator
    assert 'display_name = "Comdirect"' in sensor
    assert '"DKB"' in sensor
    assert "_compact_source_summary" in sensor
    assert "local-portfolio-architect-gateway/api" not in sensor


def test_outside_scope_holdings_use_bounded_native_dynamic_list() -> None:
    dashboard = yaml.safe_load((ROOT / "dashboard/allocation-stack.yaml").read_text())
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
