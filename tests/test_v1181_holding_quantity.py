"""v1.18.1 holding-quantity observability and dashboard wording contracts."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import sys

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.aggregation import PortfolioSourceSnapshot, aggregate_sources  # noqa: E402
from engine.models import Position  # noqa: E402


def _position(*, quantity: Decimal | None, value: str = "100") -> Position:
    return Position(
        wkn="A1XB5U",
        isin="IE00BJ0KDQ92",
        name="ETF One",
        instrument_type="etf",
        source_type="ETF",
        value_eur=Decimal(value),
        quantity=quantity,
    )


def test_quantity_is_summed_only_when_all_sources_supply_it() -> None:
    stamp = datetime(2026, 8, 9, tzinfo=timezone.utc)
    complete = aggregate_sources(
        (
            PortfolioSourceSnapshot("one", "local_rest_json", "One", stamp, {"A1XB5U": _position(quantity=Decimal("1.25"))}),
            PortfolioSourceSnapshot("two", "local_rest_json", "Two", stamp, {"A1XB5U": _position(quantity=Decimal("2.50"), value="200")}),
        )
    )
    assert complete.positions["A1XB5U"].quantity == Decimal("3.75")

    incomplete = aggregate_sources(
        (
            PortfolioSourceSnapshot("one", "local_rest_json", "One", stamp, {"A1XB5U": _position(quantity=Decimal("1.25"))}),
            PortfolioSourceSnapshot("two", "generic_csv", "Two", stamp, {"A1XB5U": _position(quantity=None, value="200")}),
        )
    )
    assert incomplete.positions["A1XB5U"].quantity is None


def test_holding_quantity_entity_contract_is_present() -> None:
    sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    assert "class PortfolioHoldingQuantitySensor" in sensor
    assert 'f"{self._position_id}_holding_quantity"' in sensor
    assert "self._holding.quantity is not None" in sensor

    en = json.loads((COMPONENT / "translations" / "en.json").read_text())
    de = json.loads((COMPONENT / "translations" / "de.json").read_text())
    icons = json.loads((COMPONENT / "icons.json").read_text())
    assert en["entity"]["sensor"]["holding_quantity"]["name"] == "{holding_name} quantity"
    assert de["entity"]["sensor"]["holding_quantity"]["name"] == "Stückzahl {holding_name}"
    assert icons["entity"]["sensor"]["holding_quantity"]["default"] == "mdi:numeric"


def test_dashboard_uses_accepted_terminology() -> None:
    source = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")
    assert "heading: Total portfolio value" in source
    assert "heading: Current portfolio allocation" in source
    assert "heading: Gesamtportfoliowert" in source
    assert "heading: Aktuelle Portfolioallokation" in source
    assert "heading: Complete portfolio" not in source
    assert "heading: Current plan drift" not in source


def test_stable_release_excludes_experimental_brokerage_probe_code() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["version"] == "1.62.4"
    assert not (ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "probe.py").exists()
    notes = (ROOT / "docs" / "RELEASE-NOTES.md").read_text()
    assert "v1.19.0-rc2" in notes
    assert "not promoted by this release" in notes
