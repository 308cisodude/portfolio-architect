"""Regression coverage for the v1.35.4 execution-policy menu-label hotfix."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
FLOW = COMPONENT / "config_flow.py"
TRANSLATIONS = COMPONENT / "translations"

BROKER_MENU_STEPS = {
    "execution_providers": "async_step_execution_providers",
    "broker_providers": "async_step_broker_providers",
    "broker_savings_plans": "async_step_broker_savings_plans",
    "funding_topology": "async_step_funding_topology",
}


def _literal_menu_options(function_name: str) -> set[str]:
    tree = ast.parse(FLOW.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PortfolioArchitectOptionsFlow"
    )
    method = next(
        node
        for node in function.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    options: set[str] = set()
    for node in ast.walk(method):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "menu" for target in node.targets
        ):
            if isinstance(node.value, (ast.List, ast.Tuple)):
                options.update(
                    item.value
                    for item in node.value.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                )
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "menu":
            continue
        if node.func.attr == "append" and len(node.args) == 1:
            item = node.args[0]
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                options.add(item.value)
        elif node.func.attr == "extend" and len(node.args) == 1:
            values = node.args[0]
            if isinstance(values, (ast.List, ast.Tuple)):
                options.update(
                    item.value
                    for item in values.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                )
    return options


def test_every_broker_editor_menu_option_has_english_and_german_label() -> None:
    for language in ("en", "de"):
        translation = json.loads(
            (TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8")
        )
        steps = translation["options"]["step"]
        for step_id, method_name in BROKER_MENU_STEPS.items():
            emitted = _literal_menu_options(method_name)
            assert emitted, (language, step_id, "no emitted menu options discovered")
            menu_options = steps[step_id].get("menu_options")
            assert isinstance(menu_options, dict), (language, step_id)
            assert set(menu_options) == emitted, (language, step_id, emitted, menu_options)
            for option in emitted:
                assert isinstance(menu_options[option], str) and menu_options[option].strip()
                assert menu_options[option] == steps[option]["title"]
