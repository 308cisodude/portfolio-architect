"""Regression contracts for v1.62.5 optional exceptions metadata handling."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import hashlib
import importlib
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
CALCULATOR = COMPONENT / "engine" / "calculator.py"
COORDINATOR = COMPONENT / "coordinator.py"

TEST_PACKAGE = "portfolio_architect_v1625_component_test"
if TEST_PACKAGE not in sys.modules:
    package = types.ModuleType(TEST_PACKAGE)
    package.__path__ = [str(COMPONENT)]
    package.__package__ = TEST_PACKAGE
    sys.modules[TEST_PACKAGE] = package

calculator = importlib.import_module(f"{TEST_PACKAGE}.engine.calculator")
bootstrap = importlib.import_module(f"{TEST_PACKAGE}.bootstrap")
models = importlib.import_module(f"{TEST_PACKAGE}.engine.models")




def _first_run_plan(position):
    return bootstrap.BootstrapPlan(
        name="v1.62.5 clean-room plan",
        budget_amount_eur=Decimal("100"),
        corridor_pp=Decimal("5"),
        minimum_trade_eur=Decimal("10"),
        rounding_step_eur=Decimal("10"),
        instruments=(
            bootstrap.BootstrapInstrument(
                position=position,
                target_pct=Decimal("100"),
                buy_enabled=True,
                ucits=True,
                domicile="IE",
                distribution="accumulating",
                fund_currency="EUR",
                ter_pct=Decimal("0.10"),
                fund_size_eur=Decimal("1000000000"),
                metadata_source="Synthetic v1.62.5 regression fixture",
            ),
        ),
        ucits_required=True,
        accumulating_preferred=True,
        ireland_preferred=True,
        max_ter_pct=Decimal("0.50"),
        minimum_fund_size_eur=Decimal("1000000"),
        savings_plan_required=False,
        free_savings_plan_preferred=False,
    )

def _write_required_files(config_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(bootstrap.REQUIRED_CONFIGURATION_FILES, start=1):
        (config_dir / name).write_text(f"schema_version: {index}\n", encoding="utf-8")


def _fingerprint(config_directory: Path, paths: tuple[Path, ...], plan_override) -> str:
    """Small exact-path-sensitive stand-in for the production fingerprint helper."""
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        if not path.is_file():
            raise ValueError("Portfolio configuration files are unavailable")
        relative = path.relative_to(config_directory).as_posix().encode("utf-8")
        body = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(body).to_bytes(8, "big"))
        digest.update(body)
    digest.update(repr(plan_override).encode("utf-8"))
    return digest.hexdigest()


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _configuration_metadata_function():
    """Compile the production coordinator metadata function without HA imports."""
    tree = ast.parse(COORDINATOR.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_configuration_metadata"
    )
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            function,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace = {
        "Path": Path,
        "Any": object,
        "configuration_files": calculator.configuration_files,
        "configuration_fingerprint": _fingerprint,
        "_mtime": _mtime,
    }
    exec(compile(module, str(COORDINATOR), "exec"), namespace)
    return namespace["_configuration_metadata"]


def test_configuration_files_excludes_absent_optional_exceptions(tmp_path: Path) -> None:
    config_dir = tmp_path / "portfolio-architect"
    _write_required_files(config_dir)
    paths = calculator.configuration_files(config_dir)
    assert tuple(path.name for path in paths) == bootstrap.REQUIRED_CONFIGURATION_FILES


def test_four_required_files_without_exceptions_have_valid_metadata(tmp_path: Path) -> None:
    config_dir = tmp_path / "portfolio-architect"
    _write_required_files(config_dir)
    metadata = _configuration_metadata_function()
    modified, fingerprint = metadata(config_dir, None)
    assert modified.tzinfo is not None
    assert len(fingerprint) == 64


def test_existing_exceptions_participates_in_metadata_fingerprint(tmp_path: Path) -> None:
    config_dir = tmp_path / "portfolio-architect"
    _write_required_files(config_dir)
    metadata = _configuration_metadata_function()
    _modified_without, fingerprint_without = metadata(config_dir, None)

    (config_dir / "exceptions.yaml").write_text(
        "schema_version: 1\nexceptions: []\n", encoding="utf-8"
    )
    paths = calculator.configuration_files(config_dir)
    assert paths[-1].name == "exceptions.yaml"
    _modified_with, fingerprint_with = metadata(config_dir, None)
    assert fingerprint_with != fingerprint_without


def test_removing_optional_exceptions_returns_to_four_file_fingerprint(tmp_path: Path) -> None:
    config_dir = tmp_path / "portfolio-architect"
    _write_required_files(config_dir)
    metadata = _configuration_metadata_function()
    _modified_before, fingerprint_before = metadata(config_dir, None)
    exception_path = config_dir / "exceptions.yaml"
    exception_path.write_text("schema_version: 1\nexceptions: []\n", encoding="utf-8")
    _modified_with, fingerprint_with = metadata(config_dir, None)
    exception_path.unlink()
    _modified_after, fingerprint_after = metadata(config_dir, None)
    assert fingerprint_with != fingerprint_before
    assert fingerprint_after == fingerprint_before


def test_missing_required_configuration_file_still_fails_closed(tmp_path: Path) -> None:
    config_dir = tmp_path / "portfolio-architect"
    _write_required_files(config_dir)
    (config_dir / "broker.yaml").unlink()
    metadata = _configuration_metadata_function()
    with pytest.raises(ValueError, match="Portfolio configuration files are unavailable"):
        metadata(config_dir, None)


def test_first_run_writer_output_is_directly_metadata_eligible(tmp_path: Path) -> None:
    config_dir = tmp_path / "portfolio-architect"
    bootstrap.initialize_configuration_directory(config_dir)
    position = models.Position(
        wkn="A1XB5U",
        isin="ZZ0000000010",
        name="Synthetic Global ETF",
        instrument_type="etf",
        source_type="generic_csv",
        value_eur=Decimal("1000"),
    )
    documents = bootstrap.build_configuration_documents(_first_run_plan(position))
    payload = bootstrap.write_initial_configuration(
        config_dir,
        documents,
        positions={"TESTETF1": position},
        evaluated_at=datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc),
        source_provider="generic_v1625_fixture",
        source_label="v1.62.5 fixture",
    )
    assert payload["schema_version"] == 8
    assert set(path.name for path in config_dir.iterdir()) == set(
        bootstrap.REQUIRED_CONFIGURATION_FILES
    )
    assert not (config_dir / "exceptions.yaml").exists()
    metadata = _configuration_metadata_function()
    modified, fingerprint = metadata(config_dir, None)
    assert modified.tzinfo is not None
    assert len(fingerprint) == 64
