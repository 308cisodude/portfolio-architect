"""v1.31.2 DKB FinTS probe hardening and live-failure regression contracts."""

from __future__ import annotations

import hashlib
import http.client
import importlib
import importlib.util
import json
import stat
from pathlib import Path
import sys
import threading
from urllib.parse import urlencode

import pytest

ROOT = Path(__file__).parents[1]
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb"
PACKAGE = APP / "src" / "portfolio_architect_gateway"
TEST_PACKAGE = "portfolio_architect_gateway_dkb_v1312_test"
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
    payload = b"".join((b"HNHBK:1:3+000000000000+300+dialog+1'", *segments, b"HNHBS:99:1+1'"))
    size = f"{len(payload):012d}".encode()
    return payload.replace(b"000000000000", size, 1)


def test_registration_id_is_exactly_25_chars_and_occurs_only_in_hkvvb_product_field() -> None:
    fints, _app = _load_package()
    assert len(PRODUCT_ID) == 25
    assert fints.normalise_product_id(PRODUCT_ID) == PRODUCT_ID
    for value in ("A" * 24, "A" * 26, "A" * 24 + "+", ""):
        with pytest.raises(ValueError, match="exactly 25"):
            fints.normalise_product_id(value)

    payload = fints.build_anonymous_bpd_request(PRODUCT_ID)
    assert payload.count(PRODUCT_ID.encode("ascii")) == 1
    segments = [segment for segment in payload.split(b"'") if segment]
    containing = [segment for segment in segments if PRODUCT_ID.encode("ascii") in segment]
    assert len(containing) == 1
    hkvvb = containing[0]
    assert hkvvb.startswith(b"HKVVB:3:3+")
    fields = hkvvb.split(b"+")
    assert fields[4] == PRODUCT_ID.encode("ascii")
    assert fields[5] == fints.FINTS_PRODUCT_VERSION.encode("ascii")


def test_valid_bank_rejection_preserves_only_bounded_sanitized_return_messages() -> None:
    fints, _app = _load_package()
    payload = _response_payload(
        b"HIRMG:2:2+9010::Produkt?+noch?:unbekannt+9210::Weitere hilfreiche Meldung'"
    )
    result = fints.parse_capability_response(payload)
    assert result.outcome == "bank_rejected"
    assert result.failure_category == "bank_response_without_bpd"
    assert result.bpd_version is None
    assert result.holdings_advertised is None
    assert result.return_codes == ("9010", "9210")
    assert [(m.code, m.text) for m in result.return_messages] == [
        ("9010", "Produkt+noch:unbekannt"),
        ("9210", "Weitere hilfreiche Meldung"),
    ]
    assert result.response_sha256 == hashlib.sha256(payload).hexdigest()
    assert result.response_bytes == len(payload)


def test_return_message_redacts_product_id_truncates_text_and_ignores_unknown_segments() -> None:
    fints, _app = _load_package()
    long_text = (f"Registrierung {PRODUCT_ID} noch nicht aktiv " + "X" * 400).encode("ascii")
    payload = _response_payload(
        b"HIRMG:2:2+9010::" + long_text + b"'",
        b"HISALS:3:7+SECRET-UNKNOWN-SEGMENT-TEXT'",
    )
    result = fints.parse_capability_response(payload, redact_tokens=(PRODUCT_ID,))
    assert len(result.return_messages) == 1
    message = result.return_messages[0]
    assert message.code == "9010"
    assert PRODUCT_ID not in message.text
    assert "[REDACTED_PRODUCT_ID]" in message.text
    assert len(message.text) <= fints.MAX_RETURN_MESSAGE_CHARS
    assert message.text.endswith("…")
    serialized = json.dumps(result.as_dict(), sort_keys=True)
    assert "SECRET-UNKNOWN-SEGMENT-TEXT" not in serialized
    assert PRODUCT_ID not in serialized


def test_complete_bpd_may_preserve_bounded_bank_warning_text_without_affecting_capability() -> None:
    fints, _app = _load_package()
    payload = _response_payload(
        b"HIRMG:2:2+0010::Auftrag entgegengenommen'",
        b"HIBPA:3:3+9+280:12030000+DKB'",
        b"HIWPDS:4:1+synthetic'",
    )
    result = fints.parse_capability_response(payload)
    assert result.outcome == "complete"
    assert result.bpd_version == 9
    assert result.holdings_advertised is True
    assert [(m.code, m.text) for m in result.return_messages] == [("0010", "Auftrag entgegengenommen")]


def test_malformed_response_without_bpd_or_return_codes_still_fails_closed() -> None:
    fints, _app = _load_package()
    with pytest.raises(fints.ProtocolError, match="bank-parameter data or return codes"):
        fints.parse_capability_response(_response_payload(b"HISALS:2:7+bounded-but-not-bpd'"))


def test_failed_probe_is_persisted_and_does_not_revert_to_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fints, app = _load_package()
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT_ID)
    assert controller.probe_view().state == "ready"

    def fail(_product_id: str):
        err = fints.ProtocolError("private parse detail that must not persist")
        err.response_sha256 = "a" * 64
        err.response_bytes = 321
        raise err

    monkeypatch.setattr(app, "probe_dkb_bpd", fail)
    first = controller.run_probe()
    assert first.state == "protocol_error"
    reopened = controller.probe_view()
    assert reopened.state == "protocol_error"
    assert reopened.result is not None
    assert reopened.result.outcome == "protocol_error"
    persisted = controller.probe_state_file.read_text(encoding="utf-8")
    persisted_doc = json.loads(persisted)
    assert stat.S_IMODE(controller.probe_state_file.stat().st_mode) == 0o600
    assert persisted_doc["schema_version"] == 2
    assert persisted_doc["response_sha256"] == "a" * 64
    assert persisted_doc["response_bytes"] == 321
    assert persisted_doc["return_messages"] == []
    assert "private parse detail" not in persisted


def test_bank_rejection_persists_codes_and_never_claims_capability(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fints, app = _load_package()
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT_ID)
    rejection = fints.parse_capability_response(
        _response_payload(b"HIRMG:2:2+9010::synthetic-rejection'")
    )
    monkeypatch.setattr(app, "probe_dkb_bpd", lambda _product_id: rejection)
    view = controller.run_probe()
    assert view.state == "bank_rejected"
    assert view.result is not None
    assert view.result.return_codes == ("9010",)
    assert view.result.holdings_advertised is None
    assert [(m.code, m.text) for m in view.result.return_messages] == [("9010", "synthetic-rejection")]
    assert view.result.response_sha256 is not None
    assert view.result.response_bytes is not None
    assert "one possible cause" in view.message
    reopened = controller.probe_view()
    assert reopened.state == "bank_rejected"
    assert reopened.result is not None and reopened.result.return_codes == ("9010",)
    assert reopened.result.return_messages == view.result.return_messages


def test_remote_http_failure_persists_status_without_response_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fints, app = _load_package()
    errors = importlib.import_module(f"{TEST_PACKAGE}.errors")
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT_ID)

    def fail(_product_id: str):
        raise errors.RemoteApiError(503, "private HTTP response detail", operation="fints_bpd_probe")

    monkeypatch.setattr(app, "probe_dkb_bpd", fail)
    view = controller.run_probe()
    assert view.state == "remote_http_error"
    assert view.result is not None and view.result.http_status == 503
    persisted = controller.probe_state_file.read_text(encoding="utf-8")
    persisted_doc = json.loads(persisted)
    assert "private HTTP response detail" not in persisted
    assert persisted_doc["http_status"] == 503
    assert persisted_doc["return_messages"] == []
    assert persisted_doc["response_sha256"] is None
    assert persisted_doc["response_bytes"] is None


class _DummyController:
    csrf_token = "csrf-token"

    def __init__(self) -> None:
        self.configured: str | None = None
        self.probed = False

    def configure_product_id(self, value: str) -> None:
        self.configured = value

    def run_probe(self):
        self.probed = True
        return None


def _post_and_location(app, controller: _DummyController, path: str, fields: dict[str, str]) -> tuple[int, str | None]:
    server = app.DKBIngressServer(
        ("127.0.0.1", 0),
        state=object(),
        controller=controller,
        api_token="test-token",
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=False,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = urlencode(fields)
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        connection.request(
            "POST",
            path,
            body=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(body.encode("utf-8"))),
            },
        )
        response = connection.getresponse()
        response.read()
        return response.status, response.getheader("Location")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_ingress_post_redirects_are_relative_and_cannot_escape_to_ha_root() -> None:
    _fints, app = _load_package()
    controller = _DummyController()
    status, location = _post_and_location(
        app,
        controller,
        "/configure-product",
        {"csrf": controller.csrf_token, "product_id": PRODUCT_ID},
    )
    assert status == 303
    assert location == "./"
    assert controller.configured == PRODUCT_ID

    status, location = _post_and_location(
        app,
        controller,
        "/probe",
        {"csrf": controller.csrf_token},
    )
    assert status == 303
    assert location == "./"
    assert controller.probed is True

    source = (PACKAGE / "dkb_app.py").read_text(encoding="utf-8")
    assert 'self._redirect("/")' not in source
    assert 'self._redirect("/?error=invalid_product_id")' not in source


def test_ingress_ui_requires_exact_length_and_presents_failure_evidence() -> None:
    source = (PACKAGE / "dkb_app.py").read_text(encoding="utf-8")
    assert 'minlength=\\"25\\" maxlength=\\"25\\" pattern=\\"[A-Za-z0-9]{{25}}\\"' in source
    assert "complete 25-character registration number" in source
    assert "Bounded return codes" in source
    assert "Sanitized bank return messages" in source
    assert "Decoded response SHA-256" in source
    assert "arbitrary segment payload and the raw FinTS response are discarded after fingerprinting" in source
    assert 'holdings = "not available"' in source
    assert "newly issued product registration that has not propagated yet is one possible cause" in source


def test_schema1_success_evidence_remains_loadable(tmp_path: Path) -> None:
    _fints, app = _load_package()
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT_ID)
    app.save_json_state(
        controller.probe_state_file,
        {
            "schema_version": 1,
            "probed_at": "2026-08-16T12:00:00+00:00",
            "bpd_version": 9,
            "parameter_segments": ["HIWPDS"],
            "return_codes": ["0010"],
            "holdings_advertised": True,
        },
    )
    view = controller.probe_view()
    assert view.state == "complete"
    assert view.result is not None
    assert view.result.outcome == "complete"
    assert view.result.holdings_advertised is True
