"""Regression contracts for v1.26.7 Gateway cold-restart snapshot integrity."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "gateway" / "src" / "portfolio_architect_gateway"
APPS = ROOT / "home_assistant_app"


def test_release_version_and_wire_contracts_remain_aligned() -> None:
    manifest = json.loads(
        (ROOT / "custom_components" / "portfolio_architect" / "manifest.json").read_text()
    )
    assert manifest["version"] == "1.53.0"
    notes = (ROOT / "docs" / "RELEASE-NOTES.md").read_text(encoding="utf-8")
    assert "payload schema 8: unchanged" in notes
    assert "REST portfolio schema 1: unchanged" in notes
    assert "Gateway health schema 8 current; schemas 1–7 remain supported" in notes


def test_cache_parser_restores_optional_quantity() -> None:
    source = (GATEWAY / "models.py").read_text(encoding="utf-8")
    parser = source.split("def parse_snapshot_bytes", 1)[1].split(
        "def _parse_cached_investment_cash", 1
    )[0]
    assert 'if "quantity" in item:' in parser
    assert 'field="position quantity"' in parser
    assert "quantity=quantity" in parser


def test_etag_validator_precedes_if_modified_since() -> None:
    source = (GATEWAY / "server.py").read_text(encoding="utf-8")
    serve = source.split("    def _serve_portfolio", 1)[1].split(
        "    def _serve_health", 1
    )[0]
    assert 'if_none_match = self.headers.get("If-None-Match")' in serve
    assert "if if_none_match is not None:" in serve
    assert "elif _not_modified_since(" in serve
    assert serve.index("if if_none_match is not None:") < serve.index(
        "elif _not_modified_since("
    )


def test_common_integrity_fix_is_synced_to_provider_apps() -> None:
    master_models = (GATEWAY / "models.py").read_bytes()
    master_server = (GATEWAY / "server.py").read_bytes()
    for slug in (
        "portfolio_architect_gateway",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
    ):
        package = APPS / slug / "src" / "portfolio_architect_gateway"
        assert (package / "models.py").read_bytes() == master_models
        assert (package / "server.py").read_bytes() == master_server


def test_upgrade_guide_preserves_authentication_and_wire_compatibility() -> None:
    guide = (ROOT / "docs" / "UPGRADE-1.35.0.md").read_text(encoding="utf-8")
    assert "Existing broker schema-1 and schema-2 configuration" in guide
    assert "cross-provider funding is **not** enabled automatically" in guide
    assert "Do not reauthenticate Comdirect" in guide
    assert "REST portfolio schema 1" in guide and "unchanged" in guide
    assert "Gateway health schema 6" in guide and "unchanged" in guide
