"""Complete-portfolio and current-plan scope regression tests."""

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT=Path(__file__).parents[1]
ENGINE_ROOT=ROOT/'custom_components'/'portfolio_architect'
sys.path.insert(0,str(ENGINE_ROOT))
from engine import calculate_portfolio_payload
MODEL_PATH=ROOT/'custom_components/portfolio_architect/model.py'
SPEC=importlib.util.spec_from_file_location('scope_model',MODEL_PATH)
assert SPEC and SPEC.loader
MODEL=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=MODEL;SPEC.loader.exec_module(MODEL)


def test_current_reference_depot_scope_contract():
    depot=ROOT/'tests'/'fixtures'/'comdirect-depot-sanitized.csv'
    payload=calculate_portfolio_payload(
        depot,
        ROOT/'examples'/'current-plan',
        evaluated_at=datetime(2026,8,17,12,0,tzinfo=timezone.utc),
    )
    summary=payload['summary']
    assert payload['schema_version']==8
    assert summary['whole_portfolio_position_count']==13
    assert summary['current_plan_position_count']==7
    assert summary['current_plan_held_position_count']==6
    assert summary['outside_scope_position_count']==7
    assert float(round(summary['whole_portfolio_value_eur'],2))==14053.01
    assert float(round(summary['current_plan_value_eur'],2))==10550.00
    assert float(round(summary['outside_scope_value_eur'],2))==3503.01
    assert [x['fund_id'] for x in payload['recommendations']]==[
        'world','emerging_markets','world_small_cap','healthcare','ai_big_data','cybersecurity','robotics'
    ]
    it=next(x for x in payload['holdings'] if x['wkn']=='A113FM')
    assert it['strategy_scope']=='outside_scope'
    old_robotics=next(x for x in payload['holdings'] if x['isin']=='IE00BYWZ0333')
    assert old_robotics['position_id']=='holding_ie00bywz0333'
    assert old_robotics['strategy_scope']=='outside_scope'
    assert it['plan_current_pct'] is None
    assert all(x['fund_id']!='legacy_world_information_technology' for x in payload['recommendations'])

    data=MODEL.parse_portfolio_data(
        payload['recommendations'],payload['summary'],payload['policy_findings'],holdings=payload['holdings']
    )
    assert len(data.holdings)==13
    assert len(data.positions)==7
    assert data.allocation.underweight==1
    assert data.allocation.on_target==4
    assert data.allocation.overweight==2


def test_outside_scope_holding_cannot_claim_plan_metadata():
    recommendations=[{
        'fund_id':'world','wkn':'A1XB5U','isin':'IE00BJ0KDQ92','name':'World','target_pct':100,
        'current_value_eur':100,'target_value_eur':100,'deviation_eur':0,'current_pct':100,
        'whole_portfolio_pct':50,'deviation_pp':0,'allocation_status':'on_target','buy_enabled':True,
        'proposed_buy_eur':10,
    }]
    holdings=[
      {'position_id':'world','wkn':'A1XB5U','isin':'IE00BJ0KDQ92','name':'World','instrument_type':'etf','source_type':'ETF','current_value_eur':100,'whole_portfolio_pct':50,'strategy_scope':'current_plan','plan_fund_id':'world','plan_current_pct':100},
      {'position_id':'holding_123456','wkn':'123456','isin':'DE0001234567','name':'Stock','instrument_type':'stock','source_type':'Aktie','current_value_eur':100,'whole_portfolio_pct':50,'strategy_scope':'outside_scope','plan_fund_id':'world','plan_current_pct':0},
    ]
    try:
        MODEL.parse_holdings(holdings,MODEL.parse_recommendations(recommendations))
    except MODEL.PortfolioArchitectDataError as err:
        assert 'outside-scope metadata' in str(err)
    else:
        raise AssertionError('outside-scope holding accepted plan metadata')
