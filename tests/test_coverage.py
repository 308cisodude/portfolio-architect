"""Tests for engine target-architecture coverage."""

from decimal import Decimal
from pathlib import Path
import sys

ENGINE_ROOT = Path(__file__).parents[1] / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(ENGINE_ROOT))

from engine.coverage import calculate_target_coverage  # noqa: E402
from engine.models import Recommendation  # noqa: E402


def recommendation(fund_id: str, target: str, value: str) -> Recommendation:
    return Recommendation(
        fund_id=fund_id,
        wkn=f"WKN{fund_id[:3]}",
        isin=f"ISIN{fund_id}",
        name=fund_id,
        target_pct=Decimal(target),
        current_value_eur=Decimal(value),
        target_value_eur=Decimal("0"),
        deviation_eur=Decimal("0"),
        current_pct=Decimal("0"),
        deviation_pp=Decimal("0"),
        allocation_status="underweight",
        buy_enabled=True,
        proposed_buy_eur=Decimal("0"),
    )


def test_zero_target_legacy_position_is_not_counted() -> None:
    coverage = calculate_target_coverage(
        [
            recommendation("world", "60", "100"),
            recommendation("robotics", "40", "0"),
            recommendation("legacy", "0", "500"),
        ]
    )
    assert coverage.total == 2
    assert coverage.held == 1
    assert coverage.missing == 1
    assert coverage.coverage_pct == Decimal("50")
    assert coverage.missing_fund_ids == ("robotics",)


def test_complete_architecture_reports_100_percent() -> None:
    coverage = calculate_target_coverage(
        [
            recommendation("world", "60", "1"),
            recommendation("robotics", "40", "0.01"),
        ]
    )
    assert coverage.coverage_pct == Decimal("100")
    assert coverage.missing == 0
    assert coverage.to_dict()["target_architecture_complete"] is True
