"""v1.18.2 Home Assistant monetary sensor metadata contracts."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
SENSOR = ROOT / "custom_components" / "portfolio_architect" / "sensor.py"


def _class_assignments(node: ast.ClassDef) -> dict[str, ast.expr]:
    assignments: dict[str, ast.expr] = {}
    for child in node.body:
        if not isinstance(child, ast.Assign):
            continue
        for target in child.targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = child.value
    return assignments


def _is_attribute(value: ast.expr | None, owner: str, attribute: str) -> bool:
    return (
        isinstance(value, ast.Attribute)
        and value.attr == attribute
        and isinstance(value.value, ast.Name)
        and value.value.id == owner
    )


def test_monetary_sensors_have_no_state_class() -> None:
    tree = ast.parse(SENSOR.read_text(encoding="utf-8"))
    classes = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    assignments = {name: _class_assignments(node) for name, node in classes.items()}
    parents = {
        name: {
            base.id for base in node.bases if isinstance(base, ast.Name)
        }
        for name, node in classes.items()
    }

    monetary = {
        name
        for name, values in assignments.items()
        if _is_attribute(
            values.get("_attr_device_class"), "SensorDeviceClass", "MONETARY"
        )
    }
    changed = True
    while changed:
        changed = False
        for name, bases in parents.items():
            if name not in monetary and bases & monetary:
                monetary.add(name)
                changed = True

    expected = {
        "PortfolioValueSensor",
        "PortfolioCurrentPlanValueSensor",
        "PortfolioOutsideScopeValueSensor",
        "_PortfolioMonthlyMoneySensor",
        "PortfolioPlanBudgetSensor",
        "PortfolioMonthlyContributionSensor",
        "PortfolioRecommendedTotalSensor",
        "PortfolioUnallocatedContributionSensor",
        "PortfolioAvailableInvestmentReserveSensor",
        "PortfolioRemainingInvestmentReserveSensor",
        "PortfolioDeferredContributionSensor",
        "PortfolioEstimatedTransactionFeesSensor",
        "PortfolioEstimatedCashOutlaySensor",
        "PortfolioAdditionalInvestmentCashRequiredSensor",
        "PortfolioAllocationValueGapSensor",
        "PortfolioProposedBuySensor",
        "PortfolioHoldingValueSensor",
    }
    assert expected <= monetary

    offenders = sorted(
        name
        for name in monetary
        if _is_attribute(
            assignments[name].get("_attr_state_class"),
            "SensorStateClass",
            "MEASUREMENT",
        )
    )
    assert offenders == []

    # The current monetary entities are absolute/advisory values, not accumulating
    # totals, so they intentionally publish no state class. A future monetary total
    # could use TOTAL without weakening the MEASUREMENT guard above.
    current_with_state_class = sorted(
        name for name in expected if "_attr_state_class" in assignments[name]
    )
    assert current_with_state_class == []


def test_non_monetary_measurement_metadata_is_preserved() -> None:
    source = SENSOR.read_text(encoding="utf-8")
    assert "class PortfolioTargetCoverageSensor" in source
    assert "class PortfolioGatewayLastRefreshDurationSensor" in source
    assert "class PortfolioHoldingQuantitySensor" in source
    assert source.count("SensorStateClass.MEASUREMENT") >= 10
