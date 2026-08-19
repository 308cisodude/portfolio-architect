from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import http.client
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlencode

from portfolio_architect_gateway.app import (
    AppController,
    AppOptions,
    IngressHttpServer,
    build_app_config,
    ensure_api_token,
)
from portfolio_architect_gateway.cash_policy import InvestmentCashPolicy
from portfolio_architect_gateway.comdirect import AccountBalanceCandidate
from portfolio_architect_gateway.models import PortfolioSnapshot, Position
from portfolio_architect_gateway.server import GatewayState
from portfolio_architect_gateway.store import save_snapshot


class FakeBootstrapClient:
    provider_id = "comdirect"
    poll_interval_seconds = 900
    def __init__(self) -> None:
        self.credentials = None
        self.selected_account_id = None
        self.candidate = AccountBalanceCandidate(
            account_id="account-internal-1",
            display_id="DE00123456789012345678",
            account_type="Girokonto",
            account_balance_eur=Decimal("1050.00"),
            available_eur=Decimal("1050.00"),
            as_of=datetime.now(timezone.utc).replace(microsecond=0),
        )

    def bootstrap_with_credentials(self, **kwargs):
        self.credentials = {
            key: kwargs[key]
            for key in ("client_id", "client_secret", "username", "password")
        }

    def discover_investment_accounts(self):
        return (self.candidate,)

    def selected_investment_account_id(self):
        return self.selected_account_id

    def select_investment_account(self, account_id):
        if account_id != self.candidate.account_id:
            raise ValueError("unknown account")
        self.selected_account_id = account_id
        return self.candidate

    def clear_investment_account(self):
        self.selected_account_id = None

    def investment_cash_policy(self):
        return getattr(self, "cash_policy", InvestmentCashPolicy())

    def set_investment_cash_policy(self, policy):
        self.cash_policy = policy

    def fetch_snapshot(self):
        selected = self.selected_account_id is not None
        return PortfolioSnapshot(
            generated_at=datetime.now(timezone.utc).replace(microsecond=0),
            positions=(
                Position("A1XB5U", "ETF One", Decimal("123.45"), instrument_type="ETF"),
            ),
            investment_reserve_eur=self.candidate.available_eur if selected else None,
            investment_reserve_as_of=self.candidate.as_of if selected else None,
        )


def test_app_options_and_private_runtime_config(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    options_path.write_text(
        json.dumps(
            {
                "poll_interval_seconds": 1200,
                "max_cached_snapshot_age_seconds": 3600,
                "request_timeout_seconds": 15,
                "mfa_timeout_seconds": 240,
                "health_endpoint_enabled": True,
                "depot_ids": ["D1"],
            }
        )
    )
    options = AppOptions.load(options_path)
    config = build_app_config(options, tmp_path / "gateway")
    assert config.server.bind == "0.0.0.0"
    assert config.server.port == 8787
    assert config.comdirect.depot_ids == ("D1",)
    assert config.comdirect.username_file.name == ".username-not-persisted"
    assert config.comdirect.password_file.name == ".password-not-persisted"
    assert config.comdirect.investment_cash_policy_file.name == "investment-cash-policy.json"


def test_app_api_token_is_stable_and_private(tmp_path: Path) -> None:
    token_path = tmp_path / "gateway-api-token"
    first = ensure_api_token(token_path)
    second = ensure_api_token(token_path)
    assert first == second
    assert len(first) >= 32
    assert token_path.stat().st_mode & 0o777 == 0o600


def _controller(tmp_path: Path):
    options = AppOptions()
    data = tmp_path / "gateway"
    data.mkdir()
    config = build_app_config(options, data)
    token = ensure_api_token(config.server.api_token_file)
    snapshot = PortfolioSnapshot(
        generated_at=datetime.now(timezone.utc).replace(microsecond=0),
        positions=(Position("A1XB5U", "ETF One", Decimal("10.00")),),
    )
    save_snapshot(config.server.snapshot_file, snapshot)
    client = FakeBootstrapClient()
    state = GatewayState(config.server, client)
    return AppController(config, client, state, token), client


def test_ingress_requires_proxy_identity_and_serves_setup(tmp_path: Path) -> None:
    controller, _client = _controller(tmp_path)
    server = IngressHttpServer(
        ("127.0.0.1", 0),
        controller,
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )
        connection.request("GET", "/")
        response = connection.getresponse()
        assert response.status == 403
        response.read()

        connection.request("GET", "/", headers={"X-Remote-User-Id": "admin"})
        response = connection.getresponse()
        body = response.read()
        assert response.status == 200
        assert b"local-portfolio-architect-gateway:8787" in body
        assert controller.api_token.encode() in body
        assert response.getheader("Cache-Control") == "no-store"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_ingress_bootstrap_keeps_username_and_password_out_of_files(tmp_path: Path) -> None:
    controller, client = _controller(tmp_path)
    server = IngressHttpServer(
        ("127.0.0.1", 0),
        controller,
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        form = urlencode(
            {
                "csrf": controller.csrf_token,
                "client_id": "client-id",
                "client_secret": "client-secret",
                "username": "bank-user",
                "password": "bank-password",
            }
        )
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )
        connection.request(
            "POST",
            "/bootstrap",
            body=form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(form.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        response.read()
        deadline = time.time() + 5
        while controller.bootstrap_view().state == "running" and time.time() < deadline:
            time.sleep(0.02)
        assert controller.bootstrap_view().state == "success"
        assert client.credentials["username"] == "bank-user"
        assert client.credentials["password"] == "bank-password"
        assert controller.config.comdirect.client_id_file.read_text() == "client-id"
        assert controller.config.comdirect.client_secret_file.read_text() == "client-secret"
        all_text = "\n".join(
            path.read_text(errors="ignore")
            for path in tmp_path.rglob("*")
            if path.is_file()
        )
        assert "bank-user" not in all_text
        assert "bank-password" not in all_text
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_ingress_manual_refresh_is_csrf_protected_and_rate_limited(tmp_path: Path) -> None:
    controller, _client = _controller(tmp_path)
    server = IngressHttpServer(
        ("127.0.0.1", 0),
        controller,
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )
        invalid_form = urlencode({"csrf": "invalid"})
        connection.request(
            "POST",
            "/refresh",
            body=invalid_form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(invalid_form.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 403
        response.read()

        form = urlencode({"csrf": controller.csrf_token})
        connection.request(
            "POST",
            "/refresh",
            body=form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(form.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        assert response.getheader("Location") == "./"
        response.read()

        deadline = time.time() + 5
        while (
            controller.status_document()["gateway"]["refresh_in_progress"]
            and time.time() < deadline
        ):
            time.sleep(0.01)
        status = controller.status_document()["gateway"]
        assert status["last_refresh_trigger"] == "manual"
        assert status["last_refresh_duration_ms"] is not None

        connection.request(
            "POST",
            "/refresh",
            body=form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(form.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 429
        assert 1 <= int(response.getheader("Retry-After")) <= 60
        response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)



def test_ingress_discovers_and_selects_masked_investment_account(tmp_path: Path) -> None:
    controller, client = _controller(tmp_path)
    server = IngressHttpServer(
        ("127.0.0.1", 0),
        controller,
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )
        discover = urlencode({"csrf": controller.csrf_token})
        connection.request(
            "POST",
            "/discover-accounts",
            body=discover,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(discover.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        response.read()
        account = controller.status_document()["investment_account"]
        assert account["state"] == "ready"
        assert len(account["candidates"]) == 1
        candidate = account["candidates"][0]
        assert candidate["label"].endswith("…5678")
        assert candidate["account_balance_eur"] == "1050.00"
        assert candidate["available_eur"] == "1050.00"
        assert "account-internal-1" not in json.dumps(account)

        select = urlencode(
            {"csrf": controller.csrf_token, "selection": candidate["token"]}
        )
        connection.request(
            "POST",
            "/select-account",
            body=select,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(select.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        response.read()
        assert client.selected_account_id == "account-internal-1"
        account = controller.status_document()["investment_account"]
        assert account["selected"] is True
        assert account["selected_label"].endswith("…5678")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

def test_ingress_page_polls_every_mutable_runtime_status_without_reload(tmp_path: Path) -> None:
    controller, _client = _controller(tmp_path)
    server = IngressHttpServer(
        ("127.0.0.1", 0),
        controller,
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )
        connection.request("GET", "/", headers={"X-Remote-User-Id": "admin"})
        response = connection.getresponse()
        body = response.read().decode()
        assert response.status == 200
        for element_id in (
            "gateway-status",
            "operating-mode",
            "snapshot-age",
            "refresh-failures",
            "snapshot-integrity",
            "snapshot-count",
            "snapshot-fingerprint",
        ):
            assert f'id="{element_id}"' in body
            assert f"'{element_id}'" in body
        assert "classList.toggle('ok'" in body
        assert "classList.toggle('warn'" in body
        assert "update();setInterval(update,2000)" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_ingress_updates_investment_cash_authorization_policy(tmp_path: Path) -> None:
    controller, client = _controller(tmp_path)
    server = IngressHttpServer(
        ("127.0.0.1", 0),
        controller,
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )

        capped_form = urlencode(
            {
                "csrf": controller.csrf_token,
                "mode": "capped",
                "cap_eur": "100",
            }
        )
        connection.request(
            "POST",
            "/set-cash-policy",
            body=capped_form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(capped_form.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        response.read()
        assert client.investment_cash_policy().mode == "capped"
        assert client.investment_cash_policy().cap_eur == Decimal("100")

        retained_form = urlencode(
            {
                "csrf": controller.csrf_token,
                "mode": "retain",
                "retain_eur": "750",
            }
        )
        connection.request(
            "POST",
            "/set-cash-policy",
            body=retained_form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(retained_form.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        response.read()
        assert client.investment_cash_policy().mode == "retain"
        assert client.investment_cash_policy().retain_eur == Decimal("750")
        assert controller.status_document()["investment_cash_policy"] == {
            "mode": "retain",
            "cap_eur": None,
            "retain_eur": "750",
        }

        # Reproduce the v1.19.0 transition bug: browsers can retain the old cap
        # field while the operator switches the policy back to all_available.
        stale_cap_form = urlencode(
            {
                "csrf": controller.csrf_token,
                "mode": "all_available",
                "cap_eur": "100",
            }
        )
        connection.request(
            "POST",
            "/set-cash-policy",
            body=stale_cap_form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(stale_cap_form.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        response.read()
        assert client.investment_cash_policy().mode == "all_available"
        assert client.investment_cash_policy().cap_eur is None
        assert controller.status_document()["investment_cash_policy"] == {
            "mode": "all_available",
            "cap_eur": None,
        }

        # A disabled HTML control is omitted from a form submission. The server
        # therefore accepts the canonical all_available request without cap_eur.
        omitted_cap_form = urlencode(
            {
                "csrf": controller.csrf_token,
                "mode": "all_available",
            }
        )
        connection.request(
            "POST",
            "/set-cash-policy",
            body=omitted_cap_form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(omitted_cap_form.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        response.read()
        assert client.investment_cash_policy().mode == "all_available"
        assert client.investment_cash_policy().cap_eur is None

        connection.request("GET", "/", headers={"X-Remote-User-Id": "admin"})
        response = connection.getresponse()
        page = response.read().decode()
        assert response.status == 200
        assert "function syncCashPolicy()" in page
        assert "cap.disabled=!capped" in page
        assert "cap.required=capped" in page
        assert "retain.disabled=!retained" in page
        assert "retain.required=retained" in page
        assert "if(!capped)cap.value=''" in page
        assert "if(!retained)retain.value=''" in page
        assert "Keep cash reserve" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

def test_ingress_cash_policy_accepts_german_amount_and_redirects_invalid_input(tmp_path: Path) -> None:
    controller, client = _controller(tmp_path)
    server = IngressHttpServer(
        ("127.0.0.1", 0),
        controller,
        allowed_sources=frozenset({"127.0.0.1"}),
        require_user_header=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )
        localized = urlencode(
            {
                "csrf": controller.csrf_token,
                "mode": "retain",
                "retain_eur": "1.024,00",
            }
        )
        connection.request(
            "POST",
            "/set-cash-policy",
            body=localized,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(localized.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        assert response.getheader("Location") == "./"
        response.read()
        assert client.investment_cash_policy().mode == "retain"
        assert client.investment_cash_policy().retain_eur == Decimal("1024.00")

        invalid = urlencode(
            {
                "csrf": controller.csrf_token,
                "mode": "retain",
                "retain_eur": "12,34,56",
            }
        )
        connection.request(
            "POST",
            "/set-cash-policy",
            body=invalid,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(invalid.encode())),
                "X-Remote-User-Id": "admin",
            },
        )
        response = connection.getresponse()
        assert response.status == 303
        assert response.getheader("Location") == "./?cash_policy_error=invalid_amount"
        response.read()
        # Rejected input cannot overwrite the last valid private policy.
        assert client.investment_cash_policy().retain_eur == Decimal("1024.00")

        connection.request(
            "GET",
            "/?cash_policy_error=invalid_amount",
            headers={"X-Remote-User-Id": "admin"},
        )
        response = connection.getresponse()
        page = response.read().decode()
        assert response.status == 200
        assert "Could not save the authorization policy" in page
        assert "1024,00 or 1024.00" in page
        assert "12,34,56" not in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
