"""Provider-neutral multi-source aggregation contracts."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.aggregation import (  # noqa: E402
    PROVIDER_MULTI_SOURCE,
    PortfolioSourceSnapshot,
    aggregate_sources,
)
from engine.calculator import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.models import Position  # noqa: E402

DKB_PROVIDER = "dkb"


def _position(
    wkn: str,
    isin: str,
    value: str,
    *,
    name: str = "Instrument",
    instrument_type: str = "etf",
) -> Position:
    return Position(
        wkn=wkn,
        isin=isin,
        name=name,
        instrument_type=instrument_type,
        source_type=instrument_type,
        value_eur=Decimal(value),
    )


def _dkb_snapshot() -> dict[str, Position]:
    return {
        "A1XB5U": Position(
            wkn="A1XB5U",
            isin="IE00BJ0KDQ92",
            name="X(IE)-MSCI WORLD 1C",
            instrument_type="etf",
            source_type="etf",
            value_eur=Decimal("273.36"),
            quantity=Decimal("2"),
        )
    }


def _comdirect_snapshot() -> dict[str, Position]:
    rows = (
        ("555750", "DE0005557508", "Deutsche Telekom AG", "stock", "1355"),
        ("766400", "DE0007664005", "Volkswagen AG", "stock", "842.6"),
        ("A113FM", "IE00BM67HT60", "Information Technology", "etf", "2364"),
        ("A12GVR", "IE00BTJRMP35", "Emerging Markets", "etf", "1525.4"),
        ("A1X3W3", "DE000A1X3W34", "Legacy position", "stock", "0"),
        ("A1XB5U", "IE00BJ0KDQ92", "MSCI World", "etf", "135.275"),
        ("A2ANH2", "IE00BYZK4776", "Healthcare", "etf", "1711.087"),
        ("A2N6LC", "IE00BGV5VN51", "AI & Big Data", "etf", "4183.52"),
        ("A2QGAH", "IE00BLPK3577", "Cybersecurity", "etf", "123.3"),
        ("A2QKFF", "US61945M1018", "Small stock", "stock", "0.937"),
        ("A2QP7J", "US19260Q1076", "Coinbase", "stock", "140.16"),
        ("A3E5A5", "DE000A3E5A59", "Synbiotic", "stock", "17.07"),
        ("DBX0WG", "IE000F354Q61", "World Small Cap", "etf", "1562.4"),
    )
    return {
        wkn: _position(wkn, isin, value, name=name, instrument_type=kind)
        for wkn, isin, name, kind, value in rows
    }


def _source_metadata(aggregation) -> dict[str, object]:
    return {
        "source_count": len(aggregation.sources),
        "source_providers": [item.provider for item in aggregation.sources],
        "source_summaries": [item.to_dict() for item in aggregation.sources],
        "source_conflict_count": len(aggregation.conflicts),
        "source_conflicts": [item.to_dict() for item in aggregation.conflicts],
        "oldest_source_generated_at": aggregation.oldest_generated_at.isoformat(),
        "newest_source_generated_at": aggregation.newest_generated_at.isoformat(),
    }


def test_dkb_gateway_snapshot_shape_is_provider_neutral() -> None:
    positions = _dkb_snapshot()
    assert tuple(positions) == ("A1XB5U",)
    position = positions["A1XB5U"]
    assert position.isin == "IE00BJ0KDQ92"
    assert position.instrument_type == "etf"
    assert position.value_eur == Decimal("273.36")
    assert position.quantity == Decimal("2")


def test_overlapping_isin_is_consolidated_once_with_exact_provenance() -> None:
    generated_at = datetime(2026, 7, 31, tzinfo=timezone.utc)
    dkb = _dkb_snapshot()
    aggregation = aggregate_sources(
        (
            PortfolioSourceSnapshot(
                source_id="comdirect",
                provider="local_rest_json",
                label="Comdirect REST",
                generated_at=generated_at,
                positions={
                    "A1XB5U": _position(
                        "A1XB5U", "IE00BJ0KDQ92", "135.275", name="MSCI World"
                    )
                },
            ),
            PortfolioSourceSnapshot(
                source_id="dkb_1",
                provider=DKB_PROVIDER,
                label="DKB Gateway",
                generated_at=generated_at,
                positions=dkb,
            ),
        )
    )

    assert tuple(aggregation.positions) == ("A1XB5U",)
    position = aggregation.positions["A1XB5U"]
    assert position.value_eur == Decimal("408.635")
    assert position.source_ids == ("comdirect", "dkb_1")
    assert dict(position.source_values_eur) == {
        "comdirect": Decimal("135.275"),
        "dkb_1": Decimal("273.36"),
    }
    assert aggregation.conflicts == ()
    assert aggregation.sources[1].to_dict()["contribution_eur"] == "273.36"


def test_cross_source_wkn_identity_collision_fails_closed() -> None:
    timestamp = datetime(2026, 7, 31, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="multiple WKN values"):
        aggregate_sources(
            (
                PortfolioSourceSnapshot(
                    "primary",
                    "local_rest_json",
                    "Primary",
                    timestamp,
                    {"A1XB5U": _position("A1XB5U", "IE00BJ0KDQ92", "100")},
                ),
                PortfolioSourceSnapshot(
                    "secondary",
                    DKB_PROVIDER,
                    "Secondary",
                    timestamp,
                    {"OTHER1": _position("OTHER1", "IE00BJ0KDQ92", "50")},
                ),
            )
        )


def test_supplied_overlap_changes_the_next_350_euro_distribution() -> None:
    generated_at = datetime(2026, 8, 17, tzinfo=timezone.utc)
    aggregation = aggregate_sources(
        (
            PortfolioSourceSnapshot(
                "comdirect",
                "local_rest_json",
                "Comdirect REST",
                generated_at,
                _comdirect_snapshot(),
            ),
            PortfolioSourceSnapshot(
                "dkb_1",
                DKB_PROVIDER,
                "DKB CSV 1",
                generated_at,
                _dkb_snapshot(),
            ),
        )
    )
    payload = calculate_portfolio_payload_from_positions(
        aggregation.positions,
        ROOT / "examples" / "current-plan",
        evaluated_at=generated_at,
        source_provider=PROVIDER_MULTI_SOURCE,
        source_label="2 sources",
        source_metadata=_source_metadata(aggregation),
    )

    recommendations = {
        item["isin"]: item for item in payload["recommendations"]
    }
    assert payload["summary"]["current_portfolio_value_eur"] == Decimal("14234.109")
    assert payload["summary"]["source_count"] == 2
    assert recommendations["IE00BJ0KDQ92"]["current_value_eur"] == Decimal("408.635")
    assert recommendations["IE00BJ0KDQ92"]["proposed_buy_eur"] == Decimal("290")
    assert recommendations["IE00BLPK3577"]["proposed_buy_eur"] == Decimal("20")
    assert recommendations["IE00BYZK4552"]["proposed_buy_eur"] == Decimal("40")
    assert sum(
        item["proposed_buy_eur"] for item in payload["recommendations"]
    ) == Decimal("350")


def test_public_dashboard_uses_positive_colours_and_short_localised_schedule() -> None:
    dashboard = yaml.safe_load((ROOT / "dashboard" / "runtime-health.yaml").read_text())
    encoded = str(dashboard)
    assert "'state': 'ok'" in encoded and "'color': 'green'" in encoded
    assert "'state': 'live'" in encoded and "'color': 'green'" in encoded

    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    schedule_cards = [
        item["card"]
        for item in walk(dashboard)
        if item.get("type") == "conditional"
        and isinstance(item.get("card"), dict)
        and item["card"].get("entity")
        == "sensor.portfolio_architect_gateway_next_refresh"
    ]
    assert len(schedule_cards) == 3
    assert all(
        item["time_format"] == {"type": "datetime", "style": "short"}
        for item in schedule_cards
    )



def test_review_schedule_uses_latest_evaluation_contract() -> None:
    source = (COMPONENT / "coordinator.py").read_text()
    start = source.index("    def plan_review_schedule")
    end = source.index("    def is_plan_review_due", start)
    body = source[start:end]
    assert "timestamp = self.data_timestamp" in body
    assert "oldest_source_generated_at" not in body
