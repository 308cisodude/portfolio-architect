"""Tests for the Home Assistant source-payload model."""

import importlib.util
from pathlib import Path
import sys

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "portfolio_architect"
    / "model.py"
)
SPEC = importlib.util.spec_from_file_location("portfolio_architect_model", MODULE_PATH)
assert SPEC and SPEC.loader
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)


def valid_item(**overrides) -> dict:
    item = {
        "fund_id": "world",
        "wkn": "A1XB5U",
        "isin": "IE00BJ0KDQ92",
        "name": "Xtrackers MSCI World UCITS ETF 1C",
        "target_pct": 100,
        "current_value_eur": 1000,
        "target_value_eur": 1000,
        "deviation_eur": 0,
        "current_pct": 100,
        "deviation_pp": 0,
        "allocation_status": "on_target",
        "buy_enabled": True,
        "proposed_buy_eur": 350,
    }
    item.update(overrides)
    return item



def valid_summary(**overrides) -> dict:
    summary = {
        "monthly_contribution_eur": 350,
        "recommended_total_eur": 350,
    }
    summary.update(overrides)
    return summary

def test_parse_valid_recommendation() -> None:
    positions = MODEL.parse_recommendations([valid_item()])
    item = positions["world"]
    assert item.target_pct == 100.0
    assert item.current_pct == 100.0
    assert item.attributes["proposed_buy_eur"] == 350.0


def test_target_coverage_detects_missing_position() -> None:
    items = [
        valid_item(target_pct=60, current_pct=100),
        valid_item(
            fund_id="robotics",
            wkn="A2ANH1",
            isin="IE00BYWZ0333",
            name="iShares Automation & Robotics UCITS ETF USD Dist",
            target_pct=40,
            current_value_eur=0,
            target_value_eur=400,
            deviation_eur=-400,
            current_pct=0,
            deviation_pp=-40,
            allocation_status="underweight",
            proposed_buy_eur=30,
        ),
    ]
    data = MODEL.parse_portfolio_data(items, valid_summary(monthly_contribution_eur=380, recommended_total_eur=380))
    assert data.coverage.total == 2
    assert data.coverage.held == 1
    assert data.coverage.missing == 1
    assert data.coverage.coverage_pct == 50.0
    assert data.coverage.missing_fund_ids == ("robotics",)


def test_duplicate_fund_id_is_rejected() -> None:
    try:
        MODEL.parse_recommendations([valid_item(), valid_item()])
    except MODEL.PortfolioArchitectDataError as err:
        assert "Duplicate fund_id" in str(err)
    else:
        raise AssertionError("duplicate fund_id was accepted")


def test_missing_target_pct_is_rejected() -> None:
    item = valid_item()
    del item["target_pct"]
    try:
        MODEL.parse_recommendations([item])
    except MODEL.PortfolioArchitectDataError as err:
        assert "target_pct" in str(err)
    else:
        raise AssertionError("missing target_pct was accepted")


def test_non_finite_number_is_rejected() -> None:
    item = valid_item(current_pct=float("nan"))
    try:
        MODEL.parse_recommendations([item])
    except MODEL.PortfolioArchitectDataError as err:
        assert "finite" in str(err)
    else:
        raise AssertionError("non-finite current_pct was accepted")


def test_unsafe_fund_id_is_rejected() -> None:
    item = valid_item(fund_id="../../unsafe")
    try:
        MODEL.parse_recommendations([item])
    except MODEL.PortfolioArchitectDataError as err:
        assert "invalid format" in str(err)
    else:
        raise AssertionError("unsafe fund_id was accepted")


def test_source_coverage_is_cross_checked() -> None:
    summary = {
        "target_positions_total": 1,
        "target_positions_held": 0,
        "target_positions_missing": 1,
        "target_position_coverage_pct": 0,
        "target_architecture_complete": False,
        "missing_target_fund_ids": ["world"],
        "missing_target_names": ["Xtrackers MSCI World UCITS ETF 1C"],
    }
    try:
        MODEL.parse_portfolio_data([valid_item()], summary)
    except MODEL.PortfolioArchitectDataError as err:
        assert "inconsistent" in str(err)
    else:
        raise AssertionError("inconsistent coverage summary was accepted")


def test_v060_monthly_plan_and_runtime_contract() -> None:
    summary = valid_summary(
        unallocated_contribution_eur=0,
        purchase_count=1,
        monthly_plan_ready=True,
        payload_schema_version=5,
        engine_version="0.6.0",
        generated_at="2026-07-29T11:00:00+00:00",
    )
    data = MODEL.parse_portfolio_data([valid_item()], summary)
    assert data.monthly_plan.ready is True
    assert data.monthly_plan.purchase_count == 1
    assert data.runtime.payload_schema_version == 5
    assert data.runtime.engine_version == "0.6.0"
    assert data.runtime.generated_at.tzinfo is not None


def test_monthly_plan_total_mismatch_is_rejected() -> None:
    try:
        MODEL.parse_portfolio_data([valid_item()], valid_summary(recommended_total_eur=349))
    except MODEL.PortfolioArchitectDataError as err:
        assert "inconsistent" in str(err)
    else:
        raise AssertionError("inconsistent monthly total was accepted")


def test_future_payload_schema_is_rejected() -> None:
    summary = valid_summary(
        unallocated_contribution_eur=0,
        purchase_count=1,
        monthly_plan_ready=True,
        payload_schema_version=999,
        engine_version="0.6.0",
        generated_at="2026-07-29T11:00:00+00:00",
    )
    try:
        MODEL.parse_portfolio_data([valid_item()], summary)
    except MODEL.PortfolioArchitectDataError as err:
        assert "Unsupported payload schema" in str(err)
    else:
        raise AssertionError("future schema version was accepted")


def valid_policy_finding(**overrides) -> dict:
    finding = {
        "rule": "free_savings_plan_preferred",
        "severity": "info",
        "status": "fail",
        "instrument_id": "IE00BJ0KDQ92",
        "message": "Zero-fee savings plan preferred",
        "observed": 1.5,
        "expected": 0,
        "exception_id": None,
        "exception_rationale": None,
        "exception_review_on": None,
    }
    finding.update(overrides)
    return finding


def test_v070_policy_contract_is_derived_and_cross_checked() -> None:
    findings = [valid_policy_finding()]
    summary = valid_summary(
        unallocated_contribution_eur=0,
        purchase_count=1,
        monthly_plan_ready=True,
        payload_schema_version=6,
        engine_version="0.7.0",
        generated_at="2026-07-29T11:00:00+00:00",
        policy_status="attention",
        failed_findings=1,
        accepted_exceptions=0,
        policy_checks_evaluated=1,
        policy_error_findings=0,
        policy_warning_findings=0,
        policy_opportunity_findings=1,
        policy_accepted_exceptions=0,
        mandatory_controls_compliant=True,
        next_exception_review_on=None,
    )
    data = MODEL.parse_portfolio_data([valid_item()], summary, findings)
    assert data.policy.status == "attention"
    assert data.policy.mandatory_controls_compliant is True
    assert data.policy.opportunities == 1
    finding = data.policy.findings["world:free_savings_plan_preferred"]
    assert finding.entity_state == "opportunity"
    assert finding.attributes["observed"] == 1.5


def test_accepted_exception_uses_translation_token_and_review_date() -> None:
    findings = [
        valid_policy_finding(
            rule="accumulating_preferred",
            severity="warning",
            status="accepted_exception",
            observed="distributing",
            expected="accumulating",
            exception_id="robotics_distributing_share_class",
            exception_rationale="Bounded rationale",
            exception_review_on="2027-07-27",
        )
    ]
    data = MODEL.parse_portfolio_data([valid_item()], valid_summary(), findings)
    finding = data.policy.findings["world:accumulating_preferred"]
    assert finding.entity_state == "accepted_exception"
    assert finding.attributes["observed"] == "distributing"
    assert finding.attributes["exception_rationale"] == "robotics_distributing_share_class"
    assert finding.exception_detail_attributes == {
        "fund_name": "Xtrackers MSCI World UCITS ETF 1C",
        "rule": "accumulating_preferred",
        "observed": "distributing",
        "expected": "accumulating",
        "review_on": "2027-07-27",
    }
    assert "exception_rationale" not in finding.exception_detail_attributes
    assert data.policy.next_exception_review_on.isoformat() == "2027-07-27"


def test_schema_6_requires_policy_findings() -> None:
    summary = valid_summary(
        unallocated_contribution_eur=0,
        purchase_count=1,
        monthly_plan_ready=True,
        payload_schema_version=6,
        engine_version="0.7.0",
        generated_at="2026-07-29T11:00:00+00:00",
    )
    try:
        MODEL.parse_portfolio_data([valid_item()], summary)
    except MODEL.PortfolioArchitectDataError as err:
        assert "requires a policy_findings" in str(err)
    else:
        raise AssertionError("schema 6 accepted a missing policy_findings attribute")


def test_duplicate_policy_finding_is_rejected() -> None:
    findings = [valid_policy_finding(), valid_policy_finding()]
    try:
        MODEL.parse_portfolio_data([valid_item()], valid_summary(), findings)
    except MODEL.PortfolioArchitectDataError as err:
        assert "Duplicate policy finding" in str(err)
    else:
        raise AssertionError("duplicate policy finding was accepted")


def test_unknown_policy_rule_is_rejected() -> None:
    try:
        MODEL.parse_portfolio_data(
            [valid_item()], valid_summary(), [valid_policy_finding(rule="unsafe_rule")]
        )
    except MODEL.PortfolioArchitectDataError as err:
        assert "rule is invalid" in str(err)
    else:
        raise AssertionError("unknown policy rule was accepted")


def test_v080_allocation_and_review_contract() -> None:
    findings = [
        valid_policy_finding(
            rule="accumulating_preferred",
            severity="warning",
            status="accepted_exception",
            observed="distributing",
            expected="accumulating",
            exception_id="robotics_distributing_share_class",
            exception_rationale="Bounded rationale",
            exception_approved_on="2026-07-27",
            exception_last_reviewed_on=None,
            exception_review_on="2027-07-27",
        )
    ]
    summary = valid_summary(
        current_portfolio_value_eur=1000,
        allocation_corridor_pp=1,
        underweight_positions=0,
        on_target_positions=1,
        overweight_positions=0,
        portfolio_allocation_on_target=True,
        unallocated_contribution_eur=0,
        purchase_count=1,
        monthly_plan_ready=True,
        payload_schema_version=7,
        engine_version="0.8.0",
        generated_at="2026-07-29T11:00:00+00:00",
        policy_status="compliant",
        failed_findings=0,
        accepted_exceptions=1,
        policy_checks_evaluated=1,
        policy_error_findings=0,
        policy_warning_findings=0,
        policy_opportunity_findings=0,
        policy_accepted_exceptions=1,
        mandatory_controls_compliant=True,
        next_exception_review_on="2027-07-27",
        exception_review_overdue=False,
        overdue_exception_reviews=0,
        oldest_overdue_exception_review_on=None,
        last_exception_decision_on="2026-07-27",
    )
    data = MODEL.parse_portfolio_data([valid_item()], summary, findings)
    assert data.allocation.allocation_on_target is True
    assert data.allocation.portfolio_value_eur == 1000
    assert data.policy.review_overdue is False
    assert data.policy.next_exception_review_on.isoformat() == "2027-07-27"
    assert data.policy.last_exception_decision_on.isoformat() == "2026-07-27"


def test_overdue_review_is_not_reported_as_next_review() -> None:
    findings = [
        valid_policy_finding(
            rule="accumulating_preferred",
            severity="warning",
            status="accepted_exception",
            observed="distributing",
            expected="accumulating",
            exception_id="robotics_distributing_share_class",
            exception_rationale="Bounded rationale",
            exception_approved_on="2026-07-27",
            exception_review_on="2027-07-27",
        )
    ]
    summary = valid_summary(
        current_portfolio_value_eur=1000,
        allocation_corridor_pp=1,
        underweight_positions=0,
        on_target_positions=1,
        overweight_positions=0,
        portfolio_allocation_on_target=True,
        unallocated_contribution_eur=0,
        purchase_count=1,
        monthly_plan_ready=True,
        payload_schema_version=7,
        engine_version="0.8.0",
        generated_at="2027-07-28T11:00:00+00:00",
        policy_status="compliant",
        failed_findings=0,
        accepted_exceptions=1,
        policy_checks_evaluated=1,
        policy_error_findings=0,
        policy_warning_findings=0,
        policy_opportunity_findings=0,
        policy_accepted_exceptions=1,
        mandatory_controls_compliant=True,
        next_exception_review_on=None,
        exception_review_overdue=True,
        overdue_exception_reviews=1,
        oldest_overdue_exception_review_on="2027-07-27",
        last_exception_decision_on="2026-07-27",
    )
    data = MODEL.parse_portfolio_data([valid_item()], summary, findings)
    assert data.policy.next_exception_review_on is None
    assert data.policy.review_overdue is True
    assert data.policy.oldest_overdue_review_on.isoformat() == "2027-07-27"
