"""v1.13.1 aggregate allocation and drift contract tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parents[1]
MODULE_PATH = (
    ROOT
    / "custom_components"
    / "portfolio_architect"
    / "allocation_overview.py"
)
SPEC = importlib.util.spec_from_file_location("allocation_overview", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _position(
    fund_id: str,
    *,
    name: str,
    status: str,
    drift: float,
    current_pct: float,
    target_pct: float,
    deviation_eur: float,
    current_value: float = 1000.0,
    target_value: float = 1000.0,
    proposed_buy: float = 0.0,
    buy_enabled: bool = True,
):
    return SimpleNamespace(
        fund_id=fund_id,
        name=name,
        wkn=f"WKN{fund_id[:3].upper()}",
        isin=f"DE000{fund_id[:6].upper():0<6}0",
        allocation_status=status,
        deviation_pp=drift,
        current_pct=current_pct,
        target_pct=target_pct,
        deviation_eur=deviation_eur,
        current_value_eur=current_value,
        target_value_eur=target_value,
        proposed_buy_eur=proposed_buy,
        buy_enabled=buy_enabled,
    )


def _data(*positions):
    counts = {
        status: sum(position.allocation_status == status for position in positions)
        for status in ("underweight", "on_target", "overweight")
    }
    return SimpleNamespace(
        positions={position.fund_id: position for position in positions},
        allocation=SimpleNamespace(
            corridor_pp=1.0,
            portfolio_value_eur=12345.675,
            current_plan_value_eur=10000.005,
            underweight=counts["underweight"],
            on_target=counts["on_target"],
            overweight=counts["overweight"],
        ),
    )


def test_groups_use_documented_deterministic_sorting() -> None:
    data = _data(
        _position("u_near", name="Zulu", status="underweight", drift=-1.2, current_pct=8.8, target_pct=10, deviation_eur=-120),
        _position("u_far", name="Alpha", status="underweight", drift=-4.0, current_pct=6, target_pct=10, deviation_eur=-400),
        _position("t_far", name="Beta", status="on_target", drift=0.8, current_pct=10.8, target_pct=10, deviation_eur=80),
        _position("t_near", name="Gamma", status="on_target", drift=-0.1, current_pct=9.9, target_pct=10, deviation_eur=-10),
        _position("o_near", name="Delta", status="overweight", drift=1.2, current_pct=11.2, target_pct=10, deviation_eur=120),
        _position("o_far", name="Epsilon", status="overweight", drift=3.5, current_pct=13.5, target_pct=10, deviation_eur=350),
    )

    overview = MODULE.build_allocation_overview(data)

    assert [row["fund_id"] for row in overview["underweight"]] == ["u_far", "u_near"]
    assert [row["fund_id"] for row in overview["on_target"]] == ["t_near", "t_far"]
    assert [row["fund_id"] for row in overview["overweight"]] == ["o_far", "o_near"]


def test_rows_round_half_up_and_expose_gap_or_excess() -> None:
    data = _data(
        _position(
            "under",
            name="Under",
            status="underweight",
            drift=-1.005,
            current_pct=8.995,
            target_pct=10.0,
            deviation_eur=-100.005,
            current_value=899.995,
            target_value=1000.005,
            proposed_buy=50.005,
        ),
        _position(
            "over",
            name="Over",
            status="overweight",
            drift=1.005,
            current_pct=11.005,
            target_pct=10.0,
            deviation_eur=100.005,
        ),
    )

    overview = MODULE.build_allocation_overview(data)
    under = overview["underweight"][0]
    over = overview["overweight"][0]

    assert overview["portfolio_value_eur"] == 12345.68
    assert overview["current_plan_value_eur"] == 10000.01
    assert under["drift_pp"] == -1.01
    assert under["current_pct"] == 9.0
    assert under["current_value_eur"] == 900.0
    assert under["value_gap_eur"] == 100.01
    assert under["excess_value_eur"] == 0.0
    assert under["proposed_buy_eur"] == 50.01
    assert over["value_gap_eur"] == 0.0
    assert over["excess_value_eur"] == 100.01


def test_zero_value_position_remains_visible_and_bounded() -> None:
    data = _data(
        _position(
            "zero",
            name="Zero holding",
            status="underweight",
            drift=-5.0,
            current_pct=0.0,
            target_pct=5.0,
            deviation_eur=-500.0,
            current_value=0.0,
            target_value=500.0,
            proposed_buy=50.0,
        )
    )

    row = MODULE.build_allocation_overview(data)["underweight"][0]

    assert row["current_value_eur"] == 0.0
    assert row["current_pct"] == 0.0
    assert row["corridor_lower_pct"] == 4.0
    assert row["corridor_upper_pct"] == 6.0



def test_degraded_overview_omits_actionable_purchase_fields() -> None:
    data = _data(
        _position(
            "under",
            name="Under",
            status="underweight",
            drift=-2.0,
            current_pct=8.0,
            target_pct=10.0,
            deviation_eur=-200.0,
            proposed_buy=125.0,
            buy_enabled=True,
        )
    )

    row = MODULE.build_allocation_overview(
        data, include_actionable=False
    )["underweight"][0]

    assert "proposed_buy_eur" not in row
    assert "buy_enabled" not in row
    assert row["current_pct"] == 8.0
    assert row["target_pct"] == 10.0
    assert row["value_gap_eur"] == 200.0

def test_aggregate_state_is_binary_without_hysteresis() -> None:
    on_target = _data(
        _position("target", name="Target", status="on_target", drift=0.5, current_pct=10.5, target_pct=10, deviation_eur=50)
    )
    drifted = _data(
        _position("drift", name="Drift", status="underweight", drift=-1.5, current_pct=8.5, target_pct=10, deviation_eur=-150)
    )

    assert MODULE.allocation_overview_state(on_target) == "on_target"
    assert MODULE.allocation_overview_state(drifted) == "drift_detected"


def test_sensor_handles_unavailable_or_missing_data_before_building_attributes() -> None:
    source = (ROOT / "custom_components" / "portfolio_architect" / "sensor.py").read_text()
    assert "PortfolioAllocationOverviewSensor(coordinator, entry)" in source
    assert source.count("if not self.available or self.coordinator.data is None:") >= 2
    assert "include_actionable=self.coordinator.plan_actionable" in source
