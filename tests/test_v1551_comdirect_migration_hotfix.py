"""v1.55.1 live-migration hotfix regression contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATEWAY_SRC = ROOT / "gateway" / "src"
if str(GATEWAY_SRC) not in sys.path:
    sys.path.insert(0, str(GATEWAY_SRC))

from portfolio_architect_gateway.comdirect_slug_migration import (  # noqa: E402
    MIGRATION_ERROR_CODES,
    MIGRATION_ERROR_INVALID_CODE,
    MigrationError,
    build_export_payload,
    parse_migration_code,
)
from portfolio_architect_gateway.models import PortfolioSnapshot, Position  # noqa: E402
from portfolio_architect_gateway.store import save_snapshot  # noqa: E402
from portfolio_architect_gateway import supervisor_tls  # noqa: E402

LEGACY_HOST = "b4982ef5-portfolio-architect-gateway"


def _options() -> dict[str, object]:
    return {
        "poll_interval_seconds": 900,
        "max_cached_snapshot_age_seconds": 604800,
        "request_timeout_seconds": 47,
        "mfa_timeout_seconds": 180,
        "health_endpoint_enabled": True,
        "depot_ids": [],
    }


def _state(tmp_path: Path, acquisition: dict[str, object]) -> Path:
    data = tmp_path / "legacy"
    data.mkdir()
    (data / "gateway-api-token").write_text("g" * 64, encoding="ascii")
    (data / "comdirect-client-id").write_text("client-id", encoding="ascii")
    (data / "comdirect-client-secret").write_text("client-secret", encoding="ascii")
    (data / "comdirect-session.json").write_text(
        '{"refresh_token":"excluded"}\n', encoding="utf-8"
    )
    (data / "comdirect-acquisition.json").write_text(
        json.dumps(acquisition, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    save_snapshot(
        data / "portfolio.json",
        PortfolioSnapshot(
            generated_at=datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc),
            positions=(Position("IE00TEST0001", "Synthetic ETF", Decimal("123.45")),),
        ),
    )
    supervisor_tls._create_initial_material(data, data / "tls", "comdirect", LEGACY_HOST)
    return data


def test_live_production_schema2_acquisition_state_is_migratable(tmp_path: Path) -> None:
    """Reproduce the live v1.55.1 failure: a normal post-switch schema-2 state."""
    legacy = _state(
        tmp_path,
        {
            "schema_version": 2,
            "mode": "live_api",
            "previous_mode": "csv",
            "last_method_change_at": "2026-08-26T20:39:52+00:00",
            "last_method_change_reason": "operator",
        },
    )
    payload, summary = build_export_payload(
        legacy, options=_options(), source_hostname=LEGACY_HOST
    )
    assert summary.acquisition_mode == "live_api"
    assert payload["files"]["comdirect-acquisition.json"]["size"] > 0


def test_schema2_acquisition_state_remains_strict(tmp_path: Path) -> None:
    legacy = _state(
        tmp_path,
        {
            "schema_version": 2,
            "mode": "live_api",
            "previous_mode": "csv",
            "last_method_change_at": "2026-08-26T20:39:52+00:00",
            "last_method_change_reason": "unexpected",
        },
    )
    with pytest.raises(ValueError):
        build_export_payload(legacy, options=_options(), source_hostname=LEGACY_HOST)


def test_invalid_code_uses_bounded_reason_class() -> None:
    with pytest.raises(MigrationError) as captured:
        parse_migration_code("not-a-code")
    assert captured.value.code == MIGRATION_ERROR_INVALID_CODE
    assert captured.value.code in MIGRATION_ERROR_CODES


def test_legacy_ingress_redirects_migration_failures_to_bounded_card() -> None:
    app = (ROOT / "gateway/src/portfolio_architect_gateway/app.py").read_text(encoding="utf-8")
    assert "except MigrationError as err:" in app
    assert 'f"./?migration_error={err.code}"' in app
    assert "Migration not staged." in app
    assert "No provider authority or Portfolio Architect endpoint was changed." in app
    for code in (
        "invalid_code",
        "legacy_state_invalid",
        "successor_unreachable",
        "successor_tls_mismatch",
        "successor_auth_rejected",
        "successor_payload_rejected",
        "successor_response_invalid",
        "local_stage_record_failed",
    ):
        assert code in app


def test_legacy_staging_preflights_successor_before_private_transfer() -> None:
    app = (ROOT / "gateway/src/portfolio_architect_gateway/app.py").read_text(encoding="utf-8")
    method = app.split("def stage_slug_migration", 1)[1].split("def freeze_legacy_for_cutover", 1)[0]
    assert method.index("build_export_payload(") < method.index("successor_status(")
    assert method.index("successor_status(") < method.index("send_payload_to_successor(")
    assert 'status in {"staged", "committed"} and staged_summary == local_summary' in method


def test_v1551_version_and_wire_contracts() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/portfolio_architect/manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == "1.61.0"
    server = (ROOT / "gateway/src/portfolio_architect_gateway/server.py").read_text(encoding="utf-8")
    rest = (ROOT / "custom_components/portfolio_architect/rest_client.py").read_text(encoding="utf-8")
    assert '"health_schema_version": min(version, 9)' in server
    assert '"requested_health_schema_version": 9' in rest
