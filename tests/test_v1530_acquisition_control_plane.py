"""v1.55.1 provider-neutral acquisition control-plane contracts."""

from pathlib import Path
import json
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def test_v1530_versions_and_health_schema_are_aligned() -> None:
    assert json.loads((COMPONENT / "manifest.json").read_text())["version"] == "1.61.2"
    assert 'VERSION: Final = "1.61.2"' in (COMPONENT / "const.py").read_text()
    assert '__version__ = "1.61.2"' in (ROOT / "gateway/src/portfolio_architect_gateway/__init__.py").read_text()
    for app in (
        "portfolio_architect_gateway_comdirect",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
        "portfolio_architect_gateway_import",
    ):
        config = yaml.safe_load((ROOT / "home_assistant_app" / app / "config.yaml").read_text())
        assert config["version"] == "1.61.2"
    rest = (COMPONENT / "rest_client.py").read_text()
    server = (ROOT / "gateway/src/portfolio_architect_gateway/server.py").read_text()
    assert 'HEALTH_V9_MEDIA_TYPE' in rest
    assert '"requested_health_schema_version": 9' in rest
    assert 'HEALTH_V9_MEDIA_TYPE' in server
    assert '"health_schema_version": min(version, 9)' in server


def test_control_plane_is_provider_neutral_read_only_and_no_fallback() -> None:
    common = (ROOT / "gateway/src/portfolio_architect_gateway/acquisition_control.py").read_text()
    server = (ROOT / "gateway/src/portfolio_architect_gateway/server.py").read_text()
    client = (COMPONENT / "rest_client.py").read_text()
    sensor = (COMPONENT / "sensor.py").read_text()
    assert 'FALLBACK_NONE: Final = "none"' in common
    assert 'control_from_provider(self._client)' in server
    assert '"acquisition_methods"' in client
    assert '"active_acquisition_method"' in client
    assert '"fallback_policy"' in client
    assert '"acquisition_controls"' in sensor
    assert "set_acquisition" not in client


def test_official_provider_method_inventories_are_explicit() -> None:
    dkb = (ROOT / "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway/dkb_csv.py").read_text()
    tr = (ROOT / "home_assistant_app/portfolio_architect_gateway_trade_republic/src/portfolio_architect_gateway/trade_republic_statement.py").read_text()
    generic = (ROOT / "home_assistant_app/portfolio_architect_gateway_import/src/portfolio_architect_gateway/generic_csv.py").read_text()
    assert 'AcquisitionMethod("csv", METHOD_READY, True, True)' in dkb
    assert 'AcquisitionMethod("fints", METHOD_RESEARCH_ONLY, False, False)' in dkb
    assert 'AcquisitionMethod("pdf", METHOD_READY, True, True)' in tr
    assert 'AcquisitionMethod("live_api", METHOD_UNAVAILABLE, False, False)' in tr
    assert 'single_method_control("csv", cash=False)' in generic


def test_comdirect_switch_is_gateway_local_atomic_and_requires_complete_csv_candidate() -> None:
    acquisition = (ROOT / "gateway/src/portfolio_architect_gateway/acquisition.py").read_text()
    app = (ROOT / "gateway/src/portfolio_architect_gateway/app.py").read_text()
    assert "def activate_mode" in acquisition
    assert "with self._lock:" in acquisition
    assert "both holdings and cash evidence" in acquisition
    assert '"last_method_change_reason": CHANGE_REASON_OPERATOR' in acquisition
    assert "self.acquisition.activate_mode" in app
    assert "Portfolio Architect remains a read-only consumer" in app
    assert "never calls the API as a fallback" in app
    assert "PENDING_STATE_FILE_NAME" in acquisition
    assert "_recover_interrupted_activation" in acquisition
    assert "previous_state_persisted" in acquisition
    assert "acquisition_error=activation_failed" in app


def test_v1530_does_not_advance_dkb_authenticated_fints_or_money_movement() -> None:
    dkb = (ROOT / "home_assistant_app/portfolio_architect_gateway_dkb/src/portfolio_architect_gateway/dkb_app.py").read_text()
    release = (ROOT / "docs/RELEASE-NOTES.md").read_text()
    assert "EXPERIMENTAL · RESEARCH ONLY" in dkb
    lowered = release.lower()
    assert "authenticated dkb fints" in lowered
    assert "remains disabled" in lowered
    assert "no trading" in lowered
    assert "no dashboard yaml replacement" in lowered
