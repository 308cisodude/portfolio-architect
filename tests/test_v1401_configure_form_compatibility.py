"""Regression coverage for v1.40.1 Home Assistant Configure-form compatibility."""
from __future__ import annotations

import ast
from decimal import Decimal
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
FLOW = COMPONENT / "config_flow.py"

# Home Assistant Core 2026.8.1 NumberSelector.CONFIG_SCHEMA rejects numeric
# steps below 1e-3. Keep this explicit so future selector additions cannot
# silently reintroduce an HTTP-400 options-flow transition.
_HA_NUMBER_SELECTOR_MIN_STEP = Decimal("0.001")


def _tree() -> ast.Module:
    return ast.parse(FLOW.read_text(encoding="utf-8"))


def _literal_keyword(call: ast.Call, name: str):
    for keyword in call.keywords:
        if keyword.arg == name:
            return ast.literal_eval(keyword.value)
    raise AssertionError(f"{ast.unparse(call.func)} is missing {name}")


def test_all_number_selector_steps_respect_home_assistant_floor() -> None:
    """Audit every NumberSelectorConfig used anywhere in Configure."""

    seen = 0
    for node in ast.walk(_tree()):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "NumberSelectorConfig"
        ):
            continue
        step = _literal_keyword(node, "step")
        assert isinstance(step, (int, float)), (
            f"NumberSelectorConfig at line {node.lineno} needs an explicitly audited numeric step"
        )
        assert Decimal(str(step)) >= _HA_NUMBER_SELECTOR_MIN_STEP, (
            f"NumberSelectorConfig at line {node.lineno} uses HA-incompatible step {step}"
        )
        seen += 1

    assert seen >= 10


def test_broker_evidence_dates_use_native_date_selectors_and_local_today_defaults() -> None:
    """Evidence dates must not fall back to unvalidated free-text fields."""

    source = FLOW.read_text(encoding="utf-8")
    assert "DateSelector," in source
    assert "DateSelectorConfig," in source
    assert (
        "vol.Required(CONF_BROKER_PROVIDER_AS_OF): DateSelector(DateSelectorConfig())"
        in source
    )
    assert (
        "vol.Required(CONF_BROKER_TRANSFER_AS_OF): DateSelector(DateSelectorConfig())"
        in source
    )
    assert source.count("dt_util.now().date().isoformat()") >= 2
    assert "date.today().isoformat()" not in source


def test_savings_plan_fee_selector_keeps_finest_supported_precision() -> None:
    source = FLOW.read_text(encoding="utf-8")
    assert (
        'NumberSelectorConfig(min=0, max=25, step=0.001, mode=NumberSelectorMode.BOX, unit_of_measurement="%")'
        in source
    )
    assert "step=0.0001" not in source


def test_options_flow_rendered_steps_are_bilingual_and_menu_targets_exist() -> None:
    """Audit the complete Portfolio Architect Configure menu surface."""

    tree = _tree()
    flow_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PortfolioArchitectOptionsFlow"
    )
    methods = {
        node.name.removeprefix("async_step_")
        for node in flow_class.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("async_step_")
    }
    rendered_steps: set[str] = set()
    literal_menu_targets: set[str] = set()
    for node in ast.walk(flow_class):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in {"async_show_form", "async_show_menu"}:
            for keyword in node.keywords:
                if (
                    keyword.arg == "step_id"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ):
                    rendered_steps.add(keyword.value.value)
        if node.func.attr == "async_show_menu":
            for keyword in node.keywords:
                if keyword.arg != "menu_options":
                    continue
                try:
                    value = ast.literal_eval(keyword.value)
                except (ValueError, TypeError):
                    continue
                if isinstance(value, list):
                    literal_menu_targets.update(item for item in value if isinstance(item, str))

    assert len(rendered_steps) == 32
    assert literal_menu_targets <= methods
    for language in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        translated_steps = set(translations["options"]["step"])
        assert rendered_steps <= translated_steps



def test_all_selector_config_modes_and_types_match_home_assistant_2026_8_1() -> None:
    """Reject misspelled/unsupported selector modes across every Configure form."""

    allowed_modes = {
        "NumberSelectorConfig": {"NumberSelectorMode.BOX", "NumberSelectorMode.SLIDER"},
        "SelectSelectorConfig": {"SelectSelectorMode.LIST", "SelectSelectorMode.DROPDOWN"},
    }
    allowed_text_types = {
        "TextSelectorType.COLOR",
        "TextSelectorType.DATE",
        "TextSelectorType.DATETIME_LOCAL",
        "TextSelectorType.EMAIL",
        "TextSelectorType.MONTH",
        "TextSelectorType.NUMBER",
        "TextSelectorType.PASSWORD",
        "TextSelectorType.SEARCH",
        "TextSelectorType.TEL",
        "TextSelectorType.TEXT",
        "TextSelectorType.TIME",
        "TextSelectorType.URL",
        "TextSelectorType.WEEK",
    }

    for node in ast.walk(_tree()):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        name = node.func.id
        if name == "SelectSelectorConfig":
            assert any(keyword.arg == "options" for keyword in node.keywords), (
                f"SelectSelectorConfig at line {node.lineno} is missing required options"
            )
        if name in allowed_modes:
            for keyword in node.keywords:
                if keyword.arg == "mode":
                    assert ast.unparse(keyword.value) in allowed_modes[name]
        if name == "TextSelectorConfig":
            for keyword in node.keywords:
                if keyword.arg == "type":
                    assert ast.unparse(keyword.value) in allowed_text_types
        if name == "DateSelectorConfig":
            assert not node.args and not node.keywords


def test_selector_config_keywords_and_numeric_ranges_match_home_assistant_2026_8_1() -> None:
    """Audit supported config keys and simple numeric invariants for every selector config."""

    allowed_keywords = {
        "NumberSelectorConfig": {"min", "max", "step", "unit_of_measurement", "mode", "translation_key", "read_only"},
        "SelectSelectorConfig": {"options", "multiple", "custom_value", "mode", "translation_key", "sort", "read_only"},
        "TextSelectorConfig": {"multiline", "prefix", "suffix", "type", "autocomplete", "multiple", "read_only"},
        "BooleanSelectorConfig": {"read_only"},
        "DateSelectorConfig": {"read_only"},
    }
    audited = 0
    for node in ast.walk(_tree()):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        name = node.func.id
        if name not in allowed_keywords:
            continue
        keywords = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
        assert keywords <= allowed_keywords[name], (
            f"{name} at line {node.lineno} uses unsupported keys {sorted(keywords - allowed_keywords[name])}"
        )
        if name == "NumberSelectorConfig":
            values = {}
            for keyword in node.keywords:
                if keyword.arg in {"min", "max"}:
                    try:
                        values[keyword.arg] = ast.literal_eval(keyword.value)
                    except (ValueError, TypeError):
                        pass
            if {"min", "max"} <= values.keys():
                assert values["min"] <= values["max"], (
                    f"NumberSelectorConfig at line {node.lineno} has min > max"
                )
        audited += 1
    assert audited >= 30

def test_duplicate_broker_objects_have_specific_bounded_errors() -> None:
    source = FLOW.read_text(encoding="utf-8")
    assert 'errors[CONF_BROKER_PROVIDER_ID] = "provider_already_exists"' in source
    assert 'errors[CONF_BROKER_ISIN] = "savings_plan_route_already_exists"' in source
    assert 'errors[CONF_BROKER_TO_PROVIDER] = "funding_transfer_already_exists"' in source

    for language in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        errors = translations["options"]["error"]
        assert errors["provider_already_exists"].strip()
        assert errors["savings_plan_route_already_exists"].strip()
        assert errors["funding_transfer_already_exists"].strip()


def test_broker_editor_accepts_explicit_home_assistant_local_evaluation_date() -> None:
    """The UI must not compare a local date picker value with host-UTC midnight."""

    import sys
    import types
    from datetime import date

    package = sys.modules.get("portfolio_architect")
    if package is None:
        package = types.ModuleType("portfolio_architect")
        package.__path__ = [str(COMPONENT)]
        sys.modules["portfolio_architect"] = package

    from portfolio_architect.broker_editor import upsert_provider

    broker = {
        "schema_version": 2,
        "fee_data_max_age_days": 30,
        "providers": {
            "existing": {
                "name": "Existing",
                "source": "Synthetic evidence",
                "as_of": "2026-08-20",
                "savings_plans": {},
            }
        },
    }
    updated = upsert_provider(
        broker,
        provider_id="new_provider",
        name="New provider",
        source="Synthetic evidence",
        as_of="2026-08-21",
        tie_break="neutral",
        create=True,
        evaluated_on=date(2026, 8, 21),
    )
    assert updated["providers"]["new_provider"]["as_of"] == "2026-08-21"
