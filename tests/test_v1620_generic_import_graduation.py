"""Regression contract for v1.62.0 Generic Import graduation and multi-profile support."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_import"
PACKAGE = APP / "src" / "portfolio_architect_gateway"
COMPONENT = ROOT / "custom_components" / "portfolio_architect"

TEST_PACKAGE = "portfolio_architect_gateway_v1620_test"


def _module(name: str):
    if TEST_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            TEST_PACKAGE,
            PACKAGE / "__init__.py",
            submodule_search_locations=[str(PACKAGE)],
        )
        assert spec is not None and spec.loader is not None
        package = importlib.util.module_from_spec(spec)
        sys.modules[TEST_PACKAGE] = package
        spec.loader.exec_module(package)
    return importlib.import_module(f"{TEST_PACKAGE}.{name}")


generic_csv = _module("generic_csv")
generic_profiles = _module("generic_profiles")
models = _module("models")
runtime_config = _module("runtime_config")
store = _module("store")
GenericCsvConfig = generic_csv.GenericCsvConfig
GenericCsvImportError = generic_csv.GenericCsvImportError
GenericProfileManager = generic_profiles.GenericProfileManager
LEGACY_PROVIDER_ID = generic_profiles.LEGACY_PROVIDER_ID
MAX_GENERIC_PROFILES = generic_profiles.MAX_GENERIC_PROFILES
PortfolioSnapshot = models.PortfolioSnapshot
Position = models.Position
ServerConfig = runtime_config.ServerConfig
save_snapshot = store.save_snapshot


def _server_config(tmp_path: Path) -> ServerConfig:
    token = tmp_path / "gateway-api-token"
    token.write_text("x" * 48, encoding="ascii")
    os.chmod(token, 0o600)
    return ServerConfig(
        bind="127.0.0.1",
        port=8787,
        api_token_file=token,
        snapshot_file=tmp_path / "portfolio.json",
        max_cached_snapshot_age_seconds=0,
        tls_cert_file=None,
        tls_key_file=None,
        health_endpoint_enabled=True,
    )


def _csv(*, marker: str = "") -> bytes:
    return (
        "Identifier,Security,Market Value,ISIN,Asset Type,Currency,Ignored\n"
        f"ABC123,World ETF,1234.56,DE0000000001,ETF,EUR,{marker}\n"
    ).encode("utf-8")


def _mapping() -> GenericCsvConfig:
    return GenericCsvConfig(delimiter="comma", decimal_format="dot_decimal")


def test_generic_import_is_supported_multi_profile_and_stays_unprivileged() -> None:
    config = yaml.safe_load((APP / "config.yaml").read_text(encoding="utf-8"))
    assert config["stage"] == "stable"
    assert config["environment"]["PA_PROVIDER_ID"] == LEGACY_PROVIDER_ID
    assert config["hassio_api"] is False
    assert config["homeassistant_api"] is False
    assert config["auth_api"] is False
    assert config["docker_api"] is False
    assert config["ports"]["8787/tcp"] is None
    assert "Experimental" not in config["description"]
    source = (PACKAGE / "generic_profiles.py").read_text(encoding="utf-8")
    assert "MAX_GENERIC_PROFILES" in source
    assert 'f"generic_{secrets.token_hex(6)}"' in source
    assert "/api/v1/providers/{self.provider_id}/portfolio" in source


def test_profiles_are_independent_restart_safe_and_cash_has_its_own_clock(tmp_path: Path) -> None:
    config = _server_config(tmp_path)
    discoveries: list[tuple[str, ...]] = []
    manager = GenericProfileManager(
        tmp_path,
        config,
        discovery_changed=lambda profiles: discoveries.append(
            tuple(item.provider_id for item in profiles)
        ),
    )
    first = manager.create_profile("Example Bank")
    second = manager.create_profile("Second Broker")
    assert first.provider_id != second.provider_id
    assert first.provider_id.startswith("generic_")
    assert second.provider_id.startswith("generic_")
    assert manager.ready_profiles() == ()

    evidence = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    manager.import_holdings(first.provider_id, _csv(marker="DO_NOT_PERSIST_RAW"), _mapping(), generated_at=evidence)
    assert [item.provider_id for item in manager.ready_profiles()] == [first.provider_id]
    cash_evidence = datetime(2026, 8, 31, 13, 0, tzinfo=timezone.utc)
    manager.set_cash(first.provider_id, Decimal("42.50"), as_of=cash_evidence)

    snapshot = manager.runtime(first.provider_id).provider.snapshot
    assert snapshot is not None
    assert snapshot.generated_at == evidence
    assert snapshot.investment_cash is not None
    assert snapshot.investment_cash.authorized_eur == Decimal("42.50")
    assert snapshot.investment_cash.as_of == cash_evidence
    assert manager.runtime(second.provider_id).provider.snapshot is None

    manager.rename_profile(first.provider_id, "Renamed Bank")
    assert manager.profiles()[0].provider_id == first.provider_id
    assert manager.profiles()[0].provider_name == "Renamed Bank"

    restarted = GenericProfileManager(tmp_path, config)
    restarted_snapshot = restarted.runtime(first.provider_id).provider.snapshot
    assert restarted.profiles()[0].provider_name == "Renamed Bank"
    assert restarted_snapshot is not None
    assert restarted_snapshot.generated_at == evidence
    assert restarted_snapshot.investment_cash is not None
    assert restarted_snapshot.investment_cash.as_of == cash_evidence
    assert len(restarted.ready_profiles()) == 1
    assert discoveries[-1] == (first.provider_id,)

    persisted = b"\n".join(
        path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file() and path.name != "gateway-api-token"
    )
    assert b"DO_NOT_PERSIST_RAW" not in persisted


def test_rejected_profile_import_keeps_last_canonical_snapshot(tmp_path: Path) -> None:
    manager = GenericProfileManager(tmp_path, _server_config(tmp_path))
    profile = manager.create_profile("Bank")
    manager.import_holdings(profile.provider_id, _csv(), _mapping())
    before = manager.runtime(profile.provider_id).provider.snapshot
    assert before is not None
    with pytest.raises(GenericCsvImportError):
        manager.import_holdings(
            profile.provider_id,
            b"Identifier,Security,Market Value\nBAD,Oops,-5\n",
            _mapping(),
        )
    after = manager.runtime(profile.provider_id).provider.snapshot
    assert after == before


def test_legacy_generic_csv_state_migrates_without_provider_identity_change(tmp_path: Path) -> None:
    config = _server_config(tmp_path)
    save_snapshot(
        config.snapshot_file,
        PortfolioSnapshot(
            generated_at=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc),
            positions=(
                Position(
                    identifier="ABC123",
                    name="World ETF",
                    market_value_eur=Decimal("100"),
                    isin="DE0000000001",
                    instrument_type="etf",
                ),
            ),
        ),
    )
    manager = GenericProfileManager(tmp_path, config)
    assert len(manager.profiles()) == 1
    assert manager.profiles()[0].provider_id == LEGACY_PROVIDER_ID
    assert manager.profiles()[0].portfolio_path == "/api/v1/portfolio"
    assert manager.ready_profiles()[0].provider_id == LEGACY_PROVIDER_ID


def test_profile_health_v10_exposes_human_name_and_profile_path(tmp_path: Path) -> None:
    manager = GenericProfileManager(tmp_path, _server_config(tmp_path))
    profile = manager.create_profile("My Unsupported Broker")
    manager.import_holdings(profile.provider_id, _csv(), _mapping())
    runtime = manager.runtime(profile.provider_id)
    health = runtime.state.health_document(version=10)
    assert health["health_schema_version"] == 10
    assert health["provider_id"] == profile.provider_id
    assert health["provider_name"] == "My Unsupported Broker"
    assert health["acquisition_mode"] == "csv"
    assert profile.portfolio_path == f"/api/v1/providers/{profile.provider_id}/portfolio"
    assert manager.resolve_path(profile.portfolio_path)[0] is runtime.state
    assert manager.resolve_path(profile.health_path)[0] is runtime.state


def test_profile_delete_is_scoped_and_does_not_touch_other_profile(tmp_path: Path) -> None:
    manager = GenericProfileManager(tmp_path, _server_config(tmp_path))
    first = manager.create_profile("First Bank")
    second = manager.create_profile("Second Bank")
    manager.import_holdings(first.provider_id, _csv(), _mapping())
    manager.import_holdings(second.provider_id, _csv(), _mapping())
    manager.delete_profile(first.provider_id)
    assert [item.provider_id for item in manager.profiles()] == [second.provider_id]
    assert manager.runtime(first.provider_id) is None
    assert manager.runtime(second.provider_id).provider.snapshot is not None


def test_profile_bound_is_enforced_without_collapsing_provider_identity(tmp_path: Path) -> None:
    manager = GenericProfileManager(tmp_path, _server_config(tmp_path))
    created = [manager.create_profile(f"Bank {index}") for index in range(MAX_GENERIC_PROFILES)]
    assert len({item.provider_id for item in created}) == MAX_GENERIC_PROFILES
    assert all(item.provider_id.startswith("generic_") for item in created)
    with pytest.raises(GenericCsvImportError, match="at most"):
        manager.create_profile("One too many")


def test_registry_rejects_non_string_provider_name_instead_of_coercing_it(tmp_path: Path) -> None:
    (tmp_path / "generic-profiles.json").write_text(
        json.dumps({
            "schema_version": 1,
            "profiles": [{
                "provider_id": "generic_0123456789ab",
                "provider_name": None,
                "created_at": "2026-08-31T12:00:00+00:00",
            }],
        }),
        encoding="utf-8",
    )
    with pytest.raises(Exception, match="profile is invalid"):
        GenericProfileManager(tmp_path, _server_config(tmp_path))


def test_profile_ready_discovery_tracks_rename_and_delete_without_changing_id(tmp_path: Path) -> None:
    events: list[tuple[tuple[str, str], ...]] = []
    manager = GenericProfileManager(
        tmp_path,
        _server_config(tmp_path),
        discovery_changed=lambda profiles: events.append(
            tuple((item.provider_id, item.provider_name) for item in profiles)
        ),
    )
    profile = manager.create_profile("Old Name")
    assert events[-1] == ()
    manager.import_holdings(profile.provider_id, _csv(), _mapping())
    assert events[-1] == ((profile.provider_id, "Old Name"),)
    manager.rename_profile(profile.provider_id, "New Name")
    assert events[-1] == ((profile.provider_id, "New Name"),)
    manager.delete_profile(profile.provider_id)
    assert events[-1] == ()


def test_pa_accepts_profile_transport_and_supports_eight_supplemental_gateways() -> None:
    rest_client = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert "TLS_DISCOVERY_PROFILE_SCHEMA_VERSION: Final = 2" in rest_client
    assert "_TLS_DISCOVERY_PROFILE_PATH_RE" in rest_client
    assert "HEALTH_V10_MEDIA_TYPE" in rest_client
    assert "MAX_SUPPLEMENTAL_REST_SOURCES: Final = 8" in const


def test_generic_ui_has_explicit_profile_deletion_and_no_raw_upload_persistence() -> None:
    source = (PACKAGE / "generic_import_app.py").read_text(encoding="utf-8")
    assert "Confirm permanent profile deletion" in source
    assert "Remove this provider from Portfolio Architect first" in source
    assert "Raw CSV bytes are parsed transiently and are never persisted" in source
    assert "save_json_state" not in source
    assert "document" in source
    assert "write_bytes(document)" not in source
    assert "filename" not in source.lower()
