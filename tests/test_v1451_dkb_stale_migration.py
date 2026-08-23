"""Regression coverage for v1.45.1 stale legacy-DKB migration."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
MASTER_SERVER = ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "server.py"
DKB_APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb"
COMDIRECT_APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway"
TR_APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_trade_republic"


def test_migration_uses_bounded_stale_snapshot_only_when_normal_snapshot_is_unavailable() -> None:
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    step = flow.split("async def async_step_hassio_migrate_dkb_csv_confirm", 1)[1].split(
        "async def async_step_hassio_add_supplemental_confirm", 1
    )[0]
    assert "if health.snapshot_available:" in step
    assert "await async_fetch_rest_snapshot(self.hass, candidate)" in step
    assert "health.operating_mode != \"unavailable\"" in step
    assert "await async_fetch_gateway_migration_snapshot(" in step
    assert step.index("if health.snapshot_available:") < step.index(
        "await async_fetch_gateway_migration_snapshot("
    )
    assert "dkb_gateway_migration_snapshot_unavailable" in step
    assert "options.pop(CONF_SUPPLEMENTAL_DKB_CSV_PATHS, None)" in step
    assert step.index("_dkb_migration_snapshots_match") < step.index(
        "options.pop(CONF_SUPPLEMENTAL_DKB_CSV_PATHS, None)"
    )


def test_migration_fetch_is_same_origin_pinned_https_and_integrity_checked() -> None:
    rest = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    assert 'MIGRATION_SNAPSHOT_PATH: Final = "/api/v1/migration-snapshot"' in rest
    block = rest.split("async def async_fetch_gateway_migration_snapshot", 1)[1].split(
        "async def _async_fetch_snapshot_url", 1
    )[0]
    assert "urlsplit(config.endpoint_url)" in block
    assert "SplitResult(parsed.scheme, parsed.netloc, MIGRATION_SNAPSHOT_PATH" in block
    shared = rest.split("async def _async_fetch_snapshot_url", 1)[1].split(
        "async def _async_process_response", 1
    )[0]
    assert "async_validate_local_rest_endpoint" in shared
    assert "_rest_ssl_context" in shared
    assert "_async_pinned_local_session" in shared
    assert '"Authorization": f"Bearer {config.api_token}"' in shared
    assert "allow_redirects=False" in shared
    assert "PortfolioRestMigrationSnapshotUnavailableError" in shared


def test_only_dkb_app_enables_the_migration_snapshot_endpoint() -> None:
    server = MASTER_SERVER.read_text(encoding="utf-8")
    assert 'MIGRATION_SNAPSHOT_PATH = "/api/v1/migration-snapshot"' in server
    assert "migration_snapshot_enabled: bool = False" in server
    assert "ignore_max_age=ignore_max_age" in server
    assert "self._serve_portfolio(ignore_max_age=True)" in server

    dkb = (DKB_APP / "src" / "portfolio_architect_gateway" / "dkb_app.py").read_text(
        encoding="utf-8"
    )
    assert "migration_snapshot_enabled=True" in dkb
    for app in (COMDIRECT_APP, TR_APP):
        provider_sources = "\n".join(
            p.read_text(encoding="utf-8")
            for p in (app / "src" / "portfolio_architect_gateway").glob("*.py")
        )
        assert "migration_snapshot_enabled=True" not in provider_sources


def test_expired_health_contract_is_fail_closed_and_schema_consistent() -> None:
    server = MASTER_SERVER.read_text(encoding="utf-8")
    health = server.split("def health_document", 1)[1].split(
        "def _classify_remote_api_error", 1
    )[0]
    assert "if view is not None:" in health
    assert '"snapshot_available": view is not None' in health
    assert '"snapshot_sha256": view.sha256 if view is not None else None' in health
    assert "snapshot.generated_at" not in health


def test_bilingual_actionable_migration_snapshot_error_exists() -> None:
    for language in ("en", "de"):
        translations = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        message = translations["config"]["error"][
            "dkb_gateway_migration_snapshot_unavailable"
        ]
        assert "1.45.1" in message
        assert "source" in message.casefold() or "quell" in message.casefold()
