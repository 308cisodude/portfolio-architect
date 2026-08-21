"""v1.41.0 shared Gateway human-input validation contracts."""

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
    InvestmentCashPolicy,
    MODE_CAPPED,
    MODE_RETAIN,
    parse_policy_input,
)
from portfolio_architect_gateway.human_input import (  # noqa: E402
    HumanInputError,
    parse_bounded_integer,
    parse_human_eur,
    parse_human_percentage,
    parse_human_quantity,
)


def test_shared_numeric_primitives_accept_only_unambiguous_human_forms() -> None:
    assert parse_human_eur("1.024,00") == Decimal("1024.00")
    assert parse_human_eur("1,024.00") == Decimal("1024.00")
    assert parse_human_eur("1\u202f024,50") == Decimal("1024.50")
    assert parse_human_eur("1’024.50") == Decimal("1024.50")

    assert parse_human_percentage("12,5") == Decimal("12.5")
    assert parse_human_percentage("12.345") == Decimal("12.345")

    assert parse_human_quantity("1 234,5678", maximum=Decimal("1000000")) == Decimal("1234.5678")
    assert parse_human_quantity("1,234.5678", maximum=Decimal("1000000")) == Decimal("1234.5678")
    with pytest.raises(HumanInputError):
        parse_human_quantity("1,234", maximum=Decimal("1000000"))

    assert parse_bounded_integer("1.024", minimum=0, maximum=5000) == 1024
    assert parse_bounded_integer("1 024", minimum=0, maximum=5000) == 1024


def test_shared_numeric_errors_are_bounded_and_never_echo_rejected_tokens() -> None:
    rejected = (
        "-1",
        "+1",
        "1e3",
        "EUR 100",
        "1,23,456",
        "1.2.3",
        "0x10",
        "9" * 80,
    )
    for token in rejected:
        with pytest.raises(HumanInputError) as exc_info:
            parse_human_eur(token, label="Cash reserve")
        message = str(exc_info.value)
        assert token not in message
        assert len(message) <= 120
        assert "Cash reserve" in message


def test_shared_numeric_primitives_apply_common_bounds_before_field_semantics() -> None:
    with pytest.raises(HumanInputError, match="between 0 and 100"):
        parse_human_percentage("100,01")
    with pytest.raises(HumanInputError, match="between 1 and 12"):
        parse_bounded_integer("13", minimum=1, maximum=12)
    with pytest.raises(HumanInputError, match="between 0 and 10"):
        parse_human_quantity("10,1", maximum=Decimal("10"))


def test_comdirect_cash_policy_migrates_to_shared_eur_primitive_without_behavior_change() -> None:
    samples = (
        (MODE_RETAIN, "1024", Decimal("1024")),
        (MODE_RETAIN, "1024.00", Decimal("1024.00")),
        (MODE_RETAIN, "1024,00", Decimal("1024.00")),
        (MODE_RETAIN, "1.024,00", Decimal("1024.00")),
        (MODE_RETAIN, "1,024.00", Decimal("1024.00")),
        (MODE_RETAIN, "1\u00a0024,00", Decimal("1024.00")),
        (MODE_RETAIN, "1\u202f024,00", Decimal("1024.00")),
        (MODE_RETAIN, "1'024,00", Decimal("1024.00")),
        (MODE_RETAIN, "1’024,00", Decimal("1024.00")),
        (MODE_CAPPED, "1.024,00", Decimal("1024.00")),
    )
    for mode, token, expected in samples:
        policy = (
            parse_policy_input(mode, token, "")
            if mode == MODE_CAPPED
            else parse_policy_input(mode, "", token)
        )
        assert isinstance(policy, InvestmentCashPolicy)
        actual = policy.cap_eur if mode == MODE_CAPPED else policy.retain_eur
        assert actual == expected

    cash_source = (GATEWAY_SRC / "portfolio_architect_gateway" / "cash_policy.py").read_text()
    assert "from .human_input import HumanInputError, parse_human_eur" in cash_source
    assert "_canonicalize_form_amount" not in cash_source
    assert "_ungroup_integer" not in cash_source


def test_invalid_comdirect_input_preserves_existing_private_policy_state(tmp_path: Path) -> None:
    from portfolio_architect_gateway.cash_policy import (  # noqa: PLC0415
        load_investment_cash_policy,
        save_investment_cash_policy,
    )

    path = tmp_path / "investment-cash-policy.json"
    previous = InvestmentCashPolicy(mode=MODE_RETAIN, retain_eur=Decimal("1024"))
    save_investment_cash_policy(path, previous)
    before = path.read_bytes()

    with pytest.raises(ValueError):
        # Production parses before calling the private-state save path.
        parse_policy_input(MODE_RETAIN, "", "12,34,56")

    assert path.read_bytes() == before
    assert load_investment_cash_policy(path) == previous


def test_helper_is_mirrored_but_exact_protocol_fields_do_not_opt_in() -> None:
    master = GATEWAY_SRC / "portfolio_architect_gateway" / "human_input.py"
    app_roots = (
        ROOT / "home_assistant_app" / "portfolio_architect_gateway" / "src" / "portfolio_architect_gateway",
        ROOT / "home_assistant_app" / "portfolio_architect_gateway_dkb" / "src" / "portfolio_architect_gateway",
        ROOT / "home_assistant_app" / "portfolio_architect_gateway_trade_republic" / "src" / "portfolio_architect_gateway",
    )
    for root in app_roots:
        assert (root / "human_input.py").read_bytes() == master.read_bytes()

    dkb_app = (app_roots[1] / "dkb_app.py").read_text(encoding="utf-8")
    dkb_fints = (app_roots[1] / "dkb_fints.py").read_text(encoding="utf-8")
    assert "human_input" not in dkb_app
    assert "human_input" not in dkb_fints
    assert "normalise_product_id" in dkb_fints
    assert "_PRODUCT_ID_RE.fullmatch" in dkb_fints

    tr_app = (app_roots[2] / "trade_republic_app.py").read_text(encoding="utf-8")
    assert "human_input" not in tr_app


def test_v1370_version_metadata_and_sync_contract_are_aligned() -> None:
    import json  # noqa: PLC0415
    import yaml  # noqa: PLC0415

    assert 'version = "1.41.0"' in (ROOT / "pyproject.toml").read_text()
    manifest = json.loads((ROOT / "custom_components" / "portfolio_architect" / "manifest.json").read_text())
    assert manifest["version"] == "1.41.0"
    assert 'VERSION: Final = "1.41.0"' in (
        ROOT / "custom_components" / "portfolio_architect" / "const.py"
    ).read_text()
    assert '__version__ = "1.41.0"' in (
        ROOT / "custom_components" / "portfolio_architect" / "engine" / "__init__.py"
    ).read_text()
    for app in (
        "portfolio_architect_gateway",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
    ):
        config = yaml.safe_load((ROOT / "home_assistant_app" / app / "config.yaml").read_text())
        assert config["version"] == "1.41.0"

    sync = (ROOT / "tools" / "sync_gateway_app_sources.py").read_text()
    assert '"human_input.py"' in sync
