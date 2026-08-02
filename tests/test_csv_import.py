"""CSV import security and instrument-scope tests."""

from pathlib import Path
import sys

ENGINE_ROOT=Path(__file__).parents[1]/'custom_components'/'portfolio_architect'
sys.path.insert(0,str(ENGINE_ROOT))
from engine.io import read_comdirect_positions  # noqa:E402


def _write(path:Path,body:str):
    path.write_bytes(body.encode('iso-8859-1'))


def test_all_security_types_are_imported(tmp_path):
    path=tmp_path/'depot.csv'
    _write(path,';\nStück / Nominale;Bezeichnung;WKN;Typ;Wert in EUR;ISIN\n1;ETF One;A1XB5U;ETF;100,00;IE00BJ0KDQ92\n2;Stock One;555750;Aktie;200,00;DE0005557508\nDepotwert;EUR;300,00\n')
    positions=read_comdirect_positions(path)
    assert set(positions)=={'A1XB5U','555750'}
    assert positions['A1XB5U'].instrument_type=='etf'
    assert positions['555750'].instrument_type=='stock'


def test_duplicate_wkn_is_rejected(tmp_path):
    path=tmp_path/'depot.csv'
    _write(path,';\nBezeichnung;WKN;Typ;Wert in EUR;ISIN\nOne;555750;Aktie;100,00;DE0005557508\nTwo;555750;Aktie;200,00;DE0005557508\n')
    try:
        read_comdirect_positions(path)
    except ValueError as err:
        assert 'duplicate WKN' in str(err)
    else:
        raise AssertionError('duplicate WKN was accepted')
