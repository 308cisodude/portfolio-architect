"""v1.18.1 options-flow, reserve-transition, and classification hotfixes."""

from datetime import datetime, timezone
from decimal import Decimal
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
sys.path.insert(0, str(COMPONENT))

from engine.calculator import calculate_portfolio_payload_from_positions  # noqa: E402
from engine.importers import CsvSourceConfig, PROVIDER_COMDIRECT, read_positions  # noqa: E402
from engine.rest import PROVIDER_LOCAL_REST_JSON  # noqa: E402


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def test_execution_options_use_two_serialization_safe_steps() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    policy = _function(tree, "_execution_policy_schema")
    fees = _function(tree, "_execution_fees_schema")
    rendered = ast.unparse(ast.Module(body=[policy, fees], type_ignores=[]))

    # The failing v1.16.0/v1.16.1 form used selector-specific unrestricted
    # numeric steps. The replacement deliberately uses only core Voluptuous
    # primitives that Home Assistant has serialized for years.
    assert "NumberSelector" not in rendered
    assert "SelectSelector" not in rendered
    assert '"any"' not in rendered
    assert "vol.In" in rendered
    assert "vol.Coerce" in rendered
    assert "vol.Range" in rendered

    assert "async def async_step_execution_fees" in source
    assert 'step_id="execution_fees"' in source
    assert 'last_step=True' in source


def test_venue_fee_basis_points_preserve_exact_percentage_contract() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")

    assert 'CONF_MANUAL_VENUE_FEE_BPS = "manual_venue_fee_bps"' in source
    assert 'venue_fee_pct * Decimal("100")' in source
    assert ') / Decimal("100")' in source
    assert "CONF_MANUAL_VENUE_FEE_PCT: float(venue_fee_pct)" in source

    # UI value 0.25 bps equals the existing stored execution value 0.0025%.
    assert Decimal("0.25") / Decimal("100") == Decimal("0.0025")


def test_execution_step_translations_are_complete_in_both_languages() -> None:
    import json

    for language in ("en", "de"):
        translation = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text()
        )
        steps = translation["options"]["step"]
        assert "execution" in steps
        assert "execution_fees" in steps
        fee_data = steps["execution_fees"]["data"]
        assert "manual_venue_fee_bps" in fee_data
        assert len(fee_data) == 7


def test_disabled_cost_aware_execution_ignores_gateway_reserve() -> None:
    positions = read_positions(
        ROOT / "tests" / "fixtures" / "comdirect-depot-sanitized.csv",
        CsvSourceConfig(provider=PROVIDER_COMDIRECT),
    )
    payload = calculate_portfolio_payload_from_positions(
        positions,
        ROOT / "examples" / "current-plan",
        evaluated_at=datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc),
        plan_override={
            "enabled": False,
            "execution": {
                "enabled": False,
                "reserve_mode": "gateway_balance",
            },
        },
        source_provider=PROVIDER_LOCAL_REST_JSON,
        source_label="Comdirect REST",
        source_metadata={
            "investment_reserve_eur": Decimal("1.46"),
            "investment_reserve_as_of": "2026-08-02T07:59:00+00:00",
        },
    )

    summary = payload["summary"]
    assert summary["execution_policy"] == "legacy_distribution"
    assert summary["available_investment_reserve_eur"] == Decimal("350")
    assert summary["investment_reserve_source"] == "contribution"
    assert summary["recommended_total_eur"] == Decimal("350")
    assert summary["estimated_cash_outlay_eur"] == Decimal("350")


def test_calculation_failures_are_not_mislabelled_as_supplemental_source_failures() -> None:
    source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

    assert "class SupplementalPortfolioSourceError" in source
    assert 'f"Supplemental portfolio source failed: {err}"' in source
    assert 'f"Portfolio calculation failed: {err}"' in source
    assert "except SupplementalPortfolioSourceError as err:" in source


def test_v1162_version_metadata_is_aligned() -> None:
    assert 'version = "1.38.0"' in (ROOT / "pyproject.toml").read_text()
