"""v1.1 self-contained integration architecture contract tests."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"


def test_engine_is_bundled_inside_custom_component() -> None:
    engine = COMPONENT / "engine"
    assert (engine / "calculator.py").is_file()
    assert (engine / "io.py").is_file()
    assert (engine / "rebalance.py").is_file()
    assert not (ROOT / "portfolio-architect").exists()


def test_gateway_coordinator_preserves_self_contained_calculation_runtime() -> None:
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    setup = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "calculate_portfolio_payload" in coordinator
    assert "async_add_executor_job" in coordinator
    assert "SOURCE_TYPE_LOCAL_FILES" not in coordinator
    assert "DEFAULT_UPDATE_INTERVAL_MINUTES" in coordinator
    assert "Cannot migrate Portfolio Architect to schema 12 while local CSV" in setup


def test_config_flow_is_gateway_only_but_retains_safe_reconfigure() -> None:
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    source = (COMPONENT / "source.py").read_text(encoding="utf-8")
    setup = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "CONF_CSV_PATH" not in flow
    assert "async_step_reconfigure" in flow
    assert "async_update_reload_and_abort" in flow
    assert "resolve_local_source_paths" not in flow
    assert "SOURCE_TYPE_LOCAL_FILES" not in source
    assert "Cannot migrate Portfolio Architect to schema 12 while local CSV" in setup


def test_snapshot_timestamp_comes_from_csv_mtime() -> None:
    calculator = (COMPONENT / "engine" / "calculator.py").read_text(encoding="utf-8")
    coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
    assert "evaluated_at=max(item.generated_at for item in sources)" in coordinator
    assert "datetime.fromtimestamp(path.stat().st_mtime" in calculator
    assert '"generated_at": timestamp.isoformat()' in calculator


def test_custom_integration_uses_runtime_translations() -> None:
    assert not (COMPONENT / "strings.json").exists()
    assert (COMPONENT / "translations" / "en.json").is_file()
    assert (COMPONENT / "translations" / "de.json").is_file()


def test_service_manifest_allows_hassio_flow_but_manual_setup_blocks_duplicates() -> None:
    import json

    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert manifest["integration_type"] == "service"
    assert "single_config_entry" not in manifest
    assert 'INSTANCE_UNIQUE_ID: Final = "portfolio_architect"' in const
    assert "await self.async_set_unique_id(INSTANCE_UNIQUE_ID)" in flow
    assert "if self.hass.config_entries.async_entries(DOMAIN):" in flow
    assert 'return self.async_abort(reason="already_configured")' in flow
    assert "self._abort_if_unique_id_configured()" in flow
    assert "local:{cleaned[CONF_CSV_PATH]}" not in flow


def test_duplicate_migration_never_edits_storage_or_guesses_a_winner() -> None:
    setup = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "len(domain_entries) == 1" in setup
    assert "Never" in setup and "guess" in setup
    assert ".storage must not be edited" in setup
