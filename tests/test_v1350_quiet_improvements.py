"""v1.35.0 low-risk dashboard-label and DKB probe-evidence regressions."""

from __future__ import annotations

import base64
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb"
PACKAGE = APP / "src" / "portfolio_architect_gateway"
TEST_PACKAGE = "portfolio_architect_gateway_dkb_v1350_test"
PRODUCT_ID = "9FA6681DEC0CF3046BFC2F8A6"


def _load_package():
    if TEST_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            TEST_PACKAGE,
            PACKAGE / "__init__.py",
            submodule_search_locations=[str(PACKAGE)],
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[TEST_PACKAGE] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f"{TEST_PACKAGE}.dkb_fints"), importlib.import_module(
        f"{TEST_PACKAGE}.dkb_app"
    )


def _response_payload(*segments: bytes) -> bytes:
    payload = b"".join(
        (b"HNHBK:1:3+000000000000+300+dialog+1'", *segments, b"HNHBS:99:1+1'")
    )
    size = f"{len(payload):012d}".encode()
    return payload.replace(b"000000000000", size, 1)


class _FakeResponse:
    status = 200

    def __init__(self, body: bytes) -> None:
        self._body = body
        self._read = False

    def read(self, _limit: int | None = None) -> bytes:
        if self._read:
            return b""
        self._read = True
        return self._body


class _FakeHttpsConnection:
    body = b""

    def __init__(self, *_args, **_kwargs) -> None:
        self.request_args = None

    def request(self, *args, **kwargs) -> None:
        self.request_args = (args, kwargs)

    def getresponse(self) -> _FakeResponse:
        return _FakeResponse(self.body)

    def close(self) -> None:
        return None


def test_dkb_probe_fingerprints_exact_raw_http_body_before_decode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fints, app = _load_package()
    decoded = _response_payload(
        b"HIRMG:2:2+9800::Dialog abgebrochen+9078::FinTS-Produkt nicht registriert+3079::Hersteller kontaktieren'"
    )
    # Deliberately retain a trailing newline: it must affect only the raw-body
    # fingerprint, while base64 decoding still yields the same bounded FinTS payload.
    encoded_body = base64.b64encode(decoded) + b"\n"
    _FakeHttpsConnection.body = encoded_body
    monkeypatch.setattr(fints.http.client, "HTTPSConnection", _FakeHttpsConnection)

    result = fints.probe_dkb_bpd(PRODUCT_ID)
    assert result.outcome == "bank_rejected"
    assert result.raw_response_sha256 == hashlib.sha256(encoded_body).hexdigest()
    assert result.raw_response_bytes == len(encoded_body)
    assert result.response_sha256 == hashlib.sha256(decoded).hexdigest()
    assert result.response_bytes == len(decoded)
    assert result.raw_response_sha256 != result.response_sha256

    persisted = result.as_dict()
    assert persisted["schema_version"] == 3
    assert persisted["raw_response_sha256"] == result.raw_response_sha256
    assert persisted["raw_response_bytes"] == len(encoded_body)
    serialized = json.dumps(persisted, sort_keys=True)
    assert encoded_body.decode("ascii").strip() not in serialized
    assert decoded.decode("iso-8859-1") not in serialized

    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT_ID)
    monkeypatch.setattr(app, "probe_dkb_bpd", lambda _product_id: result)
    view = controller.run_probe()
    assert view.result is not None
    assert view.result.raw_response_sha256 == result.raw_response_sha256
    assert view.result.raw_response_bytes == len(encoded_body)
    reopened = controller.probe_view()
    assert reopened.result is not None
    assert reopened.result.raw_response_sha256 == result.raw_response_sha256
    assert reopened.result.raw_response_bytes == len(encoded_body)


def test_dashboard_distinguishes_accumulating_and_distributing_robotics() -> None:
    en = (ROOT / "dashboard" / "en" / "view.yaml").read_text(encoding="utf-8")
    de = (ROOT / "dashboard" / "de" / "view.yaml").read_text(encoding="utf-8")
    bilingual = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")

    assert "name: Robotics · Acc" in en
    assert "name: Robotics · Dist" in en
    assert "name: Robotik · Thes." in de
    assert "name: Robotik · Aussch." in de
    assert "name: Robotics · Acc" in bilingual
    assert "name: Robotik · Thes." in bilingual

    for source in (en, bilingual):
        assert "name: Robotics\n" not in source
        assert "name: Robotics sources\n" not in source
    for source in (de, bilingual):
        assert "name: Robotik\n" not in source
        assert "name: Quellen Robotik\n" not in source
