"""Regression coverage for the v1.45.0 DKB Gateway CSV migration boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib
import importlib.util
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


def _csv(*, date: str, depot: str, wkn: str, isin: str, price: str, quantity: str) -> bytes:
    return (
        "Datum der Erstellung;Depotnummer;Wertpapierbezeichnung;WKN;ISIN;"
        "Bewertungskurs;Stückzahl;Assetklasse\n"
        f"{date};{depot};Synthetic World ETF;{wkn};{isin};{price};{quantity};ETF\n"
    ).encode("utf-8")


def test_gateway_parser_preserves_established_dkb_fixture_semantics() -> None:
    dkb_csv, _store = _load_gateway_modules()
    snapshot, summary = dkb_csv.parse_dkb_csv_batch((FIXTURE.read_bytes(),))

    assert snapshot.generated_at == datetime(2026, 7, 31, tzinfo=timezone.utc)
    assert summary.position_count == 1
    assert len(snapshot.positions) == 1
    item = snapshot.positions[0]
    assert item.identifier == "A1XB5U"
    assert item.isin == "IE00BJ0KDQ92"
    assert item.name == "X(IE)-MSCI WORLD 1C"
    assert item.instrument_type == "etf"
    assert item.market_value_eur == Decimal("273.36")
    assert item.quantity == Decimal("2")

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
    assert config["stage"] == "stable"
    assert "parse_dkb_csv_batch" in app
    assert 'path == "/import-csv"' in app
    assert "FinTS cannot replace or silently fall back to CSV evidence" in app
    for forbidden in ("HKWPO", "HKCCS", "HKDSE"):
        assert forbidden not in fints


def test_pa_side_dkb_csv_bridge_is_retired_after_live_proof() -> None:
    importers = COMPONENT / "engine" / "importers.py"
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    rest = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")
    assert not importers.exists()
    assert "async_step_dkb_sources" not in flow
    assert "async_step_hassio_migrate_dkb_csv_confirm" not in flow
    assert "migration-snapshot" not in rest


def test_new_pa_side_dkb_csv_sources_are_no_longer_offered() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    assert "dkb_sources" not in source
    assert "supplemental_dkb_csv_paths" not in source


def test_bilingual_current_ui_has_no_legacy_dkb_csv_controls() -> None:
    import json
    for language in ("en", "de"):
        translation = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        encoded = json.dumps(translation, ensure_ascii=False)
        assert "hassio_migrate_dkb_csv_confirm" not in encoded
        assert "dkb_gateway_migration_mismatch" not in encoded
        assert "supplemental_dkb_csv_paths" not in encoded
