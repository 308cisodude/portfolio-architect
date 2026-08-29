"""Regression coverage for the v1.35.4 locale-tolerant cash-input hotfix."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
GATEWAY_SRC = ROOT / "gateway" / "src"
if str(GATEWAY_SRC) not in sys.path:
    sys.path.insert(0, str(GATEWAY_SRC))

from portfolio_architect_gateway.cash_policy import (  # noqa: E402
    MODE_CAPPED,
    MODE_RETAIN,
    parse_policy_input,
)


@pytest.mark.parametrize(
    ("mode", "token", "expected"),
    [
        (MODE_RETAIN, "1024,00", Decimal("1024.00")),
        (MODE_RETAIN, "1.024,00", Decimal("1024.00")),
        (MODE_RETAIN, "1,024.00", Decimal("1024.00")),
        (MODE_CAPPED, "1024,00", Decimal("1024.00")),
        (MODE_CAPPED, "1\u202f024,00", Decimal("1024.00")),
    ],
)
def test_live_observed_cash_amount_formats_are_accepted(mode: str, token: str, expected: Decimal) -> None:
    policy = (
        parse_policy_input(mode, token, "")
        if mode == MODE_CAPPED
        else parse_policy_input(mode, "", token)
    )
    amount = policy.cap_eur if mode == MODE_CAPPED else policy.retain_eur
    assert amount == expected


def test_gateway_source_mirrors_keep_locale_parser_and_bounded_error_ux_aligned() -> None:
    common = ROOT / "gateway" / "src" / "portfolio_architect_gateway"
    app = ROOT / "home_assistant_app" / "portfolio_architect_gateway_comdirect" / "src" / "portfolio_architect_gateway"
    for relative in ("cash_policy.py", "app.py"):
        assert (common / relative).read_bytes() == (app / relative).read_bytes()

    source = (common / "app.py").read_text(encoding="utf-8")
    assert './?cash_policy_error=invalid_amount' in source
    assert "Could not save the authorization policy" in source
    assert "1024,00 or 1024.00" in source
    assert "except ValueError:" in source
