from datetime import date
import importlib.util
from pathlib import Path
import sys

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "portfolio_architect"
    / "schedule.py"
)
spec = importlib.util.spec_from_file_location("portfolio_architect_schedule", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)
calculate = module.calculate_plan_review_schedule


def test_first_of_month_cycle_after_late_month_evaluation():
    schedule = calculate(date(2026, 7, 29), 1, 2)
    assert schedule.planned_execution_on == date(2026, 8, 1)
    assert schedule.review_for_execution_on == date(2026, 9, 1)
    assert schedule.next_review_on == date(2026, 8, 30)
    assert not schedule.is_due(date(2026, 8, 29))
    assert schedule.is_due(date(2026, 8, 30))


def test_seventh_of_month_cycle():
    schedule = calculate(date(2026, 7, 29), 7, 2)
    assert schedule.planned_execution_on == date(2026, 8, 7)
    assert schedule.review_for_execution_on == date(2026, 9, 7)
    assert schedule.next_review_on == date(2026, 9, 5)


def test_evaluation_on_execution_day_targets_next_month():
    schedule = calculate(date(2026, 8, 7), 7, 3)
    assert schedule.planned_execution_on == date(2026, 9, 7)
    assert schedule.next_review_on == date(2026, 10, 4)


@pytest.mark.parametrize("day", [0, 29, True])
def test_invalid_execution_day_is_rejected(day):
    with pytest.raises(ValueError):
        calculate(date(2026, 7, 29), day, 2)


@pytest.mark.parametrize("lead", [0, 8, True])
def test_invalid_review_lead_is_rejected(lead):
    with pytest.raises(ValueError):
        calculate(date(2026, 7, 29), 1, lead)
