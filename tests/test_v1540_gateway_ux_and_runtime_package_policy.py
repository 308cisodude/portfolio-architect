"""v1.55.1 Gateway acquisition UX and runtime-package policy contracts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
APPS = ROOT / "home_assistant_app"


def test_acquisition_colour_semantics_are_consistent() -> None:
    comdirect = (ROOT / "gateway/src/portfolio_architect_gateway/app.py").read_text(encoding="utf-8")
    trade_republic = (APPS / "portfolio_architect_gateway_trade_republic/src/portfolio_architect_gateway/trade_republic_app.py").read_text(encoding="utf-8")
    dkb = (APPS / "portfolio_architect_gateway_dkb/src/portfolio_architect_gateway/dkb_app.py").read_text(encoding="utf-8")
    generic = (APPS / "portfolio_architect_gateway_import/src/portfolio_architect_gateway/generic_import_app.py").read_text(encoding="utf-8")

    assert '"mode-card active"' in comdirect
    assert '"mode-card inactive-ready"' in comdirect
    assert '"mode-card inactive-unavailable"' in comdirect
    assert ".mode-card.active" in comdirect and "#22c55e" in comdirect
    assert ".mode-card.inactive-ready" in comdirect and "#3b82f6" in comdirect
    assert ".mode-card.inactive-unavailable" in comdirect and "#f59e0b" in comdirect
    for source in (trade_republic, dkb, generic):
        assert ".mode-card.active" in source
        assert "#22c55e" in source
    assert ".mode-card.unavailable" in trade_republic and "#f59e0b" in trade_republic
    assert ".mode-card.research" in dkb and "#f59e0b" in dkb


def test_static_apps_no_longer_expose_gateway_freshness_option() -> None:
    for app in (
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
        "portfolio_architect_gateway_import",
    ):
        config = yaml.safe_load((APPS / app / "config.yaml").read_text(encoding="utf-8"))
        assert "max_cached_snapshot_age_seconds" not in config["options"]
        assert "max_cached_snapshot_age_seconds" not in config["schema"]
        for language in ("en", "de"):
            translations = yaml.safe_load((APPS / app / "translations" / f"{language}.yaml").read_text(encoding="utf-8"))
            assert "max_cached_snapshot_age_seconds" not in translations.get("configuration", {})

    # The common parser retains a bounded compatibility key so an existing install
    # does not fail merely because Supervisor still has the retired option stored.
    pending = (ROOT / "gateway/src/portfolio_architect_gateway/pending_app.py").read_text(encoding="utf-8")
    assert '"max_cached_snapshot_age_seconds"' in pending


def test_comdirect_cache_setting_is_explicitly_live_lkg_only() -> None:
    config = yaml.safe_load((APPS / "portfolio_architect_gateway/config.yaml").read_text(encoding="utf-8"))
    assert config["schema"]["max_cached_snapshot_age_seconds"] == "int(0,2592000)"
    english = yaml.safe_load((APPS / "portfolio_architect_gateway/translations/en.yaml").read_text(encoding="utf-8"))
    option = english["configuration"]["max_cached_snapshot_age_seconds"]
    assert option["name"] == "Maximum live LKG snapshot age"
    assert "resilience" in option["description"].lower()
    assert "Portfolio Architect" in option["description"]
    ingress = (ROOT / "gateway/src/portfolio_architect_gateway/app.py").read_text(encoding="utf-8")
    assert "Live last-known-good serving limit" in ingress
    assert "Portfolio Architect owns evidence freshness for planning" in ingress


def test_alpine_runtime_package_is_not_exact_revision_pinned() -> None:
    for app in (
        "portfolio_architect_gateway",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
        "portfolio_architect_gateway_import",
    ):
        dockerfile = (APPS / app / "Dockerfile").read_text(encoding="utf-8")
        assert "apk add --no-cache openssl" in dockerfile
        assert "apk add --no-cache openssl=" not in dockerfile

    for workflow in ("validate.yml", "release.yml"):
        text = (ROOT / ".github/workflows" / workflow).read_text(encoding="utf-8")
        assert "openssl_output=" in text
        assert 'python tools/check_openssl_runtime.py "${app}" "${openssl_output}"' in text
        assert "minimum 3.5.8" in text

    checker = (ROOT / "tools/check_openssl_runtime.py").read_text(encoding="utf-8")
    assert "MINIMUM_OPENSSL: Final = (3, 5, 8)" in checker
    assert "version < MINIMUM_OPENSSL" in checker

    sbom = json.loads((ROOT / "SBOM.spdx.json").read_text(encoding="utf-8"))
    openssl = next(pkg for pkg in sbom["packages"] if pkg["SPDXID"] == "SPDXRef-Package-OpenSSL")
    assert openssl["versionInfo"] == "build-resolved; minimum 3.5.8"
    purl = next(ref for ref in openssl["externalRefs"] if ref["referenceType"] == "purl")
    assert purl["referenceLocator"] == "pkg:apk/alpine/openssl"


def test_v1540_keeps_gateway_wire_schemas_unchanged() -> None:
    server = (ROOT / "gateway/src/portfolio_architect_gateway/server.py").read_text(encoding="utf-8")
    rest = (ROOT / "custom_components/portfolio_architect/rest_client.py").read_text(encoding="utf-8")
    assert '"health_schema_version": min(version, 8)' in server
    assert '"requested_health_schema_version": 8' in rest
    assert json.loads((ROOT / "custom_components/portfolio_architect/manifest.json").read_text())["version"] == "1.55.1"
