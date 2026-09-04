"""v1.55.1 capability-scoped Gateway maturity contracts."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib
import importlib.util
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).parents[1]
APPS = ROOT / "home_assistant_app"
DKB = APPS / "portfolio_architect_gateway_dkb"
TR = APPS / "portfolio_architect_gateway_trade_republic"
GENERIC = APPS / "portfolio_architect_gateway_import"
COMDIRECT = APPS / "portfolio_architect_gateway_comdirect"
GENERIC_PACKAGE = GENERIC / "src" / "portfolio_architect_gateway"
TEST_PACKAGE = "portfolio_architect_gateway_v1520_test"


def _generic():
    if TEST_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            TEST_PACKAGE,
            GENERIC_PACKAGE / "__init__.py",
            submodule_search_locations=[str(GENERIC_PACKAGE)],
        )
        assert spec is not None and spec.loader is not None
        package = importlib.util.module_from_spec(spec)
        sys.modules[TEST_PACKAGE] = package
        spec.loader.exec_module(package)
    return importlib.import_module(f"{TEST_PACKAGE}.generic_csv")


def _config(app: Path) -> dict[str, object]:
    return yaml.safe_load((app / "config.yaml").read_text(encoding="utf-8"))


def test_current_release_versions_and_app_maturity_are_aligned() -> None:
    assert json.loads(
        (ROOT / "custom_components" / "portfolio_architect" / "manifest.json").read_text()
    )["version"] == "1.62.5"
    assert _config(COMDIRECT)["stage"] == "stable"
    assert _config(DKB)["stage"] == "stable"
    assert _config(TR)["stage"] == "stable"
    assert _config(GENERIC)["stage"] == "stable"
    assert not (APPS / "portfolio_architect_gateway").exists()
    for app in (COMDIRECT, DKB, TR, GENERIC):
        assert _config(app)["version"] == "1.62.5"


def test_dkb_stability_is_scoped_to_csv_while_fints_probe_stays_experimental() -> None:
    config = _config(DKB)
    assert "Stable bounded local DKB" in str(config["description"])
    assert "experimental anonymous FinTS capability probe for research" in str(config["description"])
    source = (DKB / "src" / "portfolio_architect_gateway" / "dkb_app.py").read_text(
        encoding="utf-8"
    )
    assert "Static acquisition · DKB CSV" in source
    assert "EXPERIMENTAL · RESEARCH ONLY" in source
    assert "Authenticated FinTS acquisition is not enabled" in source
    assert "FinTS cannot replace or silently fall back to CSV evidence" in source


def test_trade_republic_stable_label_does_not_invent_live_api_acquisition() -> None:
    config = _config(TR)
    assert "Stable isolated Trade Republic Gateway" in str(config["description"])
    assert config["stage"] == "stable"
    source = (TR / "src" / "portfolio_architect_gateway" / "trade_republic_app.py").read_text(
        encoding="utf-8"
    )
    assert "DEPOTAUSZUG" in source
    assert "KONTOAUSZUG" in source
    assert "live_api" not in source
    en = (TR / "translations" / "en.yaml").read_text(encoding="utf-8")
    de = (TR / "translations" / "de.yaml").read_text(encoding="utf-8")
    assert "max_cached_snapshot_age_seconds" not in en
    assert "max_cached_snapshot_age_seconds" not in de


def test_synthetic_generic_import_reference_csv_is_a_standalone_smoke_fixture() -> None:
    generic = _generic()
    raw = (ROOT / "examples" / "generic-csv" / "portfolio.csv").read_bytes()
    when = datetime(2026, 8, 25, 0, 0, tzinfo=timezone.utc)
    snapshot, summary = generic.parse_generic_csv(
        raw,
        generic.GenericCsvConfig(),
        generated_at=when,
    )
    assert summary.position_count == 2
    assert snapshot.generated_at == when
    assert [item.identifier for item in snapshot.positions] == ["DEMOETF1", "DEMO1234"]
    assert all(item.market_value_eur >= 0 for item in snapshot.positions)


def test_generic_import_is_stable_multi_profile_and_remains_unprivileged() -> None:
    config = _config(GENERIC)
    assert config["stage"] == "stable"
    assert config["environment"]["PA_PROVIDER_ID"] == "generic_csv"
    assert "Supported provider-neutral multi-profile CSV Gateway" in str(config["description"])
    assert config["hassio_api"] is False
    assert config["homeassistant_api"] is False
    guide = (ROOT / "docs" / "UPGRADE-1.62.0.md").read_text(encoding="utf-8")
    assert "One Generic App supports at most eight profiles" in guide
    assert "Raw CSV bytes are parsed transiently" in guide
    assert "Remove an adopted Generic provider from Portfolio Architect before deleting" in guide


def test_sbom_describes_all_four_gateway_apps() -> None:
    sbom = json.loads((ROOT / "SBOM.spdx.json").read_text(encoding="utf-8"))
    package_names = {package["name"] for package in sbom["packages"]}
    assert {
        "Portfolio Architect Gateway — Comdirect App",
        "Portfolio Architect Gateway — DKB App",
        "Portfolio Architect Gateway — Trade Republic App",
        "Portfolio Architect Gateway — Generic Import App",
    } <= package_names
    generic = next(
        package
        for package in sbom["packages"]
        if package["name"] == "Portfolio Architect Gateway — Generic Import App"
    )
    assert generic["versionInfo"] == "1.62.5"
