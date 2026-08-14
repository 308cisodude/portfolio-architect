"""v1.26.1 ISIN-first identity hotfix and fail-closed collision contracts."""

from datetime import datetime, timezone
import importlib.util
from decimal import Decimal
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.aggregation import (  # noqa: E402
    PROVIDER_MULTI_SOURCE,
    PortfolioSourceSnapshot,
    aggregate_sources,
)
from engine.calculator import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.identity import (  # noqa: E402
    build_position_identity_index,
    match_position_for_target,
)
from engine.models import Position  # noqa: E402
from engine.rest import parse_rest_snapshot  # noqa: E402

_TR_PACKAGE_NAME = "portfolio_architect_gateway_tr_v1261_test"
_TR_PACKAGE_DIR = (
    ROOT
    / "home_assistant_app"
    / "portfolio_architect_gateway_trade_republic"
    / "src"
    / "portfolio_architect_gateway"
)
_tr_package_spec = importlib.util.spec_from_file_location(
    _TR_PACKAGE_NAME,
    _TR_PACKAGE_DIR / "__init__.py",
    submodule_search_locations=[str(_TR_PACKAGE_DIR)],
)
assert _tr_package_spec is not None and _tr_package_spec.loader is not None
_tr_package = importlib.util.module_from_spec(_tr_package_spec)
sys.modules[_TR_PACKAGE_NAME] = _tr_package
_tr_package_spec.loader.exec_module(_tr_package)

from portfolio_architect_gateway_tr_v1261_test.trade_republic_statement import (  # type: ignore[import-not-found]  # noqa: E402
    parse_statement_text,
)

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
CONFIG = ROOT / "examples" / "current-plan"


def _position(wkn: str, isin: str, value: str, name: str = "Instrument") -> Position:
    return Position(
        wkn=wkn,
        isin=isin,
        name=name,
        instrument_type="etf",
        source_type="ETF",
        value_eur=Decimal(value),
    )


def _metadata(aggregation) -> dict[str, object]:
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


def test_rest_parser_does_not_mislabel_isin_identifier_as_wkn() -> None:
    snapshot = parse_rest_snapshot(
        {
            "schema_version": 1,
            "currency": "EUR",
            "generated_at": "2026-08-14T11:00:00Z",
            "positions": [
                {
                    "identifier": "IE00BYWZ0333",
                    "isin": "IE00BYWZ0333",
                    "name": "Synthetic Automation & Robotics holding",
                    "instrument_type": "ETF",
                    "market_value_eur": "500",
                    "quantity": "4.25",
                }
            ],
        },
        now=NOW,
    )

    position = snapshot.positions["IE00BYWZ0333"]
    assert position.isin == "IE00BYWZ0333"
    assert position.wkn == ""


def _synthetic_robotics_statement() -> str:
    return "\n".join(
        [
            "TRADE REPUBLIC BANK GMBH           SYNTHETIC TEST DOCUMENT",
            "SYNTHETIC PERSON                                      DATUM 14.08.2026",
            "DEPOT SYNTHETIC",
            "                                      DEPOTAUSZUG",
            "                                       zum 14.08.2026",
            "POSITIONEN",
            "STK. / NOMINALE   WERTPAPIERBEZEICHNUNG                          KURS PRO STUECK      KURSWERT IN EUR",
            "4,250000 Stk.     Synthetic Automation & Robotics holding         117,65                 500,00",
            "                  ISIN: IE00BYWZ0333",
            "                  ANZAHL POSITIONEN: 1                                             500,00 EUR",
            "Erstellt am 2026-08-14 11:00:00 Europe/Berlin (UTC+02:00) Seite 1 von 1",
        ]
    )


def test_real_trade_republic_rest_identity_shape_completes_seven_of_seven() -> None:
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
    dkb = {"A1XB5U": _position("A1XB5U", "IE00BJ0KDQ92", "250", "MSCI World")}
    provider_snapshot = parse_statement_text(_synthetic_robotics_statement(), now=NOW)
    assert provider_snapshot.positions[0].identifier == "IE00BYWZ0333"
    assert provider_snapshot.positions[0].isin == "IE00BYWZ0333"
    trade_republic = parse_rest_snapshot(provider_snapshot.as_dict(), now=NOW)
    assert trade_republic.positions["IE00BYWZ0333"].wkn == ""

    aggregation = aggregate_sources(
        (
            PortfolioSourceSnapshot("comdirect", "comdirect", "Comdirect", NOW, comdirect),
            PortfolioSourceSnapshot(
                "trade_republic",
                "trade_republic",
                "Trade Republic",
                trade_republic.generated_at,
                trade_republic.positions,
            ),
            PortfolioSourceSnapshot("dkb_1", "dkb", "DKB CSV", NOW, dkb),
        )
    )
    payload = calculate_portfolio_payload_from_positions(
        aggregation.positions,
        CONFIG,
        evaluated_at=NOW,
        source_provider=PROVIDER_MULTI_SOURCE,
        source_label="3 sources",
        source_metadata=_metadata(aggregation),
    )

    summary = payload["summary"]
    assert summary["target_positions_held"] == 7
    assert summary["target_positions_missing"] == 0
    assert summary["target_architecture_complete"] is True
    assert summary["source_count"] == 3
    assert summary["provider_count"] == 3

    recommendations = {item["fund_id"]: item for item in payload["recommendations"]}
    robotics = recommendations["robotics"]
    assert robotics["wkn"] == "A2ANH1"
    assert robotics["isin"] == "IE00BYWZ0333"
    assert robotics["current_value_eur"] == Decimal("500")
    assert robotics["source_ids"] == ["trade_republic"]

    holdings = {item["position_id"]: item for item in payload["holdings"]}
    assert holdings["robotics"]["wkn"] == "A2ANH1"
    assert holdings["robotics"]["isin"] == "IE00BYWZ0333"
    assert holdings["robotics"]["strategy_scope"] == "current_plan"


def test_wkn_is_used_only_when_source_isin_is_unavailable() -> None:
    target = {"id": "world", "wkn": "A1XB5U", "isin": "IE00BJ0KDQ92"}
    fallback = _position("A1XB5U", "", "100", "World")
    index = build_position_identity_index((fallback,))
    assert match_position_for_target(target, index) is fallback


def test_wkn_may_not_override_conflicting_isin() -> None:
    target = {"id": "world", "wkn": "A1XB5U", "isin": "IE00BJ0KDQ92"}
    contradictory = _position("A1XB5U", "IE0000000001", "100", "Wrong identity")
    index = build_position_identity_index((contradictory,))
    with pytest.raises(ValueError, match="ISIN mismatch"):
        match_position_for_target(target, index)


def test_same_isin_with_conflicting_wkn_fails_closed() -> None:
    with pytest.raises(ValueError, match="multiple WKN values"):
        aggregate_sources(
            (
                PortfolioSourceSnapshot(
                    "one",
                    "provider_one",
                    "One",
                    NOW,
                    {"A1XB5U": _position("A1XB5U", "IE00BJ0KDQ92", "100")},
                ),
                PortfolioSourceSnapshot(
                    "two",
                    "provider_two",
                    "Two",
                    NOW,
                    {"OTHER1": _position("OTHER1", "IE00BJ0KDQ92", "50")},
                ),
            )
        )


def test_same_wkn_mapping_to_multiple_isins_fails_closed() -> None:
    with pytest.raises(ValueError, match="maps to multiple ISINs"):
        aggregate_sources(
            (
                PortfolioSourceSnapshot(
                    "one",
                    "provider_one",
                    "One",
                    NOW,
                    {"A1XB5U": _position("A1XB5U", "IE00BJ0KDQ92", "100")},
                ),
                PortfolioSourceSnapshot(
                    "two",
                    "provider_two",
                    "Two",
                    NOW,
                    {"A1XB5U": _position("A1XB5U", "IE0000000001", "50")},
                ),
            )
        )
