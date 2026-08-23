"""Regression coverage for the v1.45.0 DKB Gateway CSV migration boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb"
PACKAGE = APP / "src" / "portfolio_architect_gateway"
TEST_PACKAGE = "portfolio_architect_gateway_dkb_v1450_test"
ENGINE_PACKAGE = "portfolio_architect_engine_v1450_test"
FIXTURE = ROOT / "tests" / "fixtures" / "dkb-depot.csv"


def _load_gateway_modules():
    if TEST_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            TEST_PACKAGE,
            PACKAGE / "__init__.py",
            submodule_search_locations=[str(PACKAGE)],
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[TEST_PACKAGE] = module
        spec.loader.exec_module(module)
    return (
        importlib.import_module(f"{TEST_PACKAGE}.dkb_csv"),
        importlib.import_module(f"{TEST_PACKAGE}.store"),
    )


def _load_legacy_importers():
    package_path = COMPONENT / "engine"
    if ENGINE_PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            ENGINE_PACKAGE,
            package_path / "__init__.py",
            submodule_search_locations=[str(package_path)],
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[ENGINE_PACKAGE] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f"{ENGINE_PACKAGE}.importers")


def _csv(*, date: str, depot: str, wkn: str, isin: str, price: str, quantity: str) -> bytes:
    return (
        "Datum der Erstellung;Depotnummer;Wertpapierbezeichnung;WKN;ISIN;"
        "Bewertungskurs;Stückzahl;Assetklasse\n"
        f"{date};{depot};Synthetic World ETF;{wkn};{isin};{price};{quantity};ETF\n"
    ).encode("utf-8")


def test_gateway_parser_is_exactly_equivalent_to_legacy_fixture() -> None:
    dkb_csv, _store = _load_gateway_modules()
    legacy = _load_legacy_importers()

    old = legacy.read_dkb_positions(FIXTURE)
    snapshot, summary = dkb_csv.parse_dkb_csv_batch((FIXTURE.read_bytes(),))

    assert snapshot.generated_at == legacy.dkb_export_timestamp(FIXTURE)
    assert summary.position_count == len(old) == len(snapshot.positions)
    assert [
        (item.identifier, item.isin, item.name, item.instrument_type, item.market_value_eur, item.quantity)
        for item in snapshot.positions
    ] == [
        (item.wkn, item.isin, item.name, item.instrument_type, item.value_eur, item.quantity)
        for item in old.values()
    ]


def test_authoritative_batch_selects_newest_per_depot_and_uses_oldest_selected_date() -> None:
    dkb_csv, _store = _load_gateway_modules()
    snapshot, summary = dkb_csv.parse_dkb_csv_batch(
        (
            _csv(date="01.08.2026", depot="DEPOT-1", wkn="AAA111", isin="IE00AAA11111", price="10,00", quantity="2"),
            _csv(date="02.08.2026", depot="DEPOT-1", wkn="AAA111", isin="IE00AAA11111", price="11,00", quantity="2"),
            _csv(date="01.08.2026", depot="DEPOT-2", wkn="BBB222", isin="IE00BBB22222", price="20,00", quantity="3"),
        )
    )
    assert summary.input_file_count == 3
    assert summary.selected_depot_count == 2
    assert snapshot.generated_at == datetime(2026, 8, 1, tzinfo=timezone.utc)
    values = {item.identifier: item.market_value_eur for item in snapshot.positions}
    assert values == {"AAA111": Decimal("22.00"), "BBB222": Decimal("60.00")}


def test_same_depot_same_date_conflict_fails_closed() -> None:
    dkb_csv, _store = _load_gateway_modules()
    first = _csv(date="02.08.2026", depot="DEPOT-1", wkn="AAA111", isin="IE00AAA11111", price="11,00", quantity="2")
    second = _csv(date="02.08.2026", depot="DEPOT-1", wkn="AAA111", isin="IE00AAA11111", price="12,00", quantity="2")
    with pytest.raises(dkb_csv.DkbCsvImportError, match="same depot and date"):
        dkb_csv.parse_dkb_csv_batch((first, second))


def test_only_normalized_snapshot_is_persisted_with_private_permissions(tmp_path: Path) -> None:
    dkb_csv, store = _load_gateway_modules()
    raw = _csv(date="02.08.2026", depot="DEPOT-1", wkn="AAA111", isin="IE00AAA11111", price="11,00", quantity="2")
    snapshot, _summary = dkb_csv.parse_dkb_csv_batch((raw,))
    target = tmp_path / "portfolio.json"
    store.save_snapshot(target, snapshot)

    persisted = target.read_text(encoding="utf-8")
    assert "DEPOT-1" not in persisted
    assert "Depotnummer" not in persisted
    assert "Datum der Erstellung" not in persisted
    assert "AAA111" in persisted
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_dkb_app_is_autostart_csv_source_but_fints_stays_separate() -> None:
    config = yaml.safe_load((APP / "config.yaml").read_text(encoding="utf-8"))
    app = (PACKAGE / "dkb_app.py").read_text(encoding="utf-8")
    fints = (PACKAGE / "dkb_fints.py").read_text(encoding="utf-8")
    assert config["environment"]["PA_PROVIDER_ID"] == "dkb"
    assert config["boot"] == "auto"
    assert config["stage"] == "experimental"
    assert "parse_dkb_csv_batch" in app
    assert 'path == "/import-csv"' in app
    assert "FinTS cannot replace or silently fall back to the CSV snapshot" in app
    for forbidden in ("HKWPO", "HKCCS", "HKDSE"):
        assert forbidden not in fints


def test_discovery_routes_legacy_dkb_to_exact_atomic_migration_not_normal_add() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    discovery = source.split("async def async_step_hassio", 1)[1].split(
        "async def async_step_hassio_confirm", 1
    )[0]
    migration = source.split("async def async_step_hassio_migrate_dkb_csv_confirm", 1)[1].split(
        "async def async_step_hassio_add_supplemental_confirm", 1
    )[0]
    assert "gateway_provider_conflicts_with_dkb_csv" in discovery
    assert "async_step_hassio_migrate_dkb_csv_confirm" in discovery
    assert discovery.index("async_step_hassio_migrate_dkb_csv_confirm") < discovery.index(
        "async_step_hassio_add_supplemental_confirm"
    )
    assert "_dkb_migration_snapshots_match" in migration
    assert migration.index("_dkb_migration_snapshots_match") < migration.index(
        "async_update_entry"
    )
    assert 'options.pop(CONF_SUPPLEMENTAL_DKB_CSV_PATHS, None)' in migration
    assert 'provider_id=GATEWAY_PROVIDER_DKB' in migration
    assert 'reason="dkb_gateway_migrated"' in migration


def test_new_pa_side_dkb_csv_sources_are_no_longer_offered() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    options_sources = source.split("async def async_step_sources", 1)[1].split(
        "async def async_step_dkb_sources", 1
    )[0]
    assert "legacy_dkb" in options_sources
    assert 'menu.append("dkb_sources")' in options_sources
    assert "and legacy_dkb" in options_sources


def test_bilingual_migration_text_and_fail_closed_error_exist() -> None:
    for language in ("en", "de"):
        translation = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        config = translation["config"]
        assert "hassio_migrate_dkb_csv_confirm" in config["step"]
        assert "dkb_gateway_migration_mismatch" in config["error"]
        assert "dkb_gateway_migrated" in config["abort"]
