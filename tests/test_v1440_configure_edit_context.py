"""Regression coverage for the v1.52.0 Configure UX consistency pass."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
FLOW = COMPONENT / "config_flow.py"
TRANSLATIONS = COMPONENT / "translations"

OPTIONS_MENU_METHODS = {
    "init": "async_step_init",
    "sources": "async_step_sources",
    "rest_gateways": "async_step_rest_gateways",
    "execution_providers": "async_step_execution_providers",
    "broker_providers": "async_step_broker_providers",
    "broker_savings_plans": "async_step_broker_savings_plans",
    "funding_topology": "async_step_funding_topology",
}

EDIT_CONTEXT_KEYS = {
    "edit_execution_provider_details": {"provider_name", "provider_id"},
    "edit_savings_plan_route_details": {"provider_name", "provider_id", "isin"},
    "edit_funding_transfer_details": {
        "from_provider_name",
        "from_provider_id",
        "to_provider_name",
        "to_provider_id",
    },
    "edit_rest_gateway_details": {"provider", "provider_id", "endpoint"},
}


def _options_flow() -> ast.ClassDef:
    tree = ast.parse(FLOW.read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PortfolioArchitectOptionsFlow"
    )


def _method(name: str) -> ast.AsyncFunctionDef:
    flow = _options_flow()
    return next(
        node
        for node in flow.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    )


def _menu_options_in_emission_order(function_name: str) -> list[str]:
    method = _method(function_name)
    show_menu = next(
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "async_show_menu"
    )
    keyword = next(item for item in show_menu.keywords if item.arg == "menu_options")
    if isinstance(keyword.value, (ast.List, ast.Tuple)):
        return [
            item.value
            for item in keyword.value.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ]
    assert isinstance(keyword.value, ast.Name)
    variable = keyword.value.id

    events: list[tuple[int, list[str]]] = []
    for node in ast.walk(method):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == variable for target in node.targets
        ):
            if isinstance(node.value, (ast.List, ast.Tuple)):
                events.append(
                    (
                        node.lineno,
                        [
                            item.value
                            for item in node.value.elts
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        ],
                    )
                )
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == variable
        ):
            continue
        if node.func.attr == "append" and len(node.args) == 1:
            item = node.args[0]
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                events.append((node.lineno, [item.value]))
        elif node.func.attr == "extend" and len(node.args) == 1:
            values = node.args[0]
            if isinstance(values, (ast.List, ast.Tuple)):
                events.append(
                    (
                        node.lineno,
                        [
                            item.value
                            for item in values.elts
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        ],
                    )
                )

    result: list[str] = []
    for _, values in sorted(events):
        for value in values:
            if value not in result:
                result.append(value)
    for node in ast.walk(method):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == variable
            and node.func.attr == "insert"
            and len(node.args) == 2
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, int)
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            continue
        value = node.args[1].value
        if value not in result:
            result.insert(node.args[0].value, value)
    return result


def _description_placeholder_keys(step_id: str) -> set[str]:
    method = _method(f"async_step_{step_id}")
    show_form = next(
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "async_show_form"
        and any(
            keyword.arg == "step_id"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value == step_id
            for keyword in node.keywords
        )
    )
    keyword = next(
        (item for item in show_form.keywords if item.arg == "description_placeholders"),
        None,
    )
    assert keyword is not None, f"{step_id} has no description_placeholders"
    assert isinstance(keyword.value, ast.Dict), f"{step_id} placeholders must be explicit"
    return {
        key.value
        for key in keyword.value.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def test_every_configure_menu_has_complete_bilingual_labels_in_emission_order() -> None:
    """Audit every menu below Configure, not only the broker-editor branch."""

    emitted = {
        step_id: _menu_options_in_emission_order(method_name)
        for step_id, method_name in OPTIONS_MENU_METHODS.items()
    }
    assert all(emitted.values())

    for language in ("en", "de"):
        translation = json.loads(
            (TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8")
        )
        steps = translation["options"]["step"]
        for step_id, targets in emitted.items():
            menu_options = steps[step_id].get("menu_options")
            assert isinstance(menu_options, dict), (language, step_id)
            assert list(menu_options) == targets, (language, step_id, targets, menu_options)
            for target in targets:
                assert isinstance(menu_options[target], str) and menu_options[target].strip()
                assert target in steps and isinstance(steps[target].get("title"), str)
                assert steps[target]["title"].strip()


def test_every_existing_object_edit_form_has_visible_immutable_context() -> None:
    """Every selected-object editor must identify the object above editable fields."""

    flow = _options_flow()
    discovered = {
        node.name.removeprefix("async_step_")
        for node in flow.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name.startswith("async_step_edit_")
        and node.name.endswith("_details")
    }
    assert discovered == set(EDIT_CONTEXT_KEYS), discovered

    for step_id, required_keys in EDIT_CONTEXT_KEYS.items():
        assert required_keys <= _description_placeholder_keys(step_id)

    for language, marker in (("en", "**Editing:**"), ("de", "**Bearbeitet:**")):
        translation = json.loads(
            (TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8")
        )
        steps = translation["options"]["step"]
        for step_id, required_keys in EDIT_CONTEXT_KEYS.items():
            description = steps[step_id].get("description", "")
            assert description.startswith(marker), (language, step_id, description)
            for key in required_keys:
                assert "{" + key + "}" in description, (language, step_id, key)


def test_plan_instrument_editor_already_exposes_instrument_identity() -> None:
    """The plan editor was already compliant and must stay that way."""

    for language in ("en", "de"):
        translation = json.loads(
            (TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8")
        )
        step = translation["options"]["step"]["plan_instrument"]
        combined = f"{step.get('title', '')}\n{step.get('description', '')}"
        for placeholder in ("{instrument_name}", "{isin}", "{target_id}"):
            assert placeholder in combined
