"""Historical v1.45.1 stale-migration guarantees retained after bridge retirement."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
SERVER = ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "server.py"


def test_expired_health_schema_consistency_fix_remains_in_common_gateway() -> None:
    source = SERVER.read_text(encoding="utf-8")
    health = source.split("def health_document", 1)[1].split("def snapshot_view", 1)[0]
    assert '"snapshot_available": view is not None' in health
    assert '"snapshot_sha256": view.sha256 if view is not None else None' in health
    assert 'view.position_count if view is not None else None' in health
    assert 'snapshot_age_seconds = None' in health


def test_temporary_v1451_migration_endpoint_is_retired_in_v1460() -> None:
    server = SERVER.read_text(encoding="utf-8")
    rest = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    dkb = (
        ROOT
        / "home_assistant_app"
        / "portfolio_architect_gateway_dkb"
        / "src"
        / "portfolio_architect_gateway"
        / "dkb_app.py"
    ).read_text(encoding="utf-8")
    assert "migration-snapshot" not in server
    assert "migration_snapshot_enabled" not in server
    assert "MIGRATION_SNAPSHOT_PATH" not in rest
    assert "migration_snapshot_enabled" not in dkb


def test_historical_v1451_upgrade_guide_remains_available() -> None:
    guide = ROOT / "docs" / "UPGRADE-1.45.1.md"
    assert guide.is_file()
    text = guide.read_text(encoding="utf-8")
    assert "Maximum cached snapshot age" in text
    assert "migration endpoint" in text
