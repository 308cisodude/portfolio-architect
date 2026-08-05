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
from portfolio_architect_gateway.comdirect import AccountBalanceCandidate
from portfolio_architect_gateway.models import PortfolioSnapshot, Position
from portfolio_architect_gateway.server import GatewayState
from portfolio_architect_gateway.store import save_snapshot


class FakeBootstrapClient:
    def __init__(self) -> None:
        self.credentials = None
        self.selected_account_id = None
        self.candidate = AccountBalanceCandidate(
            account_id="account-internal-1",
            display_id="DE00123456789012345678",
            account_type="Girokonto",
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

    def discover_depots(self):
        from portfolio_architect_gateway.comdirect import DepotCandidate
        return (DepotCandidate("DEPOT-PRIVATE-1", "12345678"),)

    def probe_instrument(self, isin):
        from portfolio_architect_gateway.comdirect import InstrumentProbeResult
        return InstrumentProbeResult(
            isin=isin.upper(), name="ETF One", wkn="A1XB5U", fund_status="A",
            fund_flags=("FLAG_A",), currency="EUR",
            surcharges={"regularIssueSurcharge": "1.5"},
            venues=({"venue_id": "VENUE-PRIVATE-1", "name": "Tradegate", "country": "DE", "type": "EXCHANGE"},),
            probed_at=datetime.now(timezone.utc).replace(microsecond=0),
        )

    def probe_cost_indication(self, **kwargs):
        from portfolio_architect_gateway.comdirect import CostProbeResult
        assert kwargs["depot_id"] == "DEPOT-PRIVATE-1"
        assert kwargs["venue_id"] == "VENUE-PRIVATE-1"
        return CostProbeResult({
            "probe_type": "ordinary_order_cost_indication",
            "warning": "No order was validated or submitted. This is not a savings-plan quotation.",
            "requested_isin": kwargs["isin"],
            "requested_quantity": str(kwargs["quantity"]),
            "requested_venue": kwargs["venue_name"],
            "calculation_successful": True,
        })

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
    state = GatewayState(config, client)
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
        assert b"Experimental Comdirect brokerage diagnostics" in body
        assert b"Read instrument metadata and venues" in body
        assert b"not a promotion detector" in body
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


def test_ingress_experimental_probe_uses_opaque_tokens_and_exports_sanitized_json(tmp_path: Path) -> None:
    controller, _client = _controller(tmp_path)
    server = IngressHttpServer(("127.0.0.1", 0), controller, allowed_sources=frozenset({"127.0.0.1"}), require_user_header=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        form = urlencode({"csrf": controller.csrf_token, "isin": "IE00BJ0KDQ92"})
        connection.request("POST", "/probe-instrument", body=form, headers={"Content-Type": "application/x-www-form-urlencoded", "Content-Length": str(len(form.encode())), "X-Remote-User-Id": "admin"})
        response = connection.getresponse(); assert response.status == 303; response.read()
        view = controller.status_document()["experimental_probe"]
        assert view["state"] == "instrument_ready"
        assert "VENUE-PRIVATE-1" not in json.dumps(view)
        assert "DEPOT-PRIVATE-1" not in json.dumps(view)
        cost = urlencode({"csrf": controller.csrf_token, "depot": view["depots"][0]["token"], "venue": view["venues"][0]["token"], "quantity": "1"})
        connection.request("POST", "/probe-cost", body=cost, headers={"Content-Type": "application/x-www-form-urlencoded", "Content-Length": str(len(cost.encode())), "X-Remote-User-Id": "admin"})
        response = connection.getresponse(); assert response.status == 303; response.read()
        connection.request("GET", "/probe-result.json", headers={"X-Remote-User-Id": "admin"})
        response = connection.getresponse(); report = json.loads(response.read()); assert response.status == 200
        encoded = json.dumps(report)
        assert report["no_order_submitted"] is True
        assert report["cost_probe"]["calculation_successful"] is True
        assert "VENUE-PRIVATE-1" not in encoded
        assert "DEPOT-PRIVATE-1" not in encoded
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
