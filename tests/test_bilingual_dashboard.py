from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _entities(value):
    found=set()
    if isinstance(value,dict):
        for key,child in value.items():
            if key in {'entity','entity_id'}:
                if isinstance(child,str): found.add(child)
                elif isinstance(child,list): found.update(x for x in child if isinstance(x,str))
            found.update(_entities(child))
    elif isinstance(value,list):
        for child in value: found.update(_entities(child))
    return found


def _walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value,list):
        for child in value:
            yield from _walk(child)


def test_bilingual_dashboard_structure_and_shared_entities():
    dashboard=yaml.safe_load((ROOT/'dashboard/bilingual-dashboard.yaml').read_text())
    views=dashboard['views']
    assert [v['path'] for v in views]==['portfolio-architect','portfolio-architekt']
    assert [v['title'] for v in views]==['EN','DE']
    assert all(v['type']=='sections' and v['max_columns']==2 for v in views)
    assert all(v.get('header',{}).get('layout')=='responsive' for v in views)
    assert all(len(v['sections'])==9 for v in views)
    assert _entities(views[0])==_entities(views[1])


def test_sections_use_native_responsive_cards():
    dashboard=yaml.safe_load((ROOT/'dashboard/bilingual-dashboard.yaml').read_text())
    for view in dashboard['views']:
        assert all(section['type']=='grid' for section in view['sections'])
        for section in view['sections']:
            assert section['cards'][0]['type']=='heading'
        cards=list(_walk(view))
        types={card.get('type') for card in cards if isinstance(card,dict)}
        assert 'markdown' not in types
        assert 'entities' in types
        assert 'entity-filter' in types
        # No nested fixed-column grid cards; only Sections themselves use grid.
        assert not any(card.get('type')=='grid' and 'columns' in card for card in cards)
        assert {'tile','conditional','glance','distribution','heading','entities','entity-filter'} <= types


def test_half_width_tile_labels_are_narrow_screen_safe():
    dashboard=yaml.safe_load((ROOT/'dashboard/bilingual-dashboard.yaml').read_text())
    for card in _walk(dashboard):
        if not isinstance(card,dict):
            continue
        if card.get('type')=='tile' and card.get('grid_options',{}).get('columns')==6:
            assert len(card.get('name','')) <= 20
        if card.get('type')=='conditional' and card.get('grid_options',{}).get('columns')==6:
            inner=card.get('card',{})
            if inner.get('type')=='tile':
                assert len(inner.get('name','')) <= 20


def test_complete_portfolio_and_scope_entities_are_visible():
    source=(ROOT/'dashboard/bilingual-dashboard.yaml').read_text()
    assert 'portfolio_architect_portfolio_value' in source
    assert 'portfolio_architect_current_plan_share' in source
    assert 'portfolio_architect_outside_scope_share' in source
    assert 'presentation_outside_001_whole_portfolio_allocation' in source
    assert 'presentation_outside_001_holding_value' in source
    assert 'portfolio_architect_holding_' not in source
    assert 'legacy' not in source.casefold()


def test_standalone_views_parse():
    for language,path in [('en','portfolio-architect'),('de','portfolio-architekt')]:
        view=yaml.safe_load((ROOT/'dashboard'/language/'view.yaml').read_text())
        assert view['path']==path
        assert view['title']==language.upper()
        assert view['type']=='sections'


def test_monthly_review_cycle_is_present_in_both_views():
    dashboard=yaml.safe_load((ROOT/'dashboard/bilingual-dashboard.yaml').read_text())
    for view in dashboard['views']:
        source=yaml.safe_dump(view, sort_keys=False)
        assert 'portfolio_architect_planned_execution' in source
        assert 'portfolio_architect_next_plan_review' in source
        assert 'portfolio_architect_plan_review_due' in source
        assert 'portfolio_architect_review_schedule_configured' in source
        assert 'portfolio_architect_last_successful_refresh' in source
