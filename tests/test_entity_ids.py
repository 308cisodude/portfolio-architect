"""Regression tests for allocation entity-ID planning."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "portfolio_architect"

package = types.ModuleType("portfolio_architect")
package.__path__ = [str(PACKAGE_ROOT)]
sys.modules["portfolio_architect"] = package
const = types.ModuleType("portfolio_architect.const")
const.DOMAIN = "portfolio_architect"
sys.modules["portfolio_architect.const"] = const

spec = importlib.util.spec_from_file_location(
    "portfolio_architect.entity_ids", PACKAGE_ROOT / "entity_ids.py"
)
assert spec and spec.loader
entity_ids = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = entity_ids
spec.loader.exec_module(entity_ids)


@dataclass
class FakeEntry:
    entity_id: str
    unique_id: str


def test_actual_v040_ids_are_planned_without_reconstructed_metadata() -> None:
    entries = [
        FakeEntry(
            entity_id=(
                "sensor.portfolio_architect_portfolio_architect_"
                "world_current_allocation"
            ),
            unique_id="unexpected-but-preserved-unique-id",
        ),
        FakeEntry(
            entity_id=(
                "sensor.portfolio_architect_portfolio_architect_"
                "ai_big_data_target_allocation"
            ),
            unique_id="another-existing-unique-id",
        ),
    ]

    plans = entity_ids.plan_legacy_entity_id_migrations(entries)

    assert [(plan.old_entity_id, plan.new_entity_id) for plan in plans] == [
        (
            "sensor.portfolio_architect_portfolio_architect_world_current_allocation",
            "sensor.portfolio_architect_world_current_allocation",
        ),
        (
            "sensor.portfolio_architect_portfolio_architect_ai_big_data_target_allocation",
            "sensor.portfolio_architect_ai_big_data_target_allocation",
        ),
    ]
    assert plans[0].unique_id == "unexpected-but-preserved-unique-id"


def test_clean_and_user_renamed_ids_are_not_migrated() -> None:
    entries = [
        FakeEntry(
            entity_id="sensor.portfolio_architect_world_current_allocation",
            unique_id="clean",
        ),
        FakeEntry(
            entity_id="sensor.my_custom_world_allocation",
            unique_id="custom",
        ),
    ]

    assert entity_ids.plan_legacy_entity_id_migrations(entries) == []


def test_similar_but_unrelated_ids_are_not_migrated() -> None:
    entries = [
        FakeEntry(
            entity_id=(
                "sensor.portfolio_architect_portfolio_architect_"
                "world_current_temperature"
            ),
            unique_id="wrong-suffix",
        ),
        FakeEntry(
            entity_id="binary_sensor.portfolio_architect_portfolio_architect_world_current_allocation",
            unique_id="wrong-domain",
        ),
        FakeEntry(
            entity_id="sensor.portfolio_architect_portfolio_architect__current_allocation",
            unique_id="missing-fund",
        ),
    ]

    assert entity_ids.plan_legacy_entity_id_migrations(entries) == []


def test_helper_generates_clean_ids() -> None:
    assert entity_ids.desired_entity_id("world_small_cap", "target") == (
        "sensor.portfolio_architect_world_small_cap_target_allocation"
    )
    assert entity_ids.legacy_entity_id("world_small_cap", "target") == (
        "sensor.portfolio_architect_portfolio_architect_"
        "world_small_cap_target_allocation"
    )
