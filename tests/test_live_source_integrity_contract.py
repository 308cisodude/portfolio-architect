"""Current live-source integrity, resilience, and continuity contracts."""

from pathlib import Path
import json
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway"


def test_component_versions_are_compatible() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    const = (COMPONENT / "const.py").read_text()
    engine = (COMPONENT / "engine" / "__init__.py").read_text()
    app = yaml.safe_load((APP / "config.yaml").read_text())
    gateway = (APP / "src" / "portfolio_architect_gateway" / "__init__.py").read_text()
    assert manifest["version"] == "1.48.2"
    assert 'VERSION: Final = "1.48.2"' in const
    assert '__version__ = "1.48.2"' in engine
    assert app["version"] == "1.48.2"
    assert '__version__ = "1.48.2"' in gateway
    assert app["stage"] == "stable"


def test_integrity_headers_and_versioned_health_are_implemented() -> None:
    server = (APP / "src" / "portfolio_architect_gateway" / "server.py").read_text()
    transport = (COMPONENT / "rest_client.py").read_text()
    coordinator = (COMPONENT / "coordinator.py").read_text()
    assert "X-Portfolio-Snapshot-SHA256" in server
    assert "X-Portfolio-Position-Count" in server
    assert "HEALTH_V3_MEDIA_TYPE" in server
    assert "HEALTH_V4_MEDIA_TYPE" in server
    assert "health_document(version=7" in (
        APP / "src" / "portfolio_architect_gateway" / "app.py"
    ).read_text()
    assert "hashlib.sha256(body).hexdigest()" in transport
    assert "snapshot SHA-256 header does not match" in transport
    assert "position-count header does not match" in transport
    assert "attempted to replace the accepted snapshot" in coordinator
    assert "Gateway health fingerprint does not match" in coordinator


def test_integrity_entities_translations_and_dashboard_are_present() -> None:
    sensor = (COMPONENT / "sensor.py").read_text()
    binary = (COMPONENT / "binary_sensor.py").read_text()
    diagnostics = (COMPONENT / "diagnostics.py").read_text()
    assert "PortfolioGatewaySnapshotGeneratedSensor" in sensor
    assert "PortfolioGatewaySnapshotIntegrityVerified" in binary
    assert '"rest_snapshot_integrity"' in diagnostics
    for language in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text()
        )
        assert translations["entity"]["sensor"]["gateway_snapshot_generated"]["name"]
        assert translations["entity"]["binary_sensor"][
            "gateway_snapshot_integrity_verified"
        ]["name"]
        runtime = (ROOT / "dashboard" / language / "runtime-health.yaml").read_text()
        assert "gateway_snapshot_generated" in runtime
        assert "gateway_snapshot_integrity_verified" in runtime
        assert "gateway_operating_mode" in runtime
        assert "gateway_snapshot_age" in runtime
        assert "gateway_using_last_known_good_snapshot" in runtime


def test_last_known_good_health_entities_are_present() -> None:
    sensor = (COMPONENT / "sensor.py").read_text()
    binary = (COMPONENT / "binary_sensor.py").read_text()
    diagnostics = (COMPONENT / "diagnostics.py").read_text()
    transport = (COMPONENT / "rest_client.py").read_text()
    assert "PortfolioGatewayOperatingModeSensor" in sensor
    assert "PortfolioGatewaySnapshotAgeSensor" in sensor
    assert "PortfolioGatewaySnapshotExpiresInSensor" in sensor
    assert "PortfolioGatewayConsecutiveRefreshFailuresSensor" in sensor
    assert "PortfolioGatewayUsingLastKnownGoodSnapshot" in binary
    assert '"operating_mode"' in diagnostics
    assert '"consecutive_refresh_failures"' in diagnostics
    assert '"requested_health_schema_version": 7' in transport
