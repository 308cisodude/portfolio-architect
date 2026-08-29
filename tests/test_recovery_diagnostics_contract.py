"""v1.10 classified recovery diagnostics and repair contracts."""

from pathlib import Path
import json

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_comdirect"


def test_current_health_schema_is_requested_and_served() -> None:
    server = (APP / "src" / "portfolio_architect_gateway" / "server.py").read_text()
    client = (COMPONENT / "rest_client.py").read_text()
    assert "HEALTH_V6_MEDIA_TYPE" in server
    assert "HEALTH_V5_MEDIA_TYPE" in server
    assert 'health_document(version=8)' in (APP / "src" / "portfolio_architect_gateway" / "app.py").read_text()
    assert '"requested_health_schema_version": 9' in client
    for field in (
        "last_refresh_failure_at",
        "last_refresh_failure_class",
        "recommended_action",
        "retry_after_seconds",
    ):
        assert field in server
        assert field in client


def test_attention_entities_and_repair_issues_are_present() -> None:
    sensor = (COMPONENT / "sensor.py").read_text()
    binary = (COMPONENT / "binary_sensor.py").read_text()
    coordinator = (COMPONENT / "coordinator.py").read_text()
    diagnostics = (COMPONENT / "diagnostics.py").read_text()
    for class_name in (
        "PortfolioGatewayAttentionReasonSensor",
        "PortfolioGatewayRecommendedActionSensor",
        "PortfolioGatewayLastRefreshFailureSensor",
    ):
        assert class_name in sensor
    for class_name in (
        "PortfolioGatewayAttentionRequired",
        "PortfolioGatewayRefreshOverdue",
    ):
        assert class_name in binary
    for issue_key in (
        "gateway_repeated_refresh_failures",
        "gateway_snapshot_unavailable",
        "gateway_refresh_overdue",
        "gateway_snapshot_integrity_failure",
    ):
        assert issue_key in coordinator
    for field in (
        "gateway_recovery",
        "attention_required",
        "attention_reason",
        "recommended_action",
        "refresh_overdue",
        "last_refresh_failure_class",
    ):
        assert f'"{field}"' in diagnostics


def test_recovery_translations_icons_and_dashboard_are_present() -> None:
    icons = json.loads((COMPONENT / "icons.json").read_text())
    assert "gateway_attention_reason" in icons["entity"]["sensor"]
    assert "gateway_attention_required" in icons["entity"]["binary_sensor"]
    for language in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text()
        )
        assert translations["entity"]["sensor"]["gateway_attention_reason"]["name"]
        assert translations["entity"]["sensor"]["gateway_recommended_action"]["name"]
        assert translations["entity"]["binary_sensor"]["gateway_attention_required"]["name"]
        assert translations["issues"]["gateway_repeated_refresh_failures"]["title"]
        runtime = (ROOT / "dashboard" / language / "runtime-health.yaml").read_text()
        assert "gateway_attention_required" in runtime
        assert "attention_reason" in runtime
        assert "recommended_action" in runtime
        assert "sensor.portfolio_architect_gateway_attention_reason" not in runtime
        assert "sensor.portfolio_architect_gateway_recommended_action" not in runtime
