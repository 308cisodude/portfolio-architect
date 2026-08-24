"""v1.50.0 source-architecture UX and DKB probe observability contracts."""
from __future__ import annotations

import ast
from datetime import datetime
import importlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

import pytest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
FLOW = COMPONENT / "config_flow.py"
DKB_APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb"
DKB_PACKAGE = DKB_APP / "src" / "portfolio_architect_gateway"
TEST_PACKAGE = "portfolio_architect_gateway_dkb_v1500_test"
PRODUCT_ID = "9FA6681DEC0CF3046BFC2F8A6"


def _options_method(name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(FLOW.read_text(encoding="utf-8"))
    flow = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PortfolioArchitectOptionsFlow"
    )
    return next(
        node
        for node in flow.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    )


def _literal_menu_options(name: str) -> list[str]:
    method = _options_method(name)
    for node in ast.walk(method):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "async_show_menu"
        ):
            continue
        keyword = next((item for item in node.keywords if item.arg == "menu_options"), None)
        if keyword is not None and isinstance(keyword.value, ast.List):
            return [
                item.value
                for item in keyword.value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
    return []


def test_sources_menu_models_one_primary_and_optional_supplements() -> None:
    assert _literal_menu_options("async_step_sources") == [
        "primary_rest_gateway",
        "rest_gateways",
    ]
    source = FLOW.read_text(encoding="utf-8")
    rest_block = source.split("async def async_step_rest_gateways", 1)[1].split(
        "async def async_step_edit_rest_gateway", 1
    )[0]
    assert 'menu = ["add_rest_gateway"]' in rest_block
    assert 'menu.extend(["edit_rest_gateway", "remove_rest_gateway"])' in rest_block


def test_primary_source_edit_is_identity_preserving_and_updates_entry_data() -> None:
    source = FLOW.read_text(encoding="utf-8")
    block = source.split("async def async_step_primary_rest_gateway", 1)[1].split(
        "async def async_step_rest_gateways", 1
    )[0]
    assert 'candidate.endpoint_url != existing.endpoint_url' in block
    assert 'health.provider_id != current_provider_id' in block
    assert 'any(item.provider_id == health.provider_id for item in supplemental)' in block
    assert 'health.snapshot_sha256 != result.snapshot_sha256' in block
    assert 'self.hass.config_entries.async_update_entry(self.config_entry, data=data)' in block
    assert 'data[CONF_REST_API_TOKEN] = candidate.api_token' in block
    assert 'data[CONF_REST_ENDPOINT_URL] = candidate.endpoint_url' in block


def test_supplemental_gateway_edit_keeps_provider_identity_immutable() -> None:
    source = FLOW.read_text(encoding="utf-8")
    block = source.split("async def async_step_edit_rest_gateway_details", 1)[1].split(
        "async def async_step_add_rest_gateway", 1
    )[0]
    assert 'health.provider_id != existing.provider_id' in block
    assert 'provider_id=existing.provider_id' in block
    assert 'configured.as_storage_dict()' in block
    assert 'item.provider_id == existing.provider_id' in block
    assert 'health.snapshot_sha256 != result.snapshot_sha256' in block
    assert 'candidate.endpoint_url == primary.endpoint_url' in block


def test_source_ux_has_complete_bilingual_primary_and_add_edit_remove_labels() -> None:
    for language, editing_marker in (("en", "**Editing:**"), ("de", "**Bearbeitet:**")):
        data = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        steps = data["options"]["step"]
        assert list(steps["sources"]["menu_options"]) == [
            "primary_rest_gateway",
            "rest_gateways",
        ]
        assert list(steps["rest_gateways"]["menu_options"]) == [
            "add_rest_gateway",
            "edit_rest_gateway",
            "remove_rest_gateway",
        ]
        assert "{provider}" in steps["primary_rest_gateway"]["description"]
        assert "{endpoint}" in steps["primary_rest_gateway"]["description"]
        details = steps["edit_rest_gateway_details"]["description"]
        assert details.startswith(editing_marker)
        for placeholder in ("{provider}", "{provider_id}", "{endpoint}"):
            assert placeholder in details


def _load_dkb_package():
    if TEST_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            TEST_PACKAGE,
            DKB_PACKAGE / "__init__.py",
            submodule_search_locations=[str(DKB_PACKAGE)],
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[TEST_PACKAGE] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f"{TEST_PACKAGE}.dkb_fints"), importlib.import_module(
        f"{TEST_PACKAGE}.dkb_app"
    )


def test_dkb_probe_persists_server_side_dispatch_timestamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fints, app = _load_dkb_package()
    controller = app.DKBProbeController(tmp_path)
    controller.configure_product_id(PRODUCT_ID)
    rejection = fints.CapabilityProbeResult(
        probed_at="2026-08-24T16:10:32+00:00",
        bpd_version=None,
        parameter_segments=(),
        return_codes=("9800", "9078", "3079"),
        holdings_advertised=None,
        outcome="bank_rejected",
        failure_category="bank_response_without_bpd",
        response_sha256="a" * 64,
        response_bytes=236,
    )
    monkeypatch.setattr(app, "probe_dkb_bpd", lambda _product_id: rejection)
    before = datetime.now().astimezone()
    controller.run_probe()
    after = datetime.now().astimezone()

    sent_at = controller.last_probe_sent_at()
    assert sent_at is not None
    parsed = datetime.fromisoformat(sent_at)
    assert parsed.tzinfo is not None and parsed.utcoffset() is not None
    assert before.timestamp() - 1 <= parsed.timestamp() <= after.timestamp() + 1
    assert stat.S_IMODE(controller.probe_sent_at_file.stat().st_mode) == 0o600

    class DummyState:
        def health_document(self, *, version: int):
            assert version == 7
            return {"health_schema_version": 7}

    status = controller.status_document(DummyState())
    assert status["fints"]["probe_sent_at"] == sent_at

    controller.configure_product_id("A" * 25)
    assert controller.last_probe_sent_at() is None
    assert not controller.probe_sent_at_file.exists()


def test_dkb_probe_ingress_displays_persisted_last_sent_timestamp_without_changing_gate() -> None:
    source = (DKB_PACKAGE / "dkb_app.py").read_text(encoding="utf-8")
    assert 'PROBE_SENT_AT_FILE_NAME: Final = "dkb-fints-probe-sent-at"' in source
    assert "Last probe sent:" in source
    assert 'ZoneInfo("Europe/Berlin")' in source
    assert 'strftime("%Y-%m-%d %H:%M:%S %Z")' in source
    assert "Server-side dispatch timestamp" in source
    assert '"probe_sent_at": self.last_probe_sent_at()' in source
    assert "Authenticated FinTS acquisition is not enabled" in source
    assert "cannot replace or fall back from CSV evidence" in source
