from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src" / "portfolio_architect_gateway"


def test_bank_client_has_no_trading_endpoint_or_generic_public_request_api() -> None:
    production = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (SRC / "comdirect.py", SRC / "transport.py")
    ).casefold()
    for forbidden in (
        "/orders",
        "/order",
        "place_order",
        "cancel_order",
        "modify_order",
        "orderbook",
    ):
        assert forbidden not in production
    assert "def get_depots" in production
    assert "def get_positions" in production
    assert "def get_instrument" in production


def test_container_reference_is_pinned_and_hardened() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    compose = (ROOT / "compose.yaml").read_text()
    assert "python:3.14.6-alpine3.24@sha256:" in dockerfile
    assert "USER portfolio:portfolio" in dockerfile
    for control in (
        "read_only: true",
        "cap_drop:",
        "ALL",
        "no-new-privileges:true",
        "pids_limit:",
        "mem_limit:",
        "tmpfs:",
    ):
        assert control in compose


def test_production_logs_do_not_contain_secret_or_money_fields() -> None:
    server = (SRC / "server.py").read_text().casefold()
    assert "authorization" not in server.split("def log_message", 1)[1]
    assert "market_value" not in server
