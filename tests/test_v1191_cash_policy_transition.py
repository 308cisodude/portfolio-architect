"""v1.19.1 server-authoritative cash-policy transition contracts."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
GATEWAY = ROOT / "gateway" / "src" / "portfolio_architect_gateway"
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway" / "src" / "portfolio_architect_gateway"


def test_gateway_and_app_keep_identical_policy_transition_source() -> None:
    for name in ("cash_policy.py", "app.py"):
        assert (GATEWAY / name).read_bytes() == (APP / name).read_bytes()


def test_all_available_transition_is_server_authoritative() -> None:
    cash_policy = (GATEWAY / "cash_policy.py").read_text(encoding="utf-8")
    app = (GATEWAY / "app.py").read_text(encoding="utf-8")
    assert "if cleaned_mode == MODE_ALL_AVAILABLE:" in cash_policy
    assert "if cap_eur.strip():" not in cash_policy.split("def parse_policy_input", 1)[1].split("def _validate_amount", 1)[0]
    assert '{"csrf", "mode"}' in app
    assert 'cap_eur=_single(values, "cap_eur") if "cap_eur" in values else ""' in app
    assert "cap.disabled=!capped" in app
    assert "if(!capped)cap.value=''" in app
