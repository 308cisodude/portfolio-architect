"""Regression coverage for v1.34.1 Comdirect OAuth session maintenance."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
GATEWAY_SRC = ROOT / "gateway" / "src"
if str(GATEWAY_SRC) not in sys.path:
    sys.path.insert(0, str(GATEWAY_SRC))

from portfolio_architect_gateway.comdirect import (  # noqa: E402
    ComdirectClient,
    SESSION_MAINTENANCE_INTERVAL_SECONDS,
    TokenState,
)
from portfolio_architect_gateway.config import ComdirectConfig  # noqa: E402
from portfolio_architect_gateway.errors import (  # noqa: E402
    ReauthenticationRequired,
    RemoteApiError,
)
from portfolio_architect_gateway.transport import HttpResponse  # noqa: E402


def _response(value: dict[str, object]) -> HttpResponse:
    return HttpResponse(
        status=200,
        body=json.dumps(value, separators=(",", ":")).encode(),
        headers={"content-type": "application/json"},
    )


def _config(tmp_path: Path) -> ComdirectConfig:
    tmp_path.mkdir(parents=True, exist_ok=True)
    values = {
        "client_id": "client",
        "client_secret": "secret",
        "username": "user",
        "password": "password",
    }
    paths: dict[str, Path] = {}
    for name, value in values.items():
        path = tmp_path / name
        path.write_text(value, encoding="utf-8")
        path.chmod(0o600)
        paths[name] = path
    return ComdirectConfig(
        base_url="https://api.comdirect.de",
        client_id_file=paths["client_id"],
        client_secret_file=paths["client_secret"],
        username_file=paths["username"],
        password_file=paths["password"],
        session_file=tmp_path / "session.json",
        investment_account_file=tmp_path / "investment-account.json",
        investment_cash_policy_file=tmp_path / "investment-cash-policy.json",
        poll_interval_seconds=900,
        request_timeout_seconds=47,
        mfa_timeout_seconds=180,
        depot_ids=(),
    )


class _ExpiringRefreshTransport:
    """Model 10-minute access tokens and a 20-minute refresh-token window."""

    def __init__(self, clock: list[int]) -> None:
        self.clock = clock
        self.qsession = "qsession"
        self.refresh_issued_at: dict[str, int] = {"refresh-0": 0}
        self.refresh_calls = 0

    def restore_qsession(self, value: str | None) -> None:
        if value:
            self.qsession = value

    def current_qsession(self) -> str:
        return self.qsession

    def oauth_refresh(self, **kwargs: str) -> HttpResponse:
        token = kwargs["refresh_token"]
        issued_at = self.refresh_issued_at[token]
        self.refresh_calls += 1
        if self.clock[0] - issued_at > 1200:
            raise RemoteApiError(
                400,
                "Comdirect API returned HTTP 400",
                operation="oauth_refresh",
                error_code="invalid_grant",
            )
        replacement = f"refresh-{self.refresh_calls}"
        self.refresh_issued_at[replacement] = self.clock[0]
        return _response(
            {
                "access_token": f"access-{self.refresh_calls}",
                "refresh_token": replacement,
                "expires_in": 600,
                "token_type": "Bearer",
                "scope": "BROKERAGE_RW",
            }
        )

    def __getattr__(self, name: str):
        raise AssertionError(f"session maintenance must not call provider operation {name}")


def _client(tmp_path: Path, clock: list[int], transport: _ExpiringRefreshTransport) -> ComdirectClient:
    cfg = _config(tmp_path)
    state = TokenState(
        access_token="access-0",
        refresh_token="refresh-0",
        expires_at=600,
        scope="BROKERAGE_RW",
        qsession="qsession",
    )
    cfg.session_file.write_text(json.dumps(state.as_dict()), encoding="utf-8")
    cfg.session_file.chmod(0o600)
    return ComdirectClient(cfg, transport=transport, clock=lambda: clock[0])


def test_five_minute_session_maintenance_breaks_the_portfolio_phase_race(tmp_path: Path) -> None:
    assert SESSION_MAINTENANCE_INTERVAL_SECONDS == 300

    # Without an independent maintenance tick, a portfolio refresh around minute 8
    # can reuse the access token and leave the original refresh token to expire before
    # the next 15-minute portfolio cycle.
    stale_clock = [480]
    stale_transport = _ExpiringRefreshTransport(stale_clock)
    stale_client = _client(tmp_path / "stale", stale_clock, stale_transport)
    assert stale_client.ensure_access_token() == "access-0"
    stale_clock[0] = 1380
    with pytest.raises(ReauthenticationRequired):
        stale_client.ensure_access_token()

    maintained_clock = [300]
    maintained_transport = _ExpiringRefreshTransport(maintained_clock)
    maintained_client = _client(
        tmp_path / "maintained", maintained_clock, maintained_transport
    )

    # Keep the dark passenger on its own cadence: portfolio polling must not decide
    # whether the provider session survives.
    assert maintained_client.maintain_session() is False
    maintained_clock[0] = 600
    assert maintained_client.maintain_session() is True
    maintained_clock[0] = 900
    assert maintained_client.maintain_session() is False
    maintained_clock[0] = 1200
    assert maintained_client.maintain_session() is True
    maintained_clock[0] = 1380
    assert maintained_client.ensure_access_token() == "access-2"
    assert maintained_transport.refresh_calls == 2


def test_invalid_refresh_is_latched_until_interactive_bootstrap(tmp_path: Path) -> None:
    clock = [1380]
    transport = _ExpiringRefreshTransport(clock)
    client = _client(tmp_path, clock, transport)

    with pytest.raises(ReauthenticationRequired):
        client.ensure_access_token()
    assert transport.refresh_calls == 1

    # Once Comdirect has conclusively rejected the refresh session, scheduled loops
    # fail closed locally instead of hammering the same rejected token every cycle.
    with pytest.raises(ReauthenticationRequired):
        client.ensure_access_token()
    assert transport.refresh_calls == 1


def test_provider_specific_maintenance_thread_is_wired_only_into_comdirect_runtime() -> None:
    app = (ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "app.py").read_text(
        encoding="utf-8"
    )
    cli = (ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "cli.py").read_text(
        encoding="utf-8"
    )
    provider = (
        ROOT / "gateway" / "src" / "portfolio_architect_gateway" / "provider.py"
    ).read_text(encoding="utf-8")
    assert "client.run_session_maintenance_loop" in app
    assert "target=client.run_session_maintenance_loop" in cli
    assert "session" not in provider.lower()
    assert "oauth" not in provider.lower()


def test_ai_policy_discloses_independent_security_focused_second_opinion() -> None:
    policy = " ".join((ROOT / "AI_POLICY.md").read_text(encoding="utf-8").split())
    assert "Independent AI second-opinion review" in policy
    assert "separate AI system" in policy
    assert "security-focused" in policy
    assert "not an independent security certification" in policy
    assert "no merge, tagging, publication, or deployment authority" in policy
