"""Regression coverage for the v1.33.0 DKB FinTS capability-probe milestone."""

from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

import pytest
import yaml

ROOT = Path(__file__).parents[1]
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb"
PACKAGE = APP / "src" / "portfolio_architect_gateway"
TEST_PACKAGE = "portfolio_architect_gateway_dkb_v1280_test"


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


def _segment_types(payload: bytes) -> tuple[str, ...]:
    return tuple(
        segment.split(b":", 1)[0].decode("ascii")
        for segment in payload.split(b"'")
        if segment
    )


def _response_payload(*segments: bytes) -> bytes:
    payload = b"".join((b"HNHBK:1:3+000000000000+300+dialog+1'", *segments, b"HNHBS:99:1+1'"))
    size = f"{len(payload):012d}".encode()
    return payload.replace(b"000000000000", size, 1)


def test_anonymous_probe_request_contains_only_dialog_initialization_segments() -> None:
    fints, _app = _load_package()
    product_id = "9FA6681DEC0CF3046BFC2F8A6"
    payload = fints.build_anonymous_bpd_request(product_id)
    assert _segment_types(payload) == ("HNHBK", "HKIDN", "HKVVB", "HNHBS")
    declared_size = int(payload.split(b"+", 2)[1])
    assert declared_size == len(payload)
    assert f"+280:{fints.DKB_BANK_CODE}+{fints.ANONYMOUS_CUSTOMER_ID}+0+0'".encode() in payload
    assert f"+1+{product_id}+{fints.FINTS_PRODUCT_VERSION}'".encode() in payload
    for forbidden in (
        b"HKWPD",  # holdings
        b"HKWPO",  # securities orders
        b"HKSAL",  # balances
        b"HKKAZ",  # transactions
        b"HKCCS",  # transfers
        b"HKDSE",  # debits
    ):
        assert forbidden not in payload


def test_product_registration_number_is_strictly_bounded_for_wire_use() -> None:
    fints, _app = _load_package()
    product_id = "9FA6681DEC0CF3046BFC2F8A6"
    assert fints.normalise_product_id(f" {product_id} ") == product_id
    for value in ("", "A" * 24, "A" * 26, "ABC+123", "ABC?123", "ABC'123", "ABC:123"):
        with pytest.raises(ValueError):
            fints.normalise_product_id(value)


def test_synthetic_bpd_response_reduces_to_sanitized_capability_metadata() -> None:
    fints, _app = _load_package()
    payload = _response_payload(
        b"HIRMG:2:2+0010::accepted+3920::more'",
        b"HIBPA:3:3+42+280:12030000+DKB+1+2:300'",
        b"HISALS:4:7+private-marker-that-must-not-survive'",
        b"HIWPDS:5:6+private-holdings-parameter-payload'",
    )
    result = fints.parse_capability_response(payload)
    assert result.bpd_version == 42
    assert result.parameter_segments == ("HISALS", "HIWPDS")
    assert result.return_codes == ("0010", "3920")
    assert result.holdings_advertised is True
    serialized = json.dumps(result.as_dict(), sort_keys=True)
    assert "private-marker" not in serialized
    assert "private-holdings" not in serialized


def test_absent_holdings_parameter_remains_fail_closed_evidence() -> None:
    fints, _app = _load_package()
    payload = _response_payload(
        b"HIBPA:2:3+7+280:12030000+DKB+1+2:300'",
        b"HISALS:3:7+payload'",
    )
    result = fints.parse_capability_response(payload)
    assert result.holdings_advertised is False
    assert "HIWPDS" not in result.parameter_segments


def test_parser_rejects_unterminated_or_malformed_fints_messages() -> None:
    fints, _app = _load_package()
    for payload in (
        b"HNHBK:1:3+000000000060+300+dialog+1'HIBPA:2:3+1+payload",  # missing closing segment
        b"HIBPA:1:3+1'HNHBS:2:1+1'",  # no header envelope
        b"HNHBK:1:3+000000000055+300+dialog+1''HNHBS:2:1+1'",  # empty segment
        b"HNHBK:1:3+000000000065+300+dialog+1'@9@tiny'HNHBS:2:1+1'",  # binary field overrun
        _response_payload(b"HISALS:2:7+payload'"),  # no bank parameters or return codes
    ):
        with pytest.raises(fints.ProtocolError):
            fints.parse_capability_response(payload)


def test_probe_transport_is_fixed_verified_https_without_proxy_or_redirect_surface() -> None:
    source = (PACKAGE / "dkb_fints.py").read_text(encoding="utf-8")
    assert 'DKB_FINTS_HOST: Final = "fints.dkb.de"' in source
    assert 'DKB_FINTS_PATH: Final = "/fints"' in source
    assert "ssl.create_default_context()" in source
    assert "http.client.HTTPSConnection(" in source
    assert 'connection.request(\n            "POST",\n            DKB_FINTS_PATH' in source
    for forbidden in (
        "requests.",
        "urllib.request",
        "ProxyHandler",
        "CERT_NONE",
        "check_hostname = False",
        "allow_redirects",
        "python-fints",
    ):
        assert forbidden not in source


def test_product_registration_and_probe_result_are_private_and_sanitized(tmp_path: Path) -> None:
    _fints, app = _load_package()
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id("9FA6681DEC0CF3046BFC2F8A6")
    assert controller.product_id() == "9FA6681DEC0CF3046BFC2F8A6"
    assert stat.S_IMODE(controller.product_id_file.stat().st_mode) == 0o600

    result = {
        "schema_version": 1,
        "probed_at": "2026-08-16T12:00:00+00:00",
        "bpd_version": 9,
        "parameter_segments": ["HIWPDS"],
        "return_codes": ["0010"],
        "holdings_advertised": True,
    }
    app.save_json_state(controller.probe_state_file, result)
    view = controller.probe_view()
    assert view.result is not None and view.result.holdings_advertised is True
    serialized = view.result.as_dict()
    assert set(serialized) == {
        "schema_version",
        "probed_at",
        "outcome",
        "failure_category",
        "http_status",
        "bpd_version",
        "parameter_segments",
        "return_codes",
        "return_messages",
        "response_sha256",
        "response_bytes",
        "holdings_advertised",
    }
    # Legacy schema-1 success evidence gains no invented diagnostic text or raw-response metadata.
    assert serialized["return_messages"] == []
    assert serialized["response_sha256"] is None
    assert serialized["response_bytes"] is None

    controller.configure_product_id("0123456789ABCDEFGHIJKLMNO")
    assert controller.product_id() == "0123456789ABCDEFGHIJKLMNO"
    assert not controller.probe_state_file.exists()
    assert controller.probe_view().state == "ready"


def test_dkb_app_remains_manual_experimental_and_without_live_acquisition() -> None:
    config = yaml.safe_load((APP / "config.yaml").read_text(encoding="utf-8"))
    assert config["version"] == "1.33.0"
    assert config["stage"] == "experimental"
    assert config["boot"] == "manual_only"
    assert config["environment"]["PA_PROVIDER_ID"] == "dkb"
    assert config["ports"]["8787/tcp"] is None
    assert config["host_network"] is False
    assert config["hassio_api"] is False
    assert config["homeassistant_api"] is False
    assert config["docker_api"] is False

    source = (PACKAGE / "dkb_app.py").read_text(encoding="utf-8")
    assert "PendingProvider(provider_id)" in source
    assert 'state.refresh(trigger="startup")' in source
    assert "run_refresh_loop" not in source
    assert "fetch_snapshot(" not in source
    assert "probe_dkb_bpd(product_id)" in source
    assert 'self.send_header("Allow", "GET, POST")' in source
    for method in ("do_PUT", "do_PATCH", "do_DELETE", "do_HEAD", "do_OPTIONS"):
        assert method in source


def test_dkb_ingress_has_no_bank_credential_or_transaction_form_fields() -> None:
    source = (PACKAGE / "dkb_app.py").read_text(encoding="utf-8")
    assert 'name=\\"product_id\\"' in source
    assert 'name=\\"csrf\\"' in source
    for forbidden in (
        'name=\\"username\\"',
        'name=\\"login\\"',
        'name=\\"pin\\"',
        'name=\\"tan\\"',
        'name=\\"password\\"',
        "submit_order",
        "place_order",
        "create_transfer",
        "transaction_history",
    ):
        assert forbidden not in source


def test_v1280_documentation_preserves_registration_and_user_capability_gates() -> None:
    upgrade = (ROOT / "docs" / "UPGRADE-1.33.0.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    for source in (upgrade, roadmap):
        assert "FinTS" in source
        assert "HIWPDS" in source
        assert "registration" in source.casefold()
        assert "no holdings" in source.casefold() or "does not yet enable live" in source.casefold()
    assert "authenticated user" in upgrade.casefold()
    assert "dkb_csv" in roadmap
