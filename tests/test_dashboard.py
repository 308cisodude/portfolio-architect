from pathlib import Path
import yaml

ROOT=Path(__file__).parents[1]
DASHBOARD=ROOT/'dashboard'
LOCALES=('en','de')
FILES={'allocation-stack.yaml','monthly-investment-plan.yaml','policy-compliance.yaml','target-architecture.yaml','runtime-health.yaml','view.yaml'}


def _load(locale,filename):
    return yaml.safe_load((DASHBOARD/locale/filename).read_text(encoding='utf-8'))


def test_localized_dashboard_file_sets_match_and_parse():
    for locale in LOCALES:
        assert {p.name for p in (DASHBOARD/locale).glob('*.yaml')}==FILES
        for filename in FILES: assert _load(locale,filename) is not None


def test_allocation_stack_is_native_and_separates_scopes():
    for locale in LOCALES:
        source=(DASHBOARD/locale/'allocation-stack.yaml').read_text()
        config=yaml.safe_load(source)
        assert config['type']=='vertical-stack'
        assert source.count('type: distribution')==0
        assert source.count('type: entity-filter')>=3
        assert 'whole_portfolio_allocation' in source
        assert 'outside_scope' in source
        assert '_current_allocation' in source and '_target_allocation' in source
        assert 'type: tile' in source
        assert 'type: entities' in source
        assert 'type: entity-filter' in source
        assert 'legacy' not in source.casefold()
        assert 'markdown' not in source.casefold()


def test_monthly_plan_uses_conditional_tiles():
    for locale in LOCALES:
        source=(DASHBOARD/locale/'monthly-investment-plan.yaml').read_text()
        config=yaml.safe_load(source)
        assert config['type']=='vertical-stack'
        assert source.count('_proposed_buy')==32
        assert 'presentation_target_01_purchase_explanation' in source
        assert 'type: conditional' in source
        assert 'type: tile' in source
        assert 'type: entities' in source
        assert 'entity-filter' in source


def test_target_and_runtime_cards_are_compact_native_cards():
    for locale in LOCALES:
        target=(DASHBOARD/locale/'target-architecture.yaml').read_text()
        runtime=(DASHBOARD/locale/'runtime-health.yaml').read_text()
        assert 'type: tile' in target and 'type: glance' in target
        assert 'type: bar-gauge' in target
        assert 'type: tile' in runtime
        assert 'last_successful_refresh' in runtime and 'portfolio_architect_version' in runtime
        assert 'type: entities' in target
        assert 'type: entity-filter' in target
        assert 'type: entities' not in runtime
        assert 'markdown' not in target.casefold()+runtime.casefold()


def test_policy_is_native_cards_only():
    for locale in LOCALES:
        source=(DASHBOARD/locale/'policy-compliance.yaml').read_text()
        assert 'mandatory_controls_compliant' in source
        assert 'policy_checks_evaluated' not in source
        assert source.count('optimisation_opportunity_count') == 2
        assert 'accepted_exception_count' in source
        assert 'type: conditional' in source
        assert 'type: tile' in source
        assert 'type: heading' in source
        assert 'type: entities' in source
        assert 'entity-filter' in source
        assert 'markdown' not in source.casefold()


def test_monthly_cycle_cards_are_native_and_localised():
    for locale in LOCALES:
        monthly=(DASHBOARD/locale/'monthly-investment-plan.yaml').read_text()
        runtime=(DASHBOARD/locale/'runtime-health.yaml').read_text()
        assert 'portfolio_architect_planned_execution' in monthly
        assert 'portfolio_architect_next_plan_review' in runtime
        assert 'portfolio_architect_plan_review_due' in runtime
        assert 'portfolio_architect_review_schedule_configured' in runtime
        assert 'type: tile' in monthly+runtime
        assert 'type: conditional' in monthly+runtime
