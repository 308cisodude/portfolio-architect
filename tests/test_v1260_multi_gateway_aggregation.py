"""v1.26 multi-Gateway aggregation and distinct-provider contracts."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

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

NOW = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc)
CONFIG = ROOT / "examples" / "current-plan"


def _position(wkn: str, isin: str, value: str, name: str) -> Position:
    return Position(
        wkn=wkn,
        isin=isin,
        name=name,
        instrument_type="etf",
        source_type="ETF",
        value_eur=Decimal(value),
    )


def _aggregation_metadata(aggregation) -> dict[str, object]:
    provider_ids = list(dict.fromkeys(item.provider for item in aggregation.sources))
    return {
        "source_count": len(aggregation.sources),
        "source_providers": [item.provider for item in aggregation.sources],
        "provider_count": len(provider_ids),
        "provider_ids": provider_ids,
        "source_summaries": [item.to_dict() for item in aggregation.sources],
        "source_conflict_count": len(aggregation.conflicts),
        "source_conflicts": [item.to_dict() for item in aggregation.conflicts],
        "oldest_source_generated_at": aggregation.oldest_generated_at.isoformat(),
        "newest_source_generated_at": aggregation.newest_generated_at.isoformat(),
    }


def test_trade_republic_gateway_snapshot_completes_target_architecture() -> None:
    comdirect_rows = (
        ("A1XB5U", "IE00BJ0KDQ92", "4500", "MSCI World"),
        ("A12GVR", "IE00BTJRMP35", "1500", "Emerging Markets"),
        ("DBX0WG", "IE000F354Q61", "1500", "World Small Cap"),
        ("A2ANH2", "IE00BYZK4776", "800", "Healthcare"),
        ("A2N6LC", "IE00BGV5VN51", "700", "AI & Big Data"),
        ("A2QGAH", "IE00BLPK3577", "500", "Cybersecurity"),
    )
    comdirect = {
        wkn: _position(wkn, isin, value, name)
        for wkn, isin, value, name in comdirect_rows
    }
    dkb = {
        "A1XB5U": _position("A1XB5U", "IE00BJ0KDQ92", "250", "MSCI World")
    }
    trade_republic = {
        "IE00BYZK4552": _position(
            "",
            "IE00BYZK4552",
            "500",
            "Synthetic Automation & Robotics accumulating holding",
        )
    }
    aggregation = aggregate_sources(
        (
            PortfolioSourceSnapshot("comdirect", "comdirect", "Comdirect", NOW, comdirect),
            PortfolioSourceSnapshot("trade_republic", "trade_republic", "Trade Republic", NOW, trade_republic),
            PortfolioSourceSnapshot("dkb_1", "dkb", "DKB CSV", NOW, dkb),
        )
    )
    payload = calculate_portfolio_payload_from_positions(
        aggregation.positions,
        CONFIG,
        evaluated_at=NOW,
        source_provider=PROVIDER_MULTI_SOURCE,
        source_label="3 sources",
        source_metadata=_aggregation_metadata(aggregation),
    )

    summary = payload["summary"]
    assert summary["target_positions_held"] == 7
    assert summary["target_positions_missing"] == 0
    assert summary["target_architecture_complete"] is True
    assert summary["source_count"] == 3
    assert summary["provider_count"] == 3
    assert summary["provider_ids"] == ["comdirect", "trade_republic", "dkb"]

    recommendations = {item["fund_id"]: item for item in payload["recommendations"]}
    robotics = recommendations["robotics"]
    assert robotics["current_value_eur"] == Decimal("500")
    assert robotics["source_ids"] == ["trade_republic"]
    assert robotics["source_values_eur"] == {"trade_republic": Decimal("500")}
    world = recommendations["world"]
    assert world["source_ids"] == ["comdirect", "dkb_1"]
    assert world["source_values_eur"] == {
        "comdirect": Decimal("4500"),
        "dkb_1": Decimal("250"),
    }


def test_provider_count_is_distinct_from_source_instance_count() -> None:
    snapshots = (
        PortfolioSourceSnapshot(
            "comdirect", "comdirect", "Comdirect", NOW,
            {"A1XB5U": _position("A1XB5U", "IE00BJ0KDQ92", "100", "World")},
        ),
        PortfolioSourceSnapshot(
            "dkb_1", "dkb", "DKB 1", NOW,
            {"A12GVR": _position("A12GVR", "IE00BTJRMP35", "50", "EM")},
        ),
        PortfolioSourceSnapshot(
            "dkb_2", "dkb", "DKB 2", NOW,
            {"DBX0WG": _position("DBX0WG", "IE000F354Q61", "40", "Small Cap")},
        ),
        PortfolioSourceSnapshot(
            "trade_republic", "trade_republic", "Trade Republic", NOW,
            {"IE00BYWZ0333": _position("", "IE00BYWZ0333", "30", "Robotics")},
        ),
    )
    metadata = _aggregation_metadata(aggregate_sources(snapshots))
    assert metadata["source_count"] == 4
    assert metadata["provider_count"] == 3
    assert metadata["provider_ids"] == ["comdirect", "dkb", "trade_republic"]


def test_additional_gateway_configuration_is_private_and_fail_closed_by_contract() -> None:
    rest_client = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")

    assert "class SupplementalRestSourceConfig" in rest_client
    assert '"rest_api_token": self.api_token' in rest_client
    public_method = rest_client.split("def as_public_dict", 2)[2].split("@dataclass", 1)[0]
    assert "api_token" not in public_method
    assert "_supplemental_rest_identity_tokens(self.supplemental_rest_sources)" in coordinator
    assert "Multi-Gateway aggregation requires primary Gateway health schema 6" in coordinator
    assert "Supplemental portfolio source failed" in coordinator
    assert "self._use_home_assistant_last_known_good" in coordinator
    assert "health.health_schema_version < 6" in flow
    assert "primary_health.health_schema_version < 6" in flow
    assert 'primary_health.status != "ok"' in flow
    assert "not primary_health.snapshot_available" in flow
    assert "health.snapshot_sha256 != result.snapshot_sha256" in flow
    assert "health.snapshot_generated_at != snapshot.generated_at" in flow


def test_reference_dashboard_surfaces_distinct_provider_summary() -> None:
    bilingual = yaml.safe_load((ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text())
    for view, attribute in zip(
        bilingual["views"],
        ("provider_summary", "provider_summary_de"),
        strict=True,
    ):
        cards = [
            card
            for section in view["sections"]
            for card in section.get("cards", [])
            if isinstance(card, dict)
            and card.get("entity") == "sensor.portfolio_architect_source_provider"
        ]
        assert len(cards) == 1
        assert cards[0]["state_content"] == attribute


def test_supplemental_gateway_diagnostics_are_bounded_and_token_free() -> None:
    diagnostics = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
    block = diagnostics.split('"supplemental_gateway_health":', 1)[1].split('"home_assistant_last_known_good":', 1)[0]
    assert '"provider_id"' in block
    assert '"snapshot_available"' in block
    assert '"snapshot_generated_at"' in block
    assert "api_token" not in block
    assert "endpoint_url" not in block


def test_trade_republic_is_auto_start_but_dkb_remains_manual_only() -> None:
    tr = yaml.safe_load((ROOT / "home_assistant_app" / "portfolio_architect_gateway_trade_republic" / "config.yaml").read_text())
    dkb = yaml.safe_load((ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb" / "config.yaml").read_text())
    assert tr["boot"] == "auto"
    assert dkb["boot"] == "manual_only"
    verify = (ROOT / "tools" / "verify_release.py").read_text(encoding="utf-8")
    assert '"trade_republic",\n            "auto"' in verify
    assert '"dkb",\n            "manual_only"' in verify
