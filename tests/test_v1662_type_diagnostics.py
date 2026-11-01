"""Unknown source types must remain distinguishable from real disagreements."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

import yaml

COMPONENT = Path(__file__).parents[1] / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.aggregation import PortfolioSourceSnapshot, aggregate_sources  # noqa: E402
from engine.models import Position  # noqa: E402
from source_type_diagnostics import describe_instrument_type_findings  # noqa: E402


def _position(isin: str, instrument_type: str) -> Position:
    return Position(
        wkn="",
        isin=isin,
        name="Instrument",
        instrument_type=instrument_type,
        source_type=instrument_type,
        value_eur=Decimal("10"),
    )


def test_live_type_gaps_are_not_presented_as_identity_collisions() -> None:
    world = "IE00BJ0KDQ92"
    emerging = "IE00BTJRMP35"
    instant = datetime(2026, 10, 17, tzinfo=timezone.utc)
    result = aggregate_sources(
        (
            PortfolioSourceSnapshot("comdirect", "comdirect", "Comdirect", instant, {
                world: _position(world, "etf"), emerging: _position(emerging, "etf")
            }),
            PortfolioSourceSnapshot("dkb", "dkb", "DKB", instant, {
                world: _position(world, "other")
            }),
            PortfolioSourceSnapshot("tr", "trade_republic", "TR", instant, {
                emerging: _position(emerging, "other")
            }),
        )
    )
    assert len(result.positions) == 2
    assert all(position.value_eur == Decimal("20") for position in result.positions.values())
    presentation = describe_instrument_type_findings(item.to_dict() for item in result.conflicts)
    assert presentation["unspecified_type_count"] == 2
    assert presentation["known_type_conflict_count"] == 0
    assert presentation["finding_summary"] == "2 unspecified types"
    assert presentation["finding_summary_de"] == "2 unbekannte Typangaben"
    assert {item["classification"] for item in presentation["findings"]} == {"type_unspecified"}


def test_known_disagreement_survives_and_old_cached_findings_are_classified() -> None:
    old_cached = [
        {"identity": "IE00BTJRMP35", "field": "instrument_type", "observed": ["etf", "other"]},
        {"identity": "IE00BJ0KDQ92", "field": "instrument_type", "observed": ["etf", "stock"]},
    ]
    presentation = describe_instrument_type_findings(old_cached)
    assert presentation["unspecified_type_count"] == 1
    assert presentation["known_type_conflict_count"] == 1
    assert presentation["finding_summary"] == "1 unspecified type · 1 known type conflict"
    assert presentation["findings"][1]["classification"] == "known_type_disagreement"
    assert old_cached[0]["observed"] == ["etf", "other"]
    assert "classification" not in old_cached[0]


def test_generated_dashboards_show_the_right_summary_in_each_language() -> None:
    root = Path(__file__).parents[1]
    for locale, name, attribute in (
        ("en", "Instrument types", "finding_summary"),
        ("de", "Instrumenttypen", "finding_summary_de"),
    ):
        dashboard = yaml.safe_load((root / "dashboard/generated" / f"portfolio-architect-dashboard-{locale}.yaml").read_text())
        cards = dashboard["views"][0]["sections"][3]["cards"]
        card = next(card["card"] for card in cards if card.get("card", {}).get("entity") == "sensor.portfolio_architect_source_conflict_count")
        assert card["name"] == name
        assert card["state_content"] == attribute
