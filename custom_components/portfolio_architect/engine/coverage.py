"""Target architecture coverage calculations.

The coverage layer is deliberately independent from the buy-allocation algorithm.
It answers whether each positive-weight target building block is held, not whether
its allocation is within the configured corridor.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from .models import Recommendation

D = Decimal


@dataclass(frozen=True, slots=True)
class TargetCoverage:
    """Machine-readable coverage of positive-weight target positions."""

    total: int
    held: int
    missing: int
    coverage_pct: Decimal
    missing_fund_ids: tuple[str, ...]
    missing_names: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the stable public coverage payload contract."""
        return {
            "target_positions_total": self.total,
            "target_positions_held": self.held,
            "target_positions_missing": self.missing,
            "target_position_coverage_pct": self.coverage_pct,
            "target_architecture_complete": self.missing == 0,
            "missing_target_ids": list(self.missing_fund_ids),
            "missing_target_fund_ids": list(self.missing_fund_ids),
            "missing_target_names": list(self.missing_names),
        }


def calculate_target_coverage(
    recommendations: Iterable[Recommendation],
) -> TargetCoverage:
    """Calculate held/missing coverage for all positive target weights."""
    target_positions = tuple(
        item for item in recommendations if item.target_pct > D("0")
    )
    if not target_positions:
        raise ValueError("At least one positive-weight target position is required")

    missing_positions = tuple(
        item for item in target_positions if item.current_value_eur <= D("0")
    )
    total = len(target_positions)
    missing = len(missing_positions)
    held = total - missing
    coverage_pct = D(held) / D(total) * D("100")

    return TargetCoverage(
        total=total,
        held=held,
        missing=missing,
        coverage_pct=coverage_pct,
        missing_fund_ids=tuple(item.fund_id for item in missing_positions),
        missing_names=tuple(item.name for item in missing_positions),
    )
