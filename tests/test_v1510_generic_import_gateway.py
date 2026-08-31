"""v1.55.1 Generic Import Gateway and acquisition-boundary contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
APPS = ROOT / "home_assistant_app"
IMPORT_APP = APPS / "portfolio_architect_gateway_import"
IMPORT_PACKAGE = IMPORT_APP / "src" / "portfolio_architect_gateway"
DKB_APP = APPS / "portfolio_architect_gateway_dkb"
TEST_PACKAGE = "portfolio_architect_gateway_v1510_test"


def _generic():
    if TEST_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            TEST_PACKAGE,
            IMPORT_PACKAGE / "__init__.py",
            submodule_search_locations=[str(IMPORT_PACKAGE)],
        )
        assert spec is not None and spec.loader is not None
        package = importlib.util.module_from_spec(spec)
        sys.modules[TEST_PACKAGE] = package
        spec.loader.exec_module(package)
    return importlib.import_module(f"{TEST_PACKAGE}.generic_csv")


def test_release_versions_and_schema_are_aligned() -> None:
    assert json.loads((COMPONENT / "manifest.json").read_text())["version"] == "1.61.2"
    assert 'VERSION: Final = "1.61.2"' in (COMPONENT / "const.py").read_text()
    assert 'VERSION = 12' in (COMPONENT / "config_flow.py").read_text()
    for slug in (
        "portfolio_architect_gateway_comdirect",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
        "portfolio_architect_gateway_import",
    ):
        assert yaml.safe_load((APPS / slug / "config.yaml").read_text())["version"] == "1.61.2"


def test_portfolio_architect_runtime_is_acquisition_format_neutral() -> None:
    assert not (COMPONENT / "engine" / "importers.py").exists()
    flow = (COMPONENT / "config_flow.py").read_text()
    coordinator = (COMPONENT / "coordinator.py").read_text()
    assert "SOURCE_TYPE_LOCAL_FILES" not in flow
    assert "parse_generic_csv" not in flow
    assert "SOURCE_TYPE_LOCAL_FILES" not in coordinator


def test_schema_12_local_csv_migration_is_explicit_and_fail_closed() -> None:
    setup = (COMPONENT / "__init__.py").read_text()
    schema12 = setup.split("if entry.version < 12:", 1)[1].split("if migrated_entities:", 1)[0]
    assert "SOURCE_TYPE_LOCAL_FILES" in schema12
    assert "Portfolio Architect Gateway — Generic Import v1.61.2" in schema12
    assert "return False" in schema12
    assert "version=12" in schema12


def test_generic_import_app_has_fixed_identity_and_no_privileged_ha_api() -> None:
    config = yaml.safe_load((IMPORT_APP / "config.yaml").read_text())
    assert config["environment"]["PA_PROVIDER_ID"] == "generic_csv"
    assert config["ingress"] is True and config["panel_admin"] is True
    assert config["hassio_api"] is False
    assert config["homeassistant_api"] is False
    assert config["auth_api"] is False
    assert config["docker_api"] is False
    assert config["ports"]["8787/tcp"] is None
    entrypoint = (IMPORT_APP / "entrypoint.py").read_text()
    assert 'if provider_id != "generic_csv"' in entrypoint


def test_generic_csv_import_uses_explicit_import_time_and_eur_only() -> None:
    generic = _generic()
    config = generic.GenericCsvConfig(
        encoding="utf-8",
        delimiter="comma",
        decimal_format="dot_decimal",
        identifier_column="ID",
        name_column="Name",
        value_column="Value",
        isin_column=None,
        type_column=None,
        currency_column="Currency",
    )
    when = datetime(2026, 8, 24, 19, 0, tzinfo=timezone.utc)
    snapshot, summary = generic.parse_generic_csv(
        b"ID,Name,Value,Currency\nA1XB5U,Example ETF,123.45,EUR\n",
        config,
        generated_at=when,
    )
    assert snapshot.generated_at == when
    assert summary.generated_at == when
    assert snapshot.positions[0].market_value_eur == Decimal("123.45")
    with pytest.raises(generic.GenericCsvImportError, match="not denominated in EUR"):
        generic.parse_generic_csv(
            b"ID,Name,Value,Currency\nA1XB5U,Example ETF,123.45,USD\n",
            config,
            generated_at=when,
        )


def test_generic_import_persists_only_normalized_state_not_raw_csv() -> None:
    source = (IMPORT_PACKAGE / "generic_import_app.py").read_text()
    server = (IMPORT_PACKAGE / "server.py").read_text()
    assert "save_json_state" in source
    assert "save_snapshot" in server
    for forbidden in ("write_bytes(", "csv_filename", "original_filename", "raw_csv"):
        assert forbidden not in source
    assert "Raw CSV bytes are parsed transiently and are never persisted" in source


def test_generic_import_release_tooling_and_ci_cover_fourth_app() -> None:
    for path in (
        ROOT / "tools" / "build_release.py",
        ROOT / "tools" / "verify_release.py",
        ROOT / "tools" / "check_privacy.py",
        ROOT / ".github" / "workflows" / "validate.yml",
        ROOT / ".github" / "workflows" / "release.yml",
    ):
        assert "portfolio_architect_gateway_import" in path.read_text()


def test_dkb_probe_timestamp_is_utc_canonical_with_deterministic_berlin_display() -> None:
    source = (DKB_APP / "src" / "portfolio_architect_gateway" / "dkb_app.py").read_text()
    assert '"probe_sent_at": self.last_probe_sent_at()' in source
    assert 'ZoneInfo("Europe/Berlin")' in source
    assert "Intl.DateTimeFormat" not in source
    assert 'data-utc=' not in source
    assert "Authoritative server-side dispatch timestamp" in source
    assert "Last probe sent · Europe/Berlin" in source


def test_v151_upgrade_documents_no_automatic_generic_gateway_requirement() -> None:
    guide = (ROOT / "docs" / "UPGRADE-1.51.0.md").read_text()
    assert "Install **Portfolio Architect Gateway — Generic Import** only if" in guide
    assert "Existing official Comdirect/DKB/Trade Republic sources do not require it" in guide
    assert "No raw CSV, filename, account identifier, transaction row or provider credential is persisted" in guide
