"""v1.9 refresh scheduling and protected manual-operation contracts."""

from pathlib import Path
import json

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_comdirect"


def test_health_schema_four_and_fixed_cadence_are_implemented() -> None:
    server = (APP / "src" / "portfolio_architect_gateway" / "server.py").read_text()
    transport = (COMPONENT / "rest_client.py").read_text()
    assert "HEALTH_V4_MEDIA_TYPE" in server
    assert 'refresh(trigger="startup")' in server
    assert 'refresh(trigger="scheduled")' in server
    assert "next_deadline += interval_seconds" in server
    assert "request_manual_refresh" in server
    assert "_refresh_execution_lock" in server
    assert '"requested_health_schema_version": 8' in transport
    for field in (
        "refresh_in_progress",
        "last_refresh_duration_ms",
        "last_refresh_trigger",
        "next_refresh_due_at",
        "manual_refresh_min_interval_seconds",
    ):
        assert field in server
        assert field in transport


def test_manual_refresh_stays_inside_protected_ingress() -> None:
    app = (APP / "src" / "portfolio_architect_gateway" / "app.py").read_text()
    server = (APP / "src" / "portfolio_architect_gateway" / "server.py").read_text()
    config = (APP / "config.yaml").read_text()
    assert "if path not in {" in app
    for protected_path in (
        "/bootstrap",
        "/refresh",
        "/discover-accounts",
        "/select-account",
        "/clear-account",
    ):
        assert f'"{protected_path}"' in app
    assert "secrets.compare_digest" in app
    assert 'set(values) != {"csrf"}' in app
    assert "HTTPStatus.TOO_MANY_REQUESTS" in app
    assert "Refresh portfolio now" in app
    assert "panel_admin: true" in config
    assert "def do_POST" in server
    assert "self._method_not_allowed()" in server
    assert 'self.send_header("Allow", "GET")' in server


def test_refresh_entities_translations_and_dashboard_are_present() -> None:
    sensor = (COMPONENT / "sensor.py").read_text()
    binary = (COMPONENT / "binary_sensor.py").read_text()
    diagnostics = (COMPONENT / "diagnostics.py").read_text()
    for class_name in (
        "PortfolioGatewayNextRefreshSensor",
        "PortfolioGatewayLastRefreshDurationSensor",
        "PortfolioGatewayLastRefreshTriggerSensor",
    ):
        assert class_name in sensor
    assert "PortfolioGatewayRefreshInProgress" in binary
    for key in (
        "refresh_in_progress",
        "last_refresh_duration_ms",
        "last_refresh_trigger",
        "next_refresh_due_at",
        "manual_refresh_min_interval_seconds",
    ):
        assert f'"{key}"' in diagnostics
    for language in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text()
        )
        sensors = translations["entity"]["sensor"]
        binary_sensors = translations["entity"]["binary_sensor"]
        assert sensors["gateway_next_refresh"]["name"]
        assert sensors["gateway_last_refresh_duration"]["name"]
        assert sensors["gateway_last_refresh_trigger"]["name"]
        assert binary_sensors["gateway_refresh_in_progress"]["name"]
        runtime = (ROOT / "dashboard" / language / "runtime-health.yaml").read_text()
        assert "gateway_refresh_schedule" in runtime
        assert "gateway_next_refresh" in runtime
        assert "style: short" in runtime
        assert "gateway_last_refresh_duration" in runtime
        assert "gateway_last_refresh_trigger" in runtime
        assert "gateway_refresh_in_progress" in runtime
