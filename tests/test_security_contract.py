"""Security-by-design contract tests."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
MODEL = ROOT / "custom_components" / "portfolio_architect" / "model.py"
ENGINE_DIR = ROOT / "custom_components" / "portfolio_architect" / "engine"
ENGINE = ENGINE_DIR / "rebalance.py"
DIAGNOSTICS = ROOT / "custom_components" / "portfolio_architect" / "diagnostics.py"


def test_input_sizes_and_identifiers_are_bounded() -> None:
    model = MODEL.read_text(encoding="utf-8")
    engine = ENGINE.read_text(encoding="utf-8")
    targets = (ENGINE_DIR / "targets.py").read_text(encoding="utf-8")
    assert "MAX_POSITIONS = 32" in model
    assert "MAX_HOLDINGS = 512" in model
    assert "^[a-z0-9_]{1,64}$" in model
    assert "MAX_TARGETS = 32" in targets
    assert "^[a-z0-9_]{1,64}$" in targets


def test_diagnostics_omit_financial_values_and_fund_names() -> None:
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    assert '"missing_fund_ids"' in diagnostics
    assert '"missing_names"' not in diagnostics
    assert '"current_value_eur"' not in diagnostics
    assert '"proposed_buy_eur"' not in diagnostics


def test_no_dynamic_code_execution_or_shell_calls() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [MODEL, *ENGINE_DIR.glob("*.py")]
    )
    assert "eval(" not in sources
    assert "exec(" not in sources
    assert "subprocess" not in sources
    assert "os.system" not in sources


def test_monthly_money_and_schema_are_bounded() -> None:
    model = MODEL.read_text(encoding="utf-8")
    assert "MAX_MONEY_EUR = 1_000_000_000.0" in model
    assert "MAX_MONTHLY_CONTRIBUTION_EUR = 10_000_000.0" in model
    assert "MAX_SUPPORTED_PAYLOAD_SCHEMA = 8" in model
    assert "recommended > contribution + 0.01" in model
    assert "Unsupported payload schema version" in model
    assert "MAX_POLICY_FINDINGS = 256" in model
    assert "MAX_EXCEPTION_RATIONALE_LENGTH = 1200" in model


def test_local_file_sizes_and_paths_are_bounded() -> None:
    generic_csv = (
        ROOT / "home_assistant_app" / "portfolio_architect_gateway_import" / "src"
        / "portfolio_architect_gateway" / "generic_csv.py"
    ).read_text(encoding="utf-8")
    yaml_source = (ENGINE_DIR / "io.py").read_text(encoding="utf-8")
    source = (ROOT / "custom_components" / "portfolio_architect" / "source.py").read_text(encoding="utf-8")
    assert "MAX_CSV_FILE_BYTES: Final = 10 * 1024 * 1024" in generic_csv
    assert not (ENGINE_DIR / "importers.py").exists()
    assert "_MAX_YAML_FILE_SIZE = 1024 * 1024" in yaml_source
    assert "_MAX_RELATIVE_PATH_LENGTH = 255" in source
    assert "Configured paths must remain inside" in source
