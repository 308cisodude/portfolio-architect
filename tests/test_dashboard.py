from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "dashboard"
LOCALES = ("en", "de")


def _dashboard(locale: str) -> dict:
    path = DASHBOARD / "generated" / f"portfolio-architect-dashboard-{locale}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _view(locale: str) -> dict:
    document = _dashboard(locale)
    assert len(document["views"]) == 1
    return document["views"][0]


def _section(locale: str, index: int) -> dict:
    return _view(locale)["sections"][index]


def _source(value: object) -> str:
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True)


def test_localized_generated_dashboards_parse():
    for locale in LOCALES:
        document = _dashboard(locale)
        assert set(document) == {"views"}
        assert len(document["views"]) == 1
        assert len(document["views"][0]["sections"]) == 9


def test_allocation_stack_is_native_and_separates_scopes():
    # Allocation behaviour is spread over the three generated allocation sections.
    for locale in LOCALES:
        source = _source(_view(locale)["sections"][4:9])
        assert source.count("type: distribution") == 0
        assert source.count("type: entity-filter") >= 2
        assert "whole_portfolio_allocation" in source
        assert "outside_scope" in source
        assert "_current_allocation" in source and "_target_allocation" in source
        assert "type: tile" in source
        assert "type: entities" in source
        assert "type: entity-filter" in source
        assert "legacy" not in source.casefold()
        assert "markdown" not in source.casefold()


def test_monthly_plan_uses_conditional_tiles():
    for locale in LOCALES:
        source = _source(_section(locale, 0))
        assert source.count("_proposed_buy") == 32
        assert "presentation_target_01_purchase_explanation" in source
        assert "type: conditional" in source
        assert "type: tile" in source
        assert "type: entities" in source
        assert "entity-filter" in source


def test_target_and_runtime_cards_are_compact_native_cards():
    for locale in LOCALES:
        target = _source(_section(locale, 2))
        runtime = _source(_section(locale, 3))
        assert "type: tile" in target and "type: glance" in target
        assert "type: bar-gauge" in target
        assert "type: tile" in runtime
        assert "last_successful_refresh" in runtime and "portfolio_architect_version" in runtime
        assert "type: entities" in target
        assert "type: entity-filter" in target
        assert "type: entities" not in runtime
        assert "markdown" not in target.casefold() + runtime.casefold()


def test_policy_is_native_cards_only():
    for locale in LOCALES:
        source = _source(_section(locale, 1))
        assert "mandatory_controls_compliant" in source
        assert "policy_checks_evaluated" not in source
        assert source.count("optimisation_opportunity_count") == 2
        assert "accepted_exception_count" in source
        assert "type: conditional" in source
        assert "type: tile" in source
        assert "type: heading" in source
        assert "type: entities" in source
        assert "entity-filter" in source
        assert "markdown" not in source.casefold()


def test_monthly_cycle_cards_are_native_and_localised():
    for locale in LOCALES:
        monthly = _source(_section(locale, 0))
        runtime = _source(_section(locale, 3))
        assert "portfolio_architect_planned_execution" in monthly
        assert "portfolio_architect_next_plan_review" in runtime
        assert "portfolio_architect_plan_review_due" in runtime
        assert "portfolio_architect_review_schedule_configured" in runtime
        assert "type: tile" in monthly + runtime
        assert "type: conditional" in monthly + runtime
