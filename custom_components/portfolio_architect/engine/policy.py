from __future__ import annotations
from datetime import date, timedelta
from typing import Any
from .models import Finding


def _severity(policy: dict[str, Any], rule: str) -> str:
    return policy.get("severities", {}).get(rule, "warning")


def _active_exceptions(
    exceptions_doc: dict[str, Any] | None,
    *,
    evaluated_on: date,
) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in (exceptions_doc or {}).get("exceptions", []):
        if item.get("status") != "accepted":
            continue
        expires_on = item.get("expires_on")
        if expires_on:
            try:
                if date.fromisoformat(str(expires_on)) < evaluated_on:
                    continue
            except ValueError:
                continue
        instrument_id = item.get("instrument_id")
        rule = item.get("rule")
        if instrument_id and rule:
            result[(str(instrument_id), str(rule))] = item
    return result


def evaluate(
    portfolio_doc: dict[str, Any],
    policy_doc: dict[str, Any],
    instruments_doc: dict[str, Any],
    broker_doc: dict[str, Any],
    exceptions_doc: dict[str, Any] | None = None,
    *,
    evaluated_on: date | None = None,
) -> list[Finding]:
    p = policy_doc["policy"]
    rules = p["rules"]
    instruments = instruments_doc.get("instruments", {})
    broker = broker_doc.get("broker", {})
    plans = broker.get("savings_plans", {})
    verification_days_raw = broker.get("fee_verification_max_age_days")
    verification_days: int | None = None
    if verification_days_raw is not None:
        if (
            isinstance(verification_days_raw, bool)
            or not isinstance(verification_days_raw, int)
            or not 1 <= verification_days_raw <= 3650
        ):
            raise ValueError("fee_verification_max_age_days must be an integer from 1 to 3650")
        verification_days = verification_days_raw
    exceptions = _active_exceptions(
        exceptions_doc, evaluated_on=evaluated_on or date.today()
    )
    findings: list[Finding] = []

    for fund in portfolio_doc["portfolio"]["allocation"]:
        # Policy applies only to positive-weight instruments in the current plan.
        if float(fund.get("target_pct", 0)) <= 0:
            continue
        isin = fund["isin"]
        meta = instruments.get(isin)
        if not meta:
            findings.append(Finding("metadata", "error", "fail", isin, "No instrument metadata configured"))
            continue

        checks = [
            ("ucits_required", not rules.get("ucits_required") or meta.get("ucits") is True, meta.get("ucits"), True, "ETF must be UCITS"),
            ("accumulating_preferred", not rules.get("accumulating_preferred") or meta.get("distribution") == "accumulating", meta.get("distribution"), "accumulating", "Accumulating share class preferred"),
            ("ireland_preferred", not rules.get("ireland_preferred") or meta.get("domicile") == "IE", meta.get("domicile"), "IE", "Irish domicile preferred"),
            ("max_ter_pct", meta.get("ter_pct") is not None and float(meta["ter_pct"]) <= float(rules["max_ter_pct"]), meta.get("ter_pct"), rules["max_ter_pct"], "TER exceeds policy threshold"),
            ("minimum_fund_size_eur", meta.get("fund_size_eur") is not None and float(meta["fund_size_eur"]) >= float(rules["minimum_fund_size_eur"]), meta.get("fund_size_eur"), rules["minimum_fund_size_eur"], "Fund size is below threshold or unverified"),
        ]
        if fund.get("buy_enabled", True):
            plan = plans.get(isin, {})
            checks.extend([
                ("savings_plan_required", not rules.get("savings_plan_required") or plan.get("available") is True, plan.get("available"), True, "Comdirect savings plan required"),
                ("free_savings_plan_preferred", not rules.get("free_savings_plan_preferred") or plan.get("fee_pct") == 0, plan.get("fee_pct"), 0, "Zero-fee savings plan preferred"),
            ])
            if verification_days is not None:
                verified_on_raw = plan.get("fee_verified_at")
                source_raw = plan.get("fee_source")
                verified_on = None
                if isinstance(verified_on_raw, date):
                    verified_on = verified_on_raw
                    verified_on_raw = verified_on.isoformat()
                elif isinstance(verified_on_raw, str):
                    try:
                        verified_on = date.fromisoformat(verified_on_raw)
                    except ValueError:
                        verified_on = None
                source_valid = (
                    isinstance(source_raw, str)
                    and 1 <= len(source_raw.strip()) <= 80
                    and all(ord(char) >= 32 and ord(char) != 127 for char in source_raw)
                )
                cutoff = (evaluated_on or date.today()) - timedelta(days=verification_days)
                verification_current = (
                    verified_on is not None
                    and verified_on <= (evaluated_on or date.today())
                    and verified_on >= cutoff
                    and source_valid
                )
                checks.append((
                    "savings_plan_fee_verified_recently",
                    verification_current,
                    verified_on_raw if verified_on_raw else "missing",
                    f"within_{verification_days}_days",
                    "Savings-plan fee verification is missing or stale",
                ))

        for rule, passed, observed, expected, message in checks:
            if passed:
                findings.append(Finding(rule, _severity(p, rule), "pass", isin, message, observed, expected))
                continue

            exception = exceptions.get((isin, rule))
            if exception:
                findings.append(Finding(
                    rule,
                    _severity(p, rule),
                    "accepted_exception",
                    isin,
                    message,
                    observed,
                    expected,
                    exception_id=exception.get("id"),
                    exception_rationale=exception.get("rationale"),
                    exception_approved_on=str(exception.get("approved_on")) if exception.get("approved_on") else None,
                    exception_last_reviewed_on=(
                        str(exception.get("last_reviewed_on"))
                        if exception.get("last_reviewed_on")
                        else None
                    ),
                    exception_review_on=str(exception.get("review_on")) if exception.get("review_on") else None,
                ))
            else:
                findings.append(Finding(rule, _severity(p, rule), "fail", isin, message, observed, expected))
    return findings
