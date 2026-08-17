from __future__ import annotations

from datetime import date
from typing import Any

from .execution import preferred_savings_plan_route
from .models import Finding


def _severity(policy: dict[str, Any], rule: str) -> str:
    return policy.get("severities", {}).get(rule, "warning")


def _active_exceptions(
    exceptions_doc: dict[str, Any] | None,
    *,
    evaluated_on: date,
) -> dict[tuple[str, str], dict[str, Any]]:
    document = exceptions_doc or {}
    schema_version = document.get("schema_version", 1)
    if schema_version not in {1, 2}:
        raise ValueError("exceptions schema_version is unsupported")
    items = document.get("exceptions", [])
    if not isinstance(items, list) or len(items) > 128:
        raise ValueError("exceptions must be a bounded list")

    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("exception entry must be an object")
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
        if not instrument_id or not rule:
            continue
        assumptions = item.get("assumptions")
        if assumptions is not None:
            if schema_version < 2:
                raise ValueError("exception assumptions require schema_version 2")
            if not isinstance(assumptions, dict) or set(assumptions) != {
                "preferred_execution_provider"
            }:
                raise ValueError("exception assumptions are invalid")
            provider = assumptions.get("preferred_execution_provider")
            if (
                not isinstance(provider, str)
                or not provider
                or len(provider) > 32
                or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_" for char in provider)
            ):
                raise ValueError("exception preferred_execution_provider is invalid")
        key = (str(instrument_id), str(rule))
        if key in result:
            raise ValueError("duplicate active exception for instrument/rule")
        result[key] = item
    return result


def _exception_route_review(
    exception: dict[str, Any],
    *,
    instrument_id: str,
    preferred_execution_providers: dict[str, str | None],
) -> tuple[str, str, str | None] | None:
    """Return a review reason when an accepted route assumption no longer holds."""

    assumptions = exception.get("assumptions")
    if not isinstance(assumptions, dict):
        return None
    expected = assumptions.get("preferred_execution_provider")
    if not isinstance(expected, str):
        return None
    observed = preferred_execution_providers.get(instrument_id)
    if observed == expected:
        return None
    return ("preferred_execution_provider_changed", expected, observed)


def evaluate(
    portfolio_doc: dict[str, Any],
    policy_doc: dict[str, Any],
    instruments_doc: dict[str, Any],
    broker_doc: dict[str, Any],
    exceptions_doc: dict[str, Any] | None = None,
    *,
    evaluated_on: date | None = None,
    preferred_execution_providers: dict[str, str | None] | None = None,
) -> list[Finding]:
    p = policy_doc["policy"]
    rules = p["rules"]
    instruments = instruments_doc.get("instruments", {})
    analysis_date = evaluated_on or date.today()
    exceptions = _active_exceptions(exceptions_doc, evaluated_on=analysis_date)
    preferred_execution_providers = dict(preferred_execution_providers or {})
    findings: list[Finding] = []

    for fund in portfolio_doc["portfolio"]["allocation"]:
        # Policy applies only to positive-weight instruments in the current plan.
        if float(fund.get("target_pct", 0)) <= 0:
            continue
        isin = fund["isin"]
        meta = instruments.get(isin)
        if not meta:
            findings.append(
                Finding("metadata", "error", "fail", isin, "No instrument metadata configured")
            )
            continue

        checks = [
            ("ucits_required", not rules.get("ucits_required") or meta.get("ucits") is True, meta.get("ucits"), True, "ETF must be UCITS"),
            ("accumulating_preferred", not rules.get("accumulating_preferred") or meta.get("distribution") == "accumulating", meta.get("distribution"), "accumulating", "Accumulating share class preferred"),
            ("ireland_preferred", not rules.get("ireland_preferred") or meta.get("domicile") == "IE", meta.get("domicile"), "IE", "Irish domicile preferred"),
            ("max_ter_pct", meta.get("ter_pct") is not None and float(meta["ter_pct"]) <= float(rules["max_ter_pct"]), meta.get("ter_pct"), rules["max_ter_pct"], "TER exceeds policy threshold"),
            ("minimum_fund_size_eur", meta.get("fund_size_eur") is not None and float(meta["fund_size_eur"]) >= float(rules["minimum_fund_size_eur"]), meta.get("fund_size_eur"), rules["minimum_fund_size_eur"], "Fund size is below threshold or unverified"),
        ]
        if fund.get("buy_enabled", True):
            best_plan = preferred_savings_plan_route(
                broker_doc, isin, evaluated_on=analysis_date
            )
            plan_available = best_plan is not None
            best_fee = best_plan.fee_pct if best_plan is not None else None
            checks.extend(
                [
                    (
                        "savings_plan_required",
                        not rules.get("savings_plan_required") or plan_available,
                        plan_available,
                        True,
                        "Savings plan required from at least one fresh execution provider",
                    ),
                    (
                        "free_savings_plan_preferred",
                        not rules.get("free_savings_plan_preferred")
                        or (best_fee is not None and best_fee == 0),
                        float(best_fee) if best_fee is not None else None,
                        0,
                        "Zero-fee savings plan preferred across eligible execution providers",
                    ),
                ]
            )

        for rule, passed, observed, expected, message in checks:
            if passed:
                findings.append(
                    Finding(rule, _severity(p, rule), "pass", isin, message, observed, expected)
                )
                continue

            exception = exceptions.get((isin, rule))
            if exception:
                review = _exception_route_review(
                    exception,
                    instrument_id=isin,
                    preferred_execution_providers=preferred_execution_providers,
                )
                common = dict(
                    rule=rule,
                    severity=_severity(p, rule),
                    instrument_id=isin,
                    message=message,
                    observed=observed,
                    expected=expected,
                    exception_id=exception.get("id"),
                    exception_rationale=exception.get("rationale"),
                    exception_approved_on=(
                        str(exception.get("approved_on"))
                        if exception.get("approved_on")
                        else None
                    ),
                    exception_last_reviewed_on=(
                        str(exception.get("last_reviewed_on"))
                        if exception.get("last_reviewed_on")
                        else None
                    ),
                    exception_review_on=(
                        str(exception.get("review_on"))
                        if exception.get("review_on")
                        else None
                    ),
                )
                if review is None:
                    findings.append(Finding(status="accepted_exception", **common))
                else:
                    reason, expected_provider, observed_provider = review
                    findings.append(
                        Finding(
                            status="review_required",
                            exception_review_reason=reason,
                            exception_expected_provider=expected_provider,
                            exception_observed_provider=observed_provider,
                            **common,
                        )
                    )
            else:
                findings.append(
                    Finding(rule, _severity(p, rule), "fail", isin, message, observed, expected)
                )
    return findings
