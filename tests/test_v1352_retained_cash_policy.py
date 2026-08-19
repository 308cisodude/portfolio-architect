"""Regression coverage for v1.35.4 retained-cash authorization."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
GATEWAY_SRC = ROOT / "gateway" / "src"
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
for candidate in (GATEWAY_SRC, COMPONENT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from portfolio_architect_gateway.cash_policy import (  # noqa: E402
    InvestmentCashPolicy,
    MODE_ALL_AVAILABLE,
    MODE_CAPPED,
    MODE_RETAIN,
    load_investment_cash_policy,
    parse_policy_input,
    save_investment_cash_policy,
)
from portfolio_architect_gateway.models import InvestmentCash, PortfolioSnapshot, Position, validate_snapshot  # noqa: E402
from engine.rest import _parse_investment_cash  # noqa: E402


def test_retained_cash_authorizes_only_amount_above_reserve() -> None:
    policy = InvestmentCashPolicy(mode=MODE_RETAIN, retain_eur=Decimal("1000"))
    assert policy.authorize(Decimal("3598.97")) == Decimal("2598.97")
    assert policy.authorize(Decimal("1000")) == Decimal("0")
    assert policy.authorize(Decimal("500")) == Decimal("0")


def test_all_three_policies_never_authorize_outside_eligible_range() -> None:
    policies = (
        InvestmentCashPolicy(mode=MODE_ALL_AVAILABLE),
        InvestmentCashPolicy(mode=MODE_CAPPED, cap_eur=Decimal("1000")),
        InvestmentCashPolicy(mode=MODE_RETAIN, retain_eur=Decimal("1000")),
    )
    for eligible in (Decimal("0"), Decimal("500"), Decimal("1000"), Decimal("3598.97")):
        for policy in policies:
            authorized = policy.authorize(eligible)
            assert Decimal("0") <= authorized <= eligible


def test_private_policy_schema2_round_trip_and_schema1_compatibility(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    retained = InvestmentCashPolicy(mode=MODE_RETAIN, retain_eur=Decimal("750.50"))
    save_investment_cash_policy(path, retained)
    assert '"schema_version":2' in path.read_text(encoding="utf-8")
    assert load_investment_cash_policy(path) == retained

    path.write_text('{"schema_version":1,"mode":"capped","cap_eur":"100"}', encoding="utf-8")
    path.chmod(0o600)
    legacy = load_investment_cash_policy(path)
    assert legacy.mode == MODE_CAPPED
    assert legacy.cap_eur == Decimal("100")


def test_form_parser_canonicalizes_mutually_exclusive_modes() -> None:
    assert parse_policy_input("all_available", "999", "888") == InvestmentCashPolicy()
    assert parse_policy_input("capped", "100", "888") == InvestmentCashPolicy(mode=MODE_CAPPED, cap_eur=Decimal("100"))
    assert parse_policy_input("retain", "999", "250") == InvestmentCashPolicy(mode=MODE_RETAIN, retain_eur=Decimal("250"))


def test_gateway_and_rest_contract_validate_exact_retained_cash_math() -> None:
    now = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
    cash = InvestmentCash(
        account_balance_eur=Decimal("3598.97"),
        eligible_eur=Decimal("3598.97"),
        authorized_eur=Decimal("2598.97"),
        policy="retain",
        as_of=now,
        retain_eur=Decimal("1000"),
    )
    snapshot = PortfolioSnapshot(
        generated_at=now,
        positions=(Position(identifier="ZZ0001", name="Synthetic ETF", market_value_eur=Decimal("1")),),
        investment_reserve_eur=Decimal("2598.97"),
        investment_reserve_as_of=now,
        investment_cash=cash,
    )
    validated = validate_snapshot(snapshot)
    wire = validated.investment_cash.as_dict()
    assert wire["policy"] == "retain"
    assert wire["retain_eur"] == "1000"
    parsed = _parse_investment_cash(wire, now=now)
    assert parsed is not None
    assert parsed.authorized_eur == Decimal("2598.97")
    assert parsed.retain_eur == Decimal("1000")

    broken = dict(wire)
    broken["authorized_eur"] = "2599"
    with pytest.raises(ValueError, match="retained-cash authorization is inconsistent"):
        _parse_investment_cash(broken, now=now)
