"""v1.2 native plan configuration and recurring schedule tests."""

from datetime import date
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
import types

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def _load_schedule():
    path = COMPONENT / "schedule.py"
    spec = importlib.util.spec_from_file_location("portfolio_architect_schedule_v12", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_engine_modules():
    package = types.ModuleType("pa_v12")
    package.__path__ = [str(COMPONENT)]
    sys.modules["pa_v12"] = package
    engine_path = COMPONENT / "engine" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "pa_v12.engine", engine_path, submodule_search_locations=[str(engine_path.parent)]
    )
    engine = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = engine
    assert spec.loader is not None
    spec.loader.exec_module(engine)
    model_path = COMPONENT / "model.py"
    model_spec = importlib.util.spec_from_file_location("pa_v12.model", model_path)
    model = importlib.util.module_from_spec(model_spec)
    sys.modules[model_spec.name] = model
    assert model_spec.loader is not None
    model_spec.loader.exec_module(model)
    return engine, model


def test_monthly_multiple_execution_schedule_reviews_next_period():
    module = _load_schedule()
    config = module.validate_schedule_config("monthly", [1, 7, 15])
    schedule = module.calculate_plan_review_schedule(date(2026, 7, 29), config, 2)
    assert schedule.planned_execution_on == date(2026, 8, 1)
    assert schedule.review_for_execution_on == date(2026, 9, 1)
    assert schedule.next_review_on == date(2026, 8, 30)
    assert schedule.executions_per_period == 3


def test_weekly_quarterly_and_yearly_schedules():
    module = _load_schedule()
    weekly = module.validate_schedule_config("weekly", [1, 5])
    assert module.calculate_plan_review_schedule(
        date(2026, 7, 29), weekly, 2
    ).review_for_execution_on == date(2026, 8, 3)

    quarterly = module.validate_schedule_config(
        "quarterly", [7], execution_month_offset=2
    )
    assert module.calculate_plan_review_schedule(
        date(2026, 7, 29), quarterly, 2
    ).review_for_execution_on == date(2026, 11, 7)

    yearly = module.validate_schedule_config(
        "yearly", [15], execution_month=3
    )
    assert module.calculate_plan_review_schedule(
        date(2026, 7, 29), yearly, 2
    ).planned_execution_on == date(2027, 3, 15)


@pytest.mark.parametrize(
    "frequency,days,month,offset",
    [
        ("weekly", [0], None, None),
        ("monthly", [29], None, None),
        ("quarterly", [1], None, 4),
        ("yearly", [1], 13, None),
        ("daily", [1], None, None),
    ],
)
def test_invalid_schedules_fail_closed(frequency, days, month, offset):
    module = _load_schedule()
    with pytest.raises(ValueError):
        module.validate_schedule_config(
            frequency,
            days,
            execution_month=month,
            execution_month_offset=offset,
        )


def test_ui_budget_is_split_per_period_and_schema_8_is_validated():
    engine, model = _load_engine_modules()
    csv_path = ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv"
    config_dir = ROOT / "examples" / "current-plan"
    portfolio = yaml.safe_load((config_dir / "portfolio.yaml").read_text())
    override = {
        "enabled": True,
        "name": "Retirement plan",
        "budget_amount_eur": 700,
        "budget_basis": "per_period",
        "frequency": "monthly",
        "executions_per_period": 2,
        "instruments": portfolio["portfolio"]["allocation"],
    }
    payload = engine.calculate_portfolio_payload(
        csv_path, config_dir, plan_override=override
    )
    summary = payload["summary"]
    assert payload["schema_version"] == 8
    assert summary["payload_schema_version"] == 8
    assert summary["plan_budget_amount_eur"] == Decimal("700.00")
    assert summary["contribution_per_execution_eur"] == Decimal("350.00")
    assert summary["scheduled_executions_per_period"] == 2
    assert summary["plan_configuration_source"] == "ui"

    parsed = model.parse_portfolio_data(
        payload["recommendations"],
        summary,
        payload["policy_findings"],
        holdings=payload["holdings"],
    )
    assert parsed.monthly_plan.budget_amount_eur == 700
    assert parsed.monthly_plan.contribution_per_execution_eur == 350
    assert parsed.monthly_plan.frequency == "monthly"


def test_plan_override_rejects_non_100_percent_targets():
    engine, _model = _load_engine_modules()
    plan_module = sys.modules["pa_v12.engine.plan"]
    with pytest.raises(ValueError, match="sum to 100"):
        plan_module.apply_plan_override(
            {
                "portfolio": {
                    "name": "Base",
                    "monthly_contribution": 100,
                    "allocation": [],
                }
            },
            {
                "enabled": True,
                "name": "Bad plan",
                "budget_amount_eur": 100,
                "budget_basis": "per_execution",
                "frequency": "monthly",
                "executions_per_period": 1,
                "instruments": [
                    {
                        "id": "one",
                        "wkn": "A1XB5U",
                        "isin": "IE00BJ0KDQ92",
                        "name": "One",
                        "target_pct": 90,
                        "buy_enabled": True,
                    }
                ],
            },
        )


def test_plan_override_can_be_reset_through_native_options_flow():
    source = (COMPONENT / "config_flow.py").read_text()
    assert 'async def async_step_reset_plan' in source
    assert 'menu_options.append("reset_plan")' in source
    assert 'options.pop(key, None)' in source
    assert 'CONF_PLAN_OVERRIDE_ENABLED' in source


def test_plan_configuration_keeps_payload_schema_8_stable():
    calculator = (COMPONENT / "engine" / "calculator.py").read_text()
    model = (COMPONENT / "model.py").read_text()
    assert '"schema_version": 8' in calculator
    assert '"payload_schema_version": 8' in calculator
    assert 'MAX_SUPPORTED_PAYLOAD_SCHEMA = 8' in model
