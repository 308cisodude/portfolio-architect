from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from portfolio_architect_gateway.cash_policy import (
    InvestmentCashPolicy,
    MODE_ALL_AVAILABLE,
    MODE_CAPPED,
    load_investment_cash_policy,
    parse_policy_input,
    save_investment_cash_policy,
)
from portfolio_architect_gateway.errors import ProtocolError


def test_missing_policy_preserves_all_available_behavior(tmp_path: Path) -> None:
    policy = load_investment_cash_policy(tmp_path / "missing.json")
    assert policy.mode == MODE_ALL_AVAILABLE
    assert policy.cap_eur is None
    assert policy.authorize(Decimal("8601.53")) == Decimal("8601.53")


def test_capped_policy_is_atomic_private_and_limits_authorization(tmp_path: Path) -> None:
    path = tmp_path / "investment-cash-policy.json"
    policy = InvestmentCashPolicy(mode=MODE_CAPPED, cap_eur=Decimal("100.00"))
    save_investment_cash_policy(path, policy)
    loaded = load_investment_cash_policy(path)
    assert loaded == policy
    assert loaded.authorize(Decimal("8601.53")) == Decimal("100.00")
    assert path.stat().st_mode & 0o777 == 0o600


def test_capped_policy_fails_closed_without_a_valid_cap(tmp_path: Path) -> None:
    path = tmp_path / "investment-cash-policy.json"
    path.write_text('{"schema_version":1,"mode":"capped"}', encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(ProtocolError, match="requires a canonical EUR cap"):
        load_investment_cash_policy(path)

    with pytest.raises(ValueError, match="canonical EUR amount"):
        parse_policy_input("capped", "100,00")


def test_all_available_form_normalizes_stale_cap_away(tmp_path: Path) -> None:
    policy = parse_policy_input("all_available", "100")
    assert policy.mode == MODE_ALL_AVAILABLE
    assert policy.cap_eur is None

    path = tmp_path / "investment-cash-policy.json"
    save_investment_cash_policy(path, policy)
    assert load_investment_cash_policy(path) == policy
    assert '"cap_eur"' not in path.read_text(encoding="utf-8")


def test_persisted_all_available_policy_with_cap_still_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "investment-cash-policy.json"
    path.write_text(
        '{"schema_version":1,"mode":"all_available","cap_eur":"100"}',
        encoding="utf-8",
    )
    path.chmod(0o600)
    with pytest.raises(ProtocolError, match="must not define a cap"):
        load_investment_cash_policy(path)
