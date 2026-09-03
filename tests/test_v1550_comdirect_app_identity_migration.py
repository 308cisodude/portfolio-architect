from __future__ import annotations

from datetime import datetime, timezone
import ast
import inspect
from decimal import Decimal
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
GATEWAY_SRC = ROOT / "gateway" / "src"
if str(GATEWAY_SRC) not in sys.path:
    sys.path.insert(0, str(GATEWAY_SRC))

from portfolio_architect_gateway.comdirect_slug_migration import (  # noqa: E402
    CUTOVER_MARKER_NAME,
    IMPORT_MARKER_NAME,
    approve_cutover,
    build_export_payload,
    commit_staged_payload,
    expected_legacy_hostname,
    expected_successor_hostname,
    mark_import_options_applied,
    stage_payload,
    validate_committed_migration_identity,
)
from portfolio_architect_gateway.models import PortfolioSnapshot, Position  # noqa: E402
from portfolio_architect_gateway.store import save_snapshot  # noqa: E402
from portfolio_architect_gateway import supervisor_tls  # noqa: E402

LEGACY_HOST = "b4982ef5-portfolio-architect-gateway"
NEW_HOST = "b4982ef5-portfolio-architect-gateway-comdirect"


def _options() -> dict[str, object]:
    return {
        "poll_interval_seconds": 900,
        "max_cached_snapshot_age_seconds": 604800,
        "request_timeout_seconds": 47,
        "mfa_timeout_seconds": 180,
        "health_endpoint_enabled": True,
        "depot_ids": ["D1"],
    }


def _legacy_state(tmp_path: Path) -> Path:
    data = tmp_path / "legacy"
    data.mkdir()
    (data / "gateway-api-token").write_text("g" * 64, encoding="ascii")
    (data / "comdirect-client-id").write_text("client-id", encoding="ascii")
    (data / "comdirect-client-secret").write_text("client-secret", encoding="ascii")
    (data / "comdirect-session.json").write_text(
        '{"refresh_token":"must-never-migrate"}\n', encoding="utf-8"
    )
    (data / "comdirect-acquisition.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "mode": "live_api",
                "previous_mode": "csv",
                "last_method_change_at": "2026-08-26T20:39:52+00:00",
                "last_method_change_reason": "operator",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    snapshot = PortfolioSnapshot(
        generated_at=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
        positions=(Position("IE00TEST0001", "Synthetic ETF", Decimal("123.45")),),
    )
    save_snapshot(data / "portfolio.json", snapshot)
    supervisor_tls._create_initial_material(data, data / "tls", "comdirect", LEGACY_HOST)
    return data


def test_exact_slug_relationship_has_no_user_controlled_destination() -> None:
    assert expected_successor_hostname(LEGACY_HOST) == NEW_HOST
    assert expected_legacy_hostname(NEW_HOST) == LEGACY_HOST
    with pytest.raises(ValueError):
        expected_successor_hostname("evil.example")
    with pytest.raises(ValueError):
        expected_legacy_hostname("b4982ef5-portfolio-architect-gateway-comdirect.attacker")


def test_migration_preserves_long_lived_state_but_excludes_oauth(tmp_path: Path) -> None:
    legacy = _legacy_state(tmp_path)
    payload, summary = build_export_payload(
        legacy, options=_options(), source_hostname=LEGACY_HOST
    )
    assert payload["oauth_session_transferred"] is False
    assert "comdirect-session.json" not in payload["files"]
    assert summary.source_hostname == LEGACY_HOST
    assert summary.acquisition_mode == "live_api"

    staging = tmp_path / "workspace" / "staging"
    assert stage_payload(
        payload, staging_directory=staging, expected_source_hostname=LEGACY_HOST
    ) == summary

    target = tmp_path / "target"
    import_marker = target / IMPORT_MARKER_NAME
    committed, options = commit_staged_payload(
        staging_directory=staging,
        data_directory=target,
        import_marker=import_marker,
    )
    assert committed == summary
    assert options["request_timeout_seconds"] == 47
    assert not (target / "comdirect-session.json").exists()
    assert (target / "gateway-api-token").read_text(encoding="ascii") == "g" * 64
    assert supervisor_tls._certificate_sha256(
        supervisor_tls._read_ca_certificate(target / "tls/ca-cert.pem")
    ) == summary.source_ca_sha256

    mark_import_options_applied(import_marker)
    approve_cutover(
        target / CUTOVER_MARKER_NAME,
        source_hostname=LEGACY_HOST,
        ca_sha256=summary.source_ca_sha256,
    )
    assert validate_committed_migration_identity(
        target, successor_hostname=NEW_HOST
    ) == summary.source_ca_sha256


def test_tampered_migration_payload_fails_closed(tmp_path: Path) -> None:
    legacy = _legacy_state(tmp_path)
    payload, _summary = build_export_payload(
        legacy, options=_options(), source_hostname=LEGACY_HOST
    )
    payload["files"]["portfolio.json"]["data"] = "AAAA"
    with pytest.raises(ValueError):
        stage_payload(
            payload,
            staging_directory=tmp_path / "staging",
            expected_source_hostname=LEGACY_HOST,
        )


def test_provider_qualified_entrypoint_uses_supported_supervisor_hostname_api() -> None:
    entrypoint_path = (
        ROOT / "home_assistant_app/portfolio_architect_gateway_comdirect/entrypoint.py"
    )
    source = entrypoint_path.read_text()
    tree = ast.parse(source)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "supervisor_app_hostname"
    ]
    assert len(calls) == 1
    supported = set(
        inspect.signature(supervisor_tls.supervisor_app_hostname).parameters
    )
    assert {kw.arg for kw in calls[0].keywords if kw.arg is not None} <= supported
    assert "expected_legacy_hostname(hostname)" in source

def test_provider_qualified_app_remains_migration_receiver_after_legacy_withdrawal() -> None:
    assert not (ROOT / "home_assistant_app/portfolio_architect_gateway").exists()
    new = yaml.safe_load(
        (ROOT / "home_assistant_app/portfolio_architect_gateway_comdirect/config.yaml").read_text()
    )
    assert new["slug"] == "portfolio_architect_gateway_comdirect"
    assert new["name"] == "Portfolio Architect Gateway — Comdirect"
    assert new["panel_title"] == "Portfolio Gateway — Comdirect"
    assert new["stage"] == "stable"
    assert new["ports"]["8787/tcp"] is None
    entrypoint = (
        ROOT / "home_assistant_app/portfolio_architect_gateway_comdirect/entrypoint.py"
    ).read_text()
    assert "serve_comdirect_migration_setup" in entrypoint
    assert "validate_committed_migration_identity" in entrypoint
    assert "expected_legacy_hostname(hostname)" in entrypoint
    assert "ready_when_live=True" in entrypoint
    assert "expected_ca_sha256" in entrypoint


def test_pa_cutover_is_explicit_same_ca_and_integrity_validated() -> None:
    rest = (ROOT / "custom_components/portfolio_architect/rest_client.py").read_text()
    flow = (ROOT / "custom_components/portfolio_architect/config_flow.py").read_text()
    assert "matches_comdirect_slug_successor" in rest
    assert "_COMDIRECT_CANONICAL_APP_HOST_SUFFIX" in rest
    assert "async_step_hassio_comdirect_slug_migration_confirm" in flow
    assert "stored.tls_ca_sha256 != discovery.ca_sha256" in flow
    assert 'health.health_schema_version < 8' in flow
    assert 'health.provider_id != GATEWAY_PROVIDER_COMDIRECT' in flow
    assert 'health.snapshot_sha256 != result.snapshot_sha256' in flow
    assert 'health.snapshot_position_count != len(snapshot.positions)' in flow
    assert 'data[CONF_REST_ENDPOINT_URL] = discovery.endpoint_url' in flow
    assert 'data[CONF_REST_API_TOKEN]' not in flow.split(
        "async_step_hassio_comdirect_slug_migration_confirm", 1
    )[1].split("async_step_hassio_confirm", 1)[0]


def test_release_tooling_carries_only_canonical_comdirect_but_keeps_receiver() -> None:
    build = (ROOT / "tools/build_release.py").read_text()
    sync = (ROOT / "tools/sync_gateway_app_sources.py").read_text()
    verify = (ROOT / "tools/verify_release.py").read_text()
    validate = (ROOT / ".github/workflows/validate.yml").read_text()
    release = (ROOT / ".github/workflows/release.yml").read_text()
    for text in (build, sync, verify, validate, release):
        assert "portfolio_architect_gateway_comdirect" in text
        assert 'home_assistant_app/portfolio_architect_gateway/' not in text
    assert "portfolio-architect-gateway-comdirect-app-v{version}.zip" in build
    assert "portfolio-architect-gateway-app-v{version}.zip" not in build
    assert "comdirect-migration-receiver" in (
        ROOT / "gateway/src/portfolio_architect_gateway/comdirect_migration_app.py"
    ).read_text()
    assert validate.count("canonical_name=") == 1
    assert release.count("canonical_name=") == 1


def test_current_release_is_v1550_and_wire_contracts_remain_unchanged() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/portfolio_architect/manifest.json").read_text()
    )
    assert manifest["version"] == "1.62.3"
    server = (ROOT / "gateway/src/portfolio_architect_gateway/server.py").read_text()
    rest = (ROOT / "custom_components/portfolio_architect/rest_client.py").read_text()
    assert '"health_schema_version": min(version, 10)' in server
    assert '"requested_health_schema_version": 10' in rest
