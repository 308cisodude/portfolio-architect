"""Regression coverage for v1.61.0 Configure removal confirmation UX."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
FLOW = COMPONENT / "config_flow.py"
TRANSLATIONS = COMPONENT / "translations"

REMOVALS = {
    "remove_rest_gateway": {
        "detail": "remove_rest_gateway_details",
        "context": {"provider", "provider_id", "endpoint"},
        "mutation": "options[CONF_SUPPLEMENTAL_REST_SOURCES]",
    },
    "remove_execution_provider": {
        "detail": "remove_execution_provider_details",
        "context": {"provider_name", "provider_id"},
        "mutation": "updated = remove_provider(",
    },
    "remove_savings_plan_route": {
        "detail": "remove_savings_plan_route_details",
        "context": {"provider_name", "provider_id", "isin"},
        "mutation": "updated = remove_savings_plan(",
    },
    "remove_funding_transfer": {
        "detail": "remove_funding_transfer_details",
        "context": {
            "from_provider_name",
            "from_provider_id",
            "to_provider_name",
            "to_provider_id",
        },
        "mutation": "updated = remove_funding_transfer(",
    },
}


def _flow_class() -> ast.ClassDef:
    tree = ast.parse(FLOW.read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PortfolioArchitectOptionsFlow"
    )


def _method(name: str) -> ast.AsyncFunctionDef:
    return next(
        node
        for node in _flow_class().body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == f"async_step_{name}"
    )


def _source(method: ast.AsyncFunctionDef) -> str:
    return ast.get_source_segment(FLOW.read_text(encoding="utf-8"), method) or ""


def _placeholders(step_id: str) -> set[str]:
    method = _method(step_id)
    form = next(
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "async_show_form"
        and any(
            kw.arg == "step_id"
            and isinstance(kw.value, ast.Constant)
            and kw.value.value == step_id
            for kw in node.keywords
        )
    )
    placeholders = next(kw.value for kw in form.keywords if kw.arg == "description_placeholders")
    assert isinstance(placeholders, ast.Dict)
    return {
        key.value
        for key in placeholders.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def test_destructive_selected_object_actions_are_two_step_and_non_destructive_on_selection() -> None:
    source = FLOW.read_text(encoding="utf-8")
    assert 'CONF_CONFIRM_REMOVE = "confirm_remove"' in source
    for step_id, contract in REMOVALS.items():
        selection = _source(_method(step_id))
        detail = _source(_method(contract["detail"]))
        assert f"return await self.async_step_{contract['detail']}()" in selection
        assert contract["mutation"] not in selection
        assert "CONF_CONFIRM_REMOVE" in detail
        assert "BooleanSelector" in detail
        assert "bool(user_input.get(CONF_CONFIRM_REMOVE))" in detail
        assert contract["mutation"] in detail
        assert "last_step=True" in detail


def test_removal_confirmation_forms_show_immutable_identity_context() -> None:
    for step_id, contract in REMOVALS.items():
        assert contract["context"] <= _placeholders(contract["detail"]), step_id


def test_removal_confirmation_copy_is_bilingual_and_explicit() -> None:
    for language, marker, confirmation in (
        ("en", "**Removing:**", "Confirm removal"),
        ("de", "**Entfernen:**", "Entfernen bestätigen"),
    ):
        data = json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
        steps = data["options"]["step"]
        for step_id, contract in REMOVALS.items():
            selection = steps[step_id]
            detail = steps[contract["detail"]]
            assert "confirmation" in selection["description"].lower() if language == "en" else "Bestätigung" in selection["description"]
            assert detail["description"].startswith(marker)
            assert detail["data"]["confirm_remove"] == confirmation
            for key in contract["context"]:
                assert "{" + key + "}" in detail["description"]


def test_primary_source_is_not_offered_as_a_removal_target() -> None:
    data = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))
    sources = data["options"]["step"]["sources"]
    assert list(sources["menu_options"]) == ["primary_rest_gateway", "rest_gateways"]
    assert "remove" not in sources["menu_options"]["primary_rest_gateway"].lower()
    assert "exactly one primary source" in sources["description"]
