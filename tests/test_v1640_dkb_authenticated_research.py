"""Authenticated DKB research never promotes capability evidence into acquisition."""
from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from fints.client import FinTSOperations

ROOT = Path(__file__).parents[1]
APP = ROOT / 'home_assistant_app/portfolio_architect_gateway_dkb'
PACKAGE = APP / 'src/portfolio_architect_gateway'
NAME = 'portfolio_architect_gateway_dkb_v1640_test'
PRODUCT = '9FA6681DEC0CF3046BFC2F8A6'


def modules():
    if NAME not in sys.modules:
        spec = importlib.util.spec_from_file_location(NAME, PACKAGE / '__init__.py', submodule_search_locations=[str(PACKAGE)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[NAME] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f'{NAME}.dkb_authenticated'), importlib.import_module(f'{NAME}.dkb_app')


def test_decoupled_approval_completes_and_secrets_remain_transient(monkeypatch, tmp_path):
    research, app = modules()
    import fints.client
    class Challenge:
        decoupled = True
    class Client:
        upa = object()
        upd_version = 7
        _standing_dialog = None
        init_tan_response = Challenge()
        def __init__(self, _bank, user, pin, endpoint, **kwargs):
            assert (user, pin, endpoint, kwargs['product_id']) == ('test.user', 'PRIVATE-PIN', research.DKB_FINTS_ENDPOINT, PRODUCT)
        def fetch_tan_mechanisms(self): return '920'
        def get_current_tan_mechanism(self): return '920'
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def send_tan(self, challenge, tan):
            assert isinstance(challenge, Challenge) and tan == ''
            return object()  # Bank app approved.
        def get_information(self):
            return {'accounts': [{'iban': 'PRIVATE-IBAN', 'owner_name': ['PRIVATE-NAME'],
                                  'supported_operations': {FinTSOperations.GET_HOLDINGS: True}}],
                    'auth': {'current_tan_mechanism': '920'}}
    monkeypatch.setattr(fints.client, 'FinTS3PinTanClient', Client)
    monkeypatch.setattr(fints.client, 'NeedTANResponse', Challenge)
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT)
    pending = controller.run_auth_observation('test.user', 'PRIVATE-PIN')
    assert pending.outcome == 'approval_pending'
    assert controller.pending_auth_is_decoupled()
    assert not (tmp_path / app.AUTH_STATE_FILE_NAME).exists()
    result = controller.continue_auth_observation()
    assert (result.outcome, result.upd_version, result.securities_capability, result.auth_method) == ('authenticated', 7, 'yes', '920')
    persisted = (tmp_path / app.AUTH_STATE_FILE_NAME).read_text()
    for secret in ('PRIVATE-PIN', 'test.user', 'PRIVATE-IBAN', 'PRIVATE-NAME'):
        assert secret not in persisted
    assert controller.auth_observation() == result
    controller.configure_product_id('A' * 25)
    assert controller.auth_observation() is None


def test_decoupled_poll_stays_pending_then_times_out(monkeypatch, tmp_path):
    research, app = modules()
    import fints.client
    class Challenge:
        decoupled = True
    class Client:
        init_tan_response = Challenge()
        _standing_dialog = None
        def __init__(self, *_args, **_kwargs): pass
        def fetch_tan_mechanisms(self): pass
        def get_current_tan_mechanism(self): return '920'
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def send_tan(self, *_args): return Challenge()
    monkeypatch.setattr(fints.client, 'FinTS3PinTanClient', Client)
    monkeypatch.setattr(fints.client, 'NeedTANResponse', Challenge)
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT)
    controller.run_auth_observation('valid', 'PRIVATE-PIN')
    assert controller.continue_auth_observation().outcome == 'approval_pending'
    monkeypatch.setattr(app.time, 'monotonic', lambda: float('inf'))
    assert controller.auth_observation().outcome == 'approval_expired'
    assert not controller.pending_auth_is_decoupled()


def test_invalid_credentials_rejected_before_bank_call():
    research, _ = modules()
    for user, pin in [('a+b', 'pin'), ('valid', 'x\nsecret'), ('valid', '')]:
        with pytest.raises(ValueError):
            research.begin_authenticated_observation(PRODUCT, user, pin)


def test_research_boundary_and_lock_are_packaged():
    source = (PACKAGE / 'dkb_authenticated.py').read_text()
    assert 'get_holdings(' not in source and 'get_balance(' not in source
    assert 'get_transactions(' not in source and 'sepa_transfer(' not in source
    config = (APP / 'config.yaml').read_text()
    assert 'research' in config and 'FinTS acquisition remains disabled' in config
    lock = (APP / 'requirements-fints.txt').read_text()
    assert 'fints==5.0.0' in lock and lock.count('--hash=sha256:') >= 17
