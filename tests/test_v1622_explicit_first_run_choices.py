"""Regression contracts for v1.62.5 explicit first-run choices and Generic READY UX."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
CONFIG_FLOW = COMPONENT / "config_flow.py"
GENERIC_UI = (
    ROOT
    / "home_assistant_app"
    / "portfolio_architect_gateway_import"
    / "src"
    / "portfolio_architect_gateway"
    / "generic_import_app.py"
)


def _step(source: str, name: str, next_name: str) -> str:
    return source.split(f"async def {name}", 1)[1].split(f"async def {next_name}", 1)[0]


def test_initial_plan_form_uses_optional_selector_fields_with_submission_time_requirements() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    step = _step(source, "async_step_initial_setup(", "async_step_initial_setup_instrument")
    for field in (
        "CONF_PLAN_NAME",
        "CONF_PLAN_BUDGET_AMOUNT",
        '"selected_instruments"',
        '"corridor_pp"',
        '"minimum_trade_eur"',
        '"rounding_step_eur"',
    ):
        assert f"vol.Optional({field})" in step
        assert f"vol.Required({field})" not in step
    assert "_mark_missing_explicit_fields(" in step
    assert 'errors[field] = "explicit_choice_required"' in source
    assert "synthesize selector minima/first options" in step


def test_initial_instrument_and_policy_boolean_choices_are_unanswered_yes_no_selects() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    instrument = _step(
        source,
        "async_step_initial_setup_instrument",
        "async_step_initial_setup_review",
    )
    review = _step(
        source,
        "async_step_initial_setup_review",
        "async_step_initial_setup_policy",
    )
    policy = source.split("async def async_step_initial_setup_policy", 1)[1].split(
        "@staticmethod", 1
    )[0]
    combined = instrument + review + policy
    assert "BooleanSelector(" not in combined
    assert combined.count("_explicit_yes_no_selector()") >= 8
    for field in (
        '"buy_enabled"',
        '"ucits"',
        '"normalise_targets"',
        '"ucits_required"',
        '"accumulating_preferred"',
        '"ireland_preferred"',
        '"savings_plan_required"',
        '"free_savings_plan_preferred"',
    ):
        assert f"vol.Optional({field})" in combined
    assert 'translation_key="explicit_yes_no"' in source
    assert "bool(user_input[\"ucits_required\"])" not in policy
    assert "policy_flags[\"ucits_required\"]" in policy


def test_first_run_enumerations_and_numeric_metadata_start_without_schema_defaults() -> None:
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    instrument = _step(
        source,
        "async_step_initial_setup_instrument",
        "async_step_initial_setup_review",
    )
    policy = source.split("async def async_step_initial_setup_policy", 1)[1].split(
        "@staticmethod", 1
    )[0]
    for field in (
        '"target_pct"',
        '"domicile"',
        '"distribution"',
        '"fund_currency"',
        '"ter_pct"',
        '"fund_size_eur"',
        '"metadata_source"',
    ):
        assert f"vol.Optional({field})" in instrument
    for field in ('"max_ter_pct"', '"minimum_fund_size_eur"'):
        assert f"vol.Optional({field})" in policy
    assert "default=" not in instrument
    assert "default=" not in policy


def test_bilingual_copy_and_yes_no_options_state_that_choices_are_explicit() -> None:
    for language, yes_label, no_label in (("en", "Yes", "No"), ("de", "Ja", "Nein")):
        payload = json.loads(
            (COMPONENT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        assert payload["selector"]["explicit_yes_no"]["options"] == {
            "yes": yes_label,
            "no": no_label,
        }
        assert "explicit_choice_required" in payload["options"]["error"]
        text = " ".join(
            payload["options"]["step"][step]["description"]
            for step in ("initial_setup", "initial_setup_instrument", "initial_setup_policy")
        )
        if language == "en":
            assert "explicit" in text.lower()
            assert "automatically" in text.lower()
        else:
            assert "ausdrücklich" in text.lower()
            assert "automatisch" in text.lower()


def test_generic_ready_profile_card_is_blue_while_csv_authority_remains_green() -> None:
    source = GENERIC_UI.read_text(encoding="utf-8")
    assert ".profile-card.ready{{border:2px solid #3b82f6aa;background:#3b82f612}}" in source
    assert ".profile-card.setup-required{{border:2px solid #f59e0baa;background:#f59e0b12}}" in source
    assert '<span class="ready-text">READY</span>' in source
    assert 'profile-card {"ready" if ready else "setup-required"}' in source
    # Acquisition-authority green remains independent from the profile readiness card.
    authority = (
        ROOT
        / "home_assistant_app"
        / "portfolio_architect_gateway_import"
        / "src"
        / "portfolio_architect_gateway"
        / "acquisition_presentation.py"
    ).read_text(encoding="utf-8")
    assert ".pa-method-card.active,.pa-method-card.authority{border:2px solid #22c55eaa" in authority


def test_release_version_targets_v1622() -> None:
    const = (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert 'VERSION: Final = "1.62.5"' in const
