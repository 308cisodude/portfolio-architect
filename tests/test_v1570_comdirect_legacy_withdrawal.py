"""v1.57.0 historical Comdirect App withdrawal contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "home_assistant_app"
CANONICAL = APPS / "portfolio_architect_gateway_comdirect"
LEGACY = APPS / "portfolio_architect_gateway"
GATEWAY_SRC = ROOT / "gateway" / "src"
if str(GATEWAY_SRC) not in sys.path:
    sys.path.insert(0, str(GATEWAY_SRC))

from portfolio_architect_gateway.comdirect_slug_migration import (  # noqa: E402
    MIGRATION_SCHEMA_VERSION,
    expected_legacy_hostname,
    expected_successor_hostname,
)

LEGACY_HOST = "b4982ef5-portfolio-architect-gateway"
CANONICAL_HOST = "b4982ef5-portfolio-architect-gateway-comdirect"


def test_v1570_withdraws_legacy_package_and_keeps_only_four_active_apps() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/portfolio_architect/manifest.json").read_text()
    )
    assert manifest["version"] == "1.62.4"
    assert not LEGACY.exists()

    active = {
        path.parent.name: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in APPS.glob("*/config.yaml")
    }
    assert set(active) == {
        "portfolio_architect_gateway_comdirect",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
        "portfolio_architect_gateway_import",
    }
    assert {config["slug"] for config in active.values()} == set(active)
    assert "portfolio_architect_gateway" not in {
        config["slug"] for config in active.values()
    }
    assert active["portfolio_architect_gateway_comdirect"]["stage"] == "stable"
    assert active["portfolio_architect_gateway_dkb"]["stage"] == "stable"
    assert active["portfolio_architect_gateway_trade_republic"]["stage"] == "stable"
    assert active["portfolio_architect_gateway_import"]["stage"] == "stable"
    assert all(config["version"] == "1.62.4" for config in active.values())


def test_release_and_publication_tooling_no_longer_carries_legacy_app() -> None:
    files = {
        "build": ROOT / "tools/build_release.py",
        "verify": ROOT / "tools/verify_release.py",
        "sync": ROOT / "tools/sync_gateway_app_sources.py",
        "release_check": ROOT / "tools/release_check.sh",
        "publication": ROOT / "tools/check_publication.py",
        "configure": ROOT / "tools/configure_publication.py",
        "privacy": ROOT / "tools/check_privacy.py",
        "validate": ROOT / ".github/workflows/validate.yml",
        "release": ROOT / ".github/workflows/release.yml",
        "codeowners": ROOT / ".github/CODEOWNERS",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}

    assert "portfolio-architect-gateway-app-v{version}.zip" not in texts["build"]
    assert "portfolio-architect-gateway-app-v{release_version}.zip" not in texts["verify"]
    for name in ("build", "sync", "release_check", "publication", "configure", "codeowners"):
        assert "home_assistant_app/portfolio_architect_gateway/" not in texts[name]

    for name in ("validate", "release"):
        # The canonical slug naturally contains the historical slug as a prefix;
        # reject only a standalone build-list entry for the retired package.
        assert re.search(r"^\s+portfolio_architect_gateway\s+\\$", texts[name], re.M) is None
        assert "portfolio_architect_gateway_comdirect" in texts[name]

    assert '"portfolio_architect_gateway",\n' not in texts["privacy"]
    assert '"home_assistant_app/portfolio_architect_gateway",\n' not in texts["privacy"]
    assert '"home_assistant_app/portfolio_architect_gateway/icon.png"' in texts["privacy"]
    assert '"home_assistant_app/portfolio_architect_gateway/logo.png"' in texts["privacy"]
    assert "historical=True" in texts["privacy"]


def test_canonical_comdirect_retains_supported_legacy_receiver_contract() -> None:
    config = yaml.safe_load((CANONICAL / "config.yaml").read_text(encoding="utf-8"))
    entrypoint = (CANONICAL / "entrypoint.py").read_text(encoding="utf-8")
    receiver = (
        CANONICAL / "src/portfolio_architect_gateway/comdirect_migration_app.py"
    ).read_text(encoding="utf-8")
    migration = (
        CANONICAL / "src/portfolio_architect_gateway/comdirect_slug_migration.py"
    ).read_text(encoding="utf-8")

    assert config["slug"] == "portfolio_architect_gateway_comdirect"
    assert config["stage"] == "stable"
    assert "serve_comdirect_migration_setup" in entrypoint
    assert "validate_committed_migration_identity" in entrypoint
    assert "expected_legacy_hostname(hostname)" in entrypoint
    assert "comdirect-migration-receiver" in receiver
    assert MIGRATION_SCHEMA_VERSION == 1
    assert '"oauth_session_transferred": False' in migration
    assert expected_successor_hostname(LEGACY_HOST) == CANONICAL_HOST
    assert expected_legacy_hostname(CANONICAL_HOST) == LEGACY_HOST


def test_sbom_and_current_docs_describe_withdrawal_without_reusing_slug() -> None:
    sbom = json.loads((ROOT / "SBOM.spdx.json").read_text(encoding="utf-8"))
    package_names = {package["name"] for package in sbom["packages"]}
    assert "Portfolio Architect Gateway — Comdirect LEGACY App" not in package_names
    assert "Portfolio Architect Gateway — Comdirect App" in package_names

    release_notes = (ROOT / "docs/RELEASE-NOTES.md").read_text(encoding="utf-8")
    upgrade = (ROOT / "docs/UPGRADE-1.57.0.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
    providers = (ROOT / "docs/GATEWAY-PROVIDERS.md").read_text(encoding="utf-8")

    assert "removed from the active repository" in release_notes
    assert "no v1.57.0 Legacy App archive is published" in upgrade
    assert "Historical Comdirect App withdrawal (v1.57.0) — completed" in roadmap
    assert "withdrawn from the active App repository in v1.57.0" in providers
    assert "historical slug is not reused" in (release_notes + upgrade + roadmap).lower()
