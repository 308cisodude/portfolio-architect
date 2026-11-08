"""Synthetic coverage for combined TR evidence and atomic publication."""
from datetime import datetime, timezone
from pathlib import Path
import importlib
import pytest
from test_v1250_trade_republic_statement_import import _synthetic_layout, _synthetic_pdf, TradeRepublicStatementProvider

mod = importlib.import_module('portfolio_architect_gateway_tr_test.trade_republic_import')
NOW = datetime(2026, 1, 16, tzinfo=timezone.utc)


def combined():
    legacy = _synthetic_layout()
    positions = legacy[legacy.index('POSITIONEN'):legacy.index('Erstellt am')]
    return '\n'.join([
        'TRADE REPUBLIC BANK GMBH', 'VERMÖGENSÜBERSICHT', 'zum 15.01.2026',
        'Brokerage  1.434,56', 'Crypto Wallet  25,00', 'Cash  400,00', 'GESAMT  1.859,56 EUR',
        'BROKERAGE', 'Aufstellung über die Brokerage Wertpapiere zum 15.01.2026.', positions,
        'CRYPTO WALLET', 'Aufstellung über die Crypto Assets zum 15.01.2026.',
        'Erstellt am 2026-01-15 09:30:00 Europe/Berlin (UTC+01:00)', '\f',
        'TRADE REPUBLIC BANK GMBH', '1 Stk.  Synthetic Crypto  25,00  25,00', 'TOKEN',
        'ANZAHL POSITIONEN: 1  25,00 EUR', 'CASH', 'Aufstellung über das Cash zum 15.01.2026.',
        'PRODUKT  SALDO', 'Cashkonto  400,00 EUR',
        'Erstellt am 2026-01-15 09:30:00 Europe/Berlin (UTC+01:00)',
    ])


def test_combined_sections_and_conservative_independent_evidence():
    e = mod.parse_net_worth_text(combined(), now=NOW)
    assert len(e.holdings.positions) == 2
    assert str(e.cash.account_balance_eur) == '400.00'
    assert e.cash.as_of == datetime(2026,1,14,23,tzinfo=timezone.utc)
    assert e.holdings.generated_at == e.cash.as_of
    assert all(p.name != 'Synthetic Crypto' for p in e.holdings.positions)


@pytest.mark.parametrize('old,new', [
    ('Cashkonto  400,00','Cashkonto  401,00'), ('GESAMT  1.859,56','GESAMT  1.859,57'),
    ('ANZAHL POSITIONEN: 2','ANZAHL POSITIONEN: 3'), ('BROKERAGE\n','UNKNOWN\n'),
    ('TOKEN','ISIN: DE0000000001\nCASH'), ('Crypto Wallet  25,00','Crypto Wallet  26,00'),
    ('zum 15.01.2026.\nPRODUKT','zum 14.01.2026.\nPRODUKT'),
])
def test_bad_combined_document_rejected(old,new):
    with pytest.raises(mod.StatementImportError):
        mod.parse_net_worth_text(combined().replace(old,new),now=NOW)


def synthetic_combined_pdf(text):
    # Wholly synthetic Latin-1 PDF, including German document markers.
    commands = ["BT", "/F1 8 Tf", "20 790 Td"]
    for line in text.replace("\f", "").splitlines():
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands += [f"({escaped}) Tj", "0 -12 Td"]
    stream = "\n".join(commands + ["ET"]).encode("cp1252")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n".encode() + b"0000000000 65535 f \n")
    for n in offsets[1:]:out.extend(f"{n:010d} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(out)


def test_real_pdf_dispatch_and_legacy_compatibility():
    e = mod.parse_import_pdf(synthetic_combined_pdf(combined()),now=NOW)
    assert len(e.holdings.positions) == 2
    assert e.cash.account_balance_eur == 400
    assert mod.parse_import_pdf(_synthetic_pdf(_synthetic_layout()),now=NOW).cash is None


def test_atomic_commit_restart_rollback_and_older_evidence(tmp_path):
    from portfolio_architect_gateway_tr_test.store import save_snapshot
    e = mod.parse_net_worth_text(combined(),now=NOW)
    p = TradeRepublicStatementProvider(tmp_path/'portfolio.json')
    def publish(**kwargs):
        save_snapshot(p.snapshot_file,p.snapshot)
        return True
    p.activate_evidence(e,publish)
    restored = TradeRepublicStatementProvider(p.snapshot_file)
    assert restored.snapshot == p.snapshot
    assert restored.cash_snapshot.as_of == e.cash.as_of
    before = p.snapshot_file.read_bytes()
    newer = mod.parse_net_worth_text(combined().replace('15.01.2026','16.01.2026').replace('2026-01-15','2026-01-16'),now=datetime(2026,1,17,tzinfo=timezone.utc))
    with pytest.raises(mod.StatementImportError): p.activate_evidence(newer,lambda **kw:False)
    assert p.snapshot_file.read_bytes() == before
    assert p.snapshot == restored.snapshot
    p.activate_evidence(newer,publish)
    with pytest.raises(mod.StatementImportError): p.activate_evidence(e,publish)


def test_canonical_cash_wins_over_legacy_sidecar_and_cash_only_bootstrap(tmp_path):
    from portfolio_architect_gateway_tr_test.store import save_snapshot
    from portfolio_architect_gateway_tr_test.trade_republic_cash_statement import save_cash_snapshot
    e = mod.parse_net_worth_text(combined(),now=NOW)
    p = TradeRepublicStatementProvider(tmp_path/'portfolio.json')
    p.activate_evidence(mod.StatementEvidence(cash=e.cash),lambda **kw:False)
    assert TradeRepublicStatementProvider(p.snapshot_file).cash_snapshot == e.cash
    p.activate_evidence(e,lambda **kw: (save_snapshot(p.snapshot_file,p.snapshot) or True))
    stale = mod.TradeRepublicCashSnapshot(e.cash.account_balance_eur+1,e.cash.as_of,e.cash.generated_at)
    save_cash_snapshot(p.cash_file,stale)
    assert TradeRepublicStatementProvider(p.snapshot_file).cash_snapshot.account_balance_eur == e.cash.account_balance_eur


def test_one_upload_form_commits_both_and_rejects_bad_pair(tmp_path):
    import http.client
    import threading
    import re
    from portfolio_architect_gateway_tr_test.trade_republic_app import TradeRepublicIngressServer
    from portfolio_architect_gateway_tr_test.runtime_config import ServerConfig
    from portfolio_architect_gateway_tr_test.server import GatewayState
    config = ServerConfig(bind='127.0.0.1',port=0,api_token_file=tmp_path/'token',
        snapshot_file=tmp_path/'portfolio.json',max_cached_snapshot_age_seconds=604800,
        tls_cert_file=None,tls_key_file=None,health_endpoint_enabled=True)
    p = TradeRepublicStatementProvider(config.snapshot_file)
    state = GatewayState(config,p)
    server = TradeRepublicIngressServer(('127.0.0.1',0),state=state,provider=p,
        provider_name='Trade Republic',api_token='x'*64,
        allowed_sources=frozenset({'127.0.0.1'}),require_user_header=False)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        connection=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=5)
        connection.request('GET','/');response=connection.getresponse();page=response.read().decode()
        assert page.count('type="file"') == 1
        assert 'Import TR statement' in page
        nonce=re.search(r'name="nonce" value="([A-Za-z0-9_-]+)"',page).group(1)
        def post(text):
            boundary='SyntheticBoundary'
            body=(f'--{boundary}\r\nContent-Disposition: form-data; name="nonce"\r\n\r\n{nonce}\r\n'
                  f'--{boundary}\r\nContent-Disposition: form-data; name="statement"; filename="synthetic.pdf"\r\n'
                  'Content-Type: application/pdf\r\n\r\n').encode()+synthetic_combined_pdf(text)+f'\r\n--{boundary}--\r\n'.encode()
            connection.request('POST','/import',body=body,headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
            response=connection.getresponse();response.read();return response.status
        assert post(combined()) == 200
        assert p.cash_snapshot.account_balance_eur == 400
        assert len(p.holdings_snapshot.positions) == 2
        before=config.snapshot_file.read_bytes()
        assert post(combined().replace('Cashkonto  400,00','Cashkonto  401,00')) == 400
        assert config.snapshot_file.read_bytes() == before
        assert TradeRepublicStatementProvider(config.snapshot_file).snapshot == p.snapshot
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)


def test_unified_dispatch_accepts_existing_cash_statement_pdf():
    from test_v1410_trade_republic_cash_statement import _cash_layout
    e = mod.parse_import_pdf(synthetic_combined_pdf(_cash_layout()),
        now=datetime(2026,8,22,tzinfo=timezone.utc))
    assert e.holdings is None
    assert str(e.cash.account_balance_eur) == '4321.09'
