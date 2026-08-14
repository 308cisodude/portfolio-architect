"""Regression contracts for v1.25.0 Trade Republic statement import."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import http.client
import importlib.util
import re
import threading

import pytest

ROOT = Path(__file__).parents[1]
TR_APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_trade_republic"
TR_SRC = TR_APP / "src"

# Load the provider-specific App package under an isolated test-only package name so
# collection cannot shadow the canonical standalone Gateway package used elsewhere.
_PACKAGE_NAME = "portfolio_architect_gateway_tr_test"
_PACKAGE_DIR = TR_SRC / "portfolio_architect_gateway"
_package_spec = importlib.util.spec_from_file_location(
    _PACKAGE_NAME,
    _PACKAGE_DIR / "__init__.py",
    submodule_search_locations=[str(_PACKAGE_DIR)],
)
assert _package_spec is not None and _package_spec.loader is not None
_package = importlib.util.module_from_spec(_package_spec)
import sys as _sys
_sys.modules[_PACKAGE_NAME] = _package
_package_spec.loader.exec_module(_package)

from portfolio_architect_gateway_tr_test.trade_republic_statement import (  # type: ignore[import-not-found]  # noqa: E402
    StatementImportError,
    TradeRepublicStatementProvider,
    parse_statement_pdf,
    parse_statement_text,
)
from portfolio_architect_gateway_tr_test.trade_republic_app import (  # type: ignore[import-not-found]  # noqa: E402
    TradeRepublicIngressServer,
    _parse_multipart_body,
)
from portfolio_architect_gateway_tr_test.runtime_config import ServerConfig  # type: ignore[import-not-found]  # noqa: E402
from portfolio_architect_gateway_tr_test.server import GatewayState  # type: ignore[import-not-found]  # noqa: E402


def _synthetic_layout(*, total: str = "1.434,56", count: int = 2) -> str:
    return "\n".join(
        [
            "TRADE REPUBLIC BANK GMBH           SYNTHETIC TEST DOCUMENT",
            "SYNTHETIC PERSON                                      DATUM 15.01.2026",
            "DEPOT SYNTHETIC",
            "                                      DEPOTAUSZUG",
            "                                       zum 15.01.2026",
            "POSITIONEN",
            "STK. / NOMINALE   WERTPAPIERBEZEICHNUNG                          KURS PRO STUECK      KURSWERT IN EUR",
            "10,500000 Stk.    Synthetic World ETF                            117,58               1.234,56",
            "                  ISIN: DE0000000001",
            "2 Stk.            Synthetic Example Share                         100,00                 200,00",
            "                  ISIN: DE0000000002",
            f"                  ANZAHL POSITIONEN: {count}                                           {total} EUR",
            "Erstellt am 2026-01-15 09:30:00 Europe/Berlin (UTC+02:00) Seite 1 von 1",
        ]
    )


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _synthetic_pdf(text: str) -> bytes:
    """Create a tiny, wholly synthetic text PDF without adding a PDF dependency."""
    commands = ["BT", "/F1 9 Tf", "40 790 Td"]
    for index, line in enumerate(text.splitlines()):
        if index:
            commands.append("0 -14 Td")
        commands.append(f"({_pdf_escape(line)}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


def test_synthetic_statement_text_maps_to_provider_neutral_snapshot() -> None:
    snapshot = parse_statement_text(
        _synthetic_layout(),
        now=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
    )
    assert snapshot.generated_at == datetime(2026, 1, 15, 7, 30, tzinfo=timezone.utc)
    assert len(snapshot.positions) == 2
    assert snapshot.positions[0].identifier == "DE0000000001"
    assert snapshot.positions[0].quantity == Decimal("10.500000")
    assert snapshot.positions[0].market_value_eur == Decimal("1234.56")
    assert snapshot.positions[0].instrument_type == "ETF"
    assert snapshot.positions[1].instrument_type == "Stock"
    public = snapshot.as_dict()
    serialized = repr(public)
    assert "SYNTHETIC PERSON" not in serialized
    assert "DEPOT SYNTHETIC" not in serialized


def test_synthetic_pdf_exercises_real_pdf_text_extraction() -> None:
    snapshot = parse_statement_pdf(
        _synthetic_pdf(_synthetic_layout()),
        now=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
    )
    assert len(snapshot.positions) == 2
    assert sum((item.market_value_eur for item in snapshot.positions), Decimal("0")) == Decimal("1434.56")


@pytest.mark.parametrize(
    "text, message",
    [
        (_synthetic_layout(total="1.434,55"), "portfolio total"),
        (_synthetic_layout(count=3), "position count"),
        (_synthetic_layout().replace("ISIN: DE0000000002", "NO ISIN HERE"), "exactly one ISIN"),
        (_synthetic_layout().replace("DEPOTAUSZUG", "KONTOAUSZUG"), "Unsupported Trade Republic document type"),
        (
            _synthetic_layout().replace("zum 15.01.2026", "zum 14.01.2026"),
            "creation date do not match",
        ),
    ],
)
def test_ambiguous_or_inconsistent_statement_fails_closed(text: str, message: str) -> None:
    with pytest.raises(StatementImportError, match=message):
        parse_statement_text(
            text,
            now=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
        )


def test_non_pdf_and_image_only_inputs_fail_closed() -> None:
    with pytest.raises(StatementImportError, match="not a PDF"):
        parse_statement_pdf(b"not-pdf")
    image_only = _synthetic_pdf("")
    with pytest.raises(StatementImportError, match="extractable text layer|unsupported|document type"):
        parse_statement_pdf(image_only)


def test_multipart_parser_accepts_only_nonce_and_pdf() -> None:
    boundary = b"PortfolioArchitectSyntheticBoundary"
    pdf = _synthetic_pdf(_synthetic_layout())
    body = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="nonce"\r\n\r\n'
        b"synthetic-nonce\r\n"
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="statement"; filename="synthetic.pdf"\r\n'
        b"Content-Type: application/pdf\r\n\r\n"
        + pdf
        + b"\r\n--" + boundary + b"--\r\n"
    )
    nonce, document = _parse_multipart_body(body, boundary)
    assert nonce == "synthetic-nonce"
    assert document == pdf



def test_admin_ingress_import_activates_snapshot_without_persisting_pdf(tmp_path: Path) -> None:
    data = tmp_path / "gateway"
    data.mkdir()
    config = ServerConfig(
        bind="127.0.0.1",
        port=0,
        api_token_file=data / "gateway-api-token",
        snapshot_file=data / "portfolio.json",
        max_cached_snapshot_age_seconds=604800,
        tls_cert_file=None,
        tls_key_file=None,
        health_endpoint_enabled=True,
    )
    provider = TradeRepublicStatementProvider(config.snapshot_file)
    state = GatewayState(config, provider)
    server = TradeRepublicIngressServer(
        ("127.0.0.1", 0),
        state=state,
        provider=provider,
        provider_name="Trade Republic",
        api_token="g" * 64,
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=False,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        connection.request("GET", "/")
        response = connection.getresponse()
        page = response.read().decode("utf-8")
        assert response.status == 200
        nonce_match = re.search(r'name="nonce" value="([A-Za-z0-9_-]+)"', page)
        assert nonce_match is not None

        boundary = b"PortfolioArchitectSyntheticBoundary"
        pdf = _synthetic_pdf(_synthetic_layout())
        body = (
            b"--" + boundary + b"\r\n"
            b'Content-Disposition: form-data; name="nonce"\r\n\r\n'
            + nonce_match.group(1).encode("ascii")
            + b"\r\n--" + boundary + b"\r\n"
            b'Content-Disposition: form-data; name="statement"; filename="synthetic.pdf"\r\n'
            b"Content-Type: application/pdf\r\n\r\n"
            + pdf
            + b"\r\n--" + boundary + b"--\r\n"
        )
        connection.request(
            "POST",
            "/import",
            body=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary.decode('ascii')}",
                "Content-Length": str(len(body)),
            },
        )
        response = connection.getresponse()
        accepted_page = response.read().decode("utf-8")
        assert response.status == 200
        assert "Statement accepted: 2 positions" in accepted_page
        assert provider.snapshot is not None
        assert config.snapshot_file.is_file()
        assert not list(tmp_path.rglob("*.pdf"))
        assert "SYNTHETIC PERSON" not in config.snapshot_file.read_text(encoding="utf-8")
        assert "DEPOT SYNTHETIC" not in config.snapshot_file.read_text(encoding="utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

def test_tr_app_dependency_is_hash_locked_and_provider_specific() -> None:
    requirements = (TR_APP / "requirements.txt").read_text(encoding="utf-8")
    assert "pypdf==6.15.0" in requirements
    assert "sha256:14e001d6504822cb1ca9c7ed9a69bccb320f59b320730f55af804361abe4d5ee" in requirements
    dockerfile = (TR_APP / "Dockerfile").read_text(encoding="utf-8")
    assert "--require-hashes" in dockerfile
    assert "--only-binary=:all:" in dockerfile
    assert "--no-deps" in dockerfile
    assert "portfolio_architect_gateway.trade_republic_app" in dockerfile
    assert "pypdf" not in (ROOT / "gateway" / "Dockerfile").read_text(encoding="utf-8")
    assert "pypdf" not in (ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb" / "Dockerfile").read_text(encoding="utf-8")


def test_tr_import_source_is_provider_specific_and_original_pdf_is_not_persisted() -> None:
    source = (TR_SRC / "portfolio_architect_gateway" / "trade_republic_app.py").read_text(encoding="utf-8")
    parser = (TR_SRC / "portfolio_architect_gateway" / "trade_republic_statement.py").read_text(encoding="utf-8")
    assert "read_bytes" not in source
    assert "write_bytes" not in source
    assert "save_snapshot" not in source
    assert "Uploaded documents are parsed in memory" in parser
    assert "ComdirectClient" not in source + parser


def test_no_trade_republic_pdf_fixture_is_tracked() -> None:
    assert not list(ROOT.rglob("*.pdf"))
