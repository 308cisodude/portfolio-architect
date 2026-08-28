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

from portfolio_architect_gateway import supervisor_tls  # noqa: E402
from portfolio_architect_gateway.comdirect_slug_migration import (  # noqa: E402
    CUTOVER_MARKER_NAME,
    IMPORT_MARKER_NAME,
    approve_cutover,
    build_export_payload,
    commit_staged_payload,
    mark_import_options_applied,
    stage_payload,
    validate_committed_migration_identity,
)
from portfolio_architect_gateway.models import PortfolioSnapshot, Position  # noqa: E402
from portfolio_architect_gateway.store import save_snapshot  # noqa: E402

LEGACY_HOST = "b4982ef5-portfolio-architect-gateway"
CANONICAL_HOST = "b4982ef5-portfolio-architect-gateway-comdirect"


def _legacy_state(tmp_path: Path) -> Path:
    data = tmp_path / "legacy"
    data.mkdir()
    (data / "gateway-api-token").write_text("g" * 64, encoding="ascii")
    (data / "comdirect-client-id").write_text("client-id", encoding="ascii")
    (data / "comdirect-client-secret").write_text("client-secret", encoding="ascii")
    (data / "comdirect-session.json").write_text(
        '{"refresh_token":"legacy-session-must-never-transfer"}\n', encoding="utf-8"
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
    save_snapshot(
        data / "portfolio.json",
        PortfolioSnapshot(
            generated_at=datetime(2026, 8, 28, 14, 16, 38, tzinfo=timezone.utc),
            positions=(Position("IE00TEST0001", "Synthetic ETF", Decimal("123.45")),),
        ),
    )
    supervisor_tls._create_initial_material(
        data, data / "tls", "comdirect", LEGACY_HOST
    )
    return data


def _committed_migration(tmp_path: Path) -> tuple[Path, str]:
    legacy = _legacy_state(tmp_path)
    payload, summary = build_export_payload(
        legacy,
        options={
            "poll_interval_seconds": 900,
            "max_cached_snapshot_age_seconds": 604800,
            "request_timeout_seconds": 30,
            "mfa_timeout_seconds": 180,
            "health_endpoint_enabled": True,
            "depot_ids": [],
        },
        source_hostname=LEGACY_HOST,
    )
    assert payload["oauth_session_transferred"] is False
    assert "comdirect-session.json" not in payload["files"]

    staging = tmp_path / "staging"
    stage_payload(
        payload,
        staging_directory=staging,
        expected_source_hostname=LEGACY_HOST,
    )
    target = tmp_path / "canonical"
    import_marker = target / IMPORT_MARKER_NAME
    commit_staged_payload(
        staging_directory=staging,
        data_directory=target,
        import_marker=import_marker,
    )
    mark_import_options_applied(import_marker)
    approve_cutover(
        target / CUTOVER_MARKER_NAME,
        source_hostname=LEGACY_HOST,
        ca_sha256=summary.source_ca_sha256,
    )
    assert not (target / "comdirect-session.json").exists()
    return target, summary.source_ca_sha256


def test_oauth_session_still_fails_closed_before_first_canonical_runtime(tmp_path: Path) -> None:
    target, _ca_sha256 = _committed_migration(tmp_path)

    # A session that appears before the first canonical runtime is still forbidden.
    (target / "comdirect-session.json").write_text(
        '{"refresh_token":"unexpected-pre-cutover-session"}\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="before canonical cut-over"):
        validate_committed_migration_identity(target, successor_hostname=CANONICAL_HOST)

    # Merely forging the stored hostname is insufficient: the actual leaf must be
    # valid for the canonical successor hostname under the preserved private CA.
    (target / "tls" / "hostname").write_text(CANONICAL_HOST, encoding="ascii")
    with pytest.raises(ValueError, match="before canonical cut-over"):
        validate_committed_migration_identity(target, successor_hostname=CANONICAL_HOST)


def test_fresh_canonical_oauth_session_survives_later_restart(tmp_path: Path) -> None:
    target, ca_sha256 = _committed_migration(tmp_path)

    # First canonical startup must still occur with no OAuth session present.
    assert validate_committed_migration_identity(
        target, successor_hostname=CANONICAL_HOST
    ) == ca_sha256

    # entrypoint.py renews the migrated legacy-host leaf only after the validator
    # passes. This successor-bound leaf is durable App-private proof that cut-over
    # already completed and the canonical runtime has started at least once.
    supervisor_tls._renew_leaf(target / "tls", CANONICAL_HOST)
    assert (target / "tls" / "hostname").read_text(encoding="ascii") == CANONICAL_HOST

    # A fresh PhotoTAN bootstrap may now create canonical OAuth state. The next App
    # restart must accept it rather than misclassifying it as transferred legacy state.
    (target / "comdirect-session.json").write_text(
        '{"refresh_token":"fresh-canonical-session"}\n', encoding="utf-8"
    )
    assert validate_committed_migration_identity(
        target, successor_hostname=CANONICAL_HOST
    ) == ca_sha256

    marker = json.loads((target / IMPORT_MARKER_NAME).read_text(encoding="utf-8"))
    assert marker["oauth_session_transferred"] is False


def test_entrypoint_validates_pre_cutover_state_before_successor_leaf_renewal() -> None:
    entrypoint = (
        ROOT / "home_assistant_app/portfolio_architect_gateway_comdirect/entrypoint.py"
    ).read_text(encoding="utf-8")
    assert entrypoint.index("validate_committed_migration_identity(") < entrypoint.index(
        "prepare_supervisor_tls(DATA, \"comdirect\")"
    )
