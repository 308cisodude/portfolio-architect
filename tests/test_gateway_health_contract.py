"""Gateway health, stable App, repair, and identifier UX contracts."""
from pathlib import Path
import json
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway"


def test_gateway_app_is_stable_and_versioned() -> None:
    config = yaml.safe_load((APP / "config.yaml").read_text(encoding="utf-8"))
    assert config["version"] == "1.36.1"
    assert config["stage"] == "stable"


def test_health_contract_is_bounded_authenticated_and_same_origin() -> None:
    transport = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    server = (APP / "src" / "portfolio_architect_gateway" / "server.py").read_text(encoding="utf-8")
    assert "MAX_REST_HEALTH_RESPONSE_BYTES: Final = 16 * 1024" in transport
    assert '"Authorization": f"Bearer {config.api_token}"' in transport
    assert 'SplitResult(parsed.scheme, parsed.netloc, "/healthz"' in transport
    assert "allow_redirects=False" in transport
    assert '"gateway_version": __version__' in server
    assert "async_fetch_gateway_health" in coordinator
    assert "async_fetch_gateway_health" in flow
    assert "Local gateway is not ready for live portfolio use" in flow
    assert "gateway_reauthentication_required" in coordinator
    assert "ir.async_create_issue" in coordinator
    assert "ir.async_delete_issue" in coordinator


def test_health_and_identifier_translations_exist() -> None:
    for language in ("en", "de"):
        data = json.loads((COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8"))
        sensors = data["entity"]["sensor"]
        binary = data["entity"]["binary_sensor"]
        assert sensors["instrument_isin"]["name"]
        assert sensors["gateway_status"]["name"]
        assert sensors["gateway_last_refresh"]["name"]
        assert sensors["gateway_last_error"]["name"]
        assert sensors["gateway_operating_mode"]["name"]
        assert sensors["gateway_snapshot_age"]["name"]
        assert sensors["gateway_snapshot_expires_in"]["name"]
        assert sensors["gateway_consecutive_refresh_failures"]["name"]
        assert binary["gateway_reauthentication_required"]["name"]
        assert binary["gateway_using_last_known_good_snapshot"]["name"]
        assert data["issues"]["gateway_reauthentication_required"]["title"]
