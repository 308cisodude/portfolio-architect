from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import http.client
import threading

from portfolio_architect_gateway.config import ComdirectConfig, GatewayConfig, ServerConfig
from portfolio_architect_gateway.errors import GatewayError
from portfolio_architect_gateway.models import PortfolioSnapshot, Position
from portfolio_architect_gateway.server import GatewayHttpServer, GatewayState
from portfolio_architect_gateway.store import save_snapshot


class NoNetworkClient:
    def fetch_snapshot(self):
        raise AssertionError("network refresh is not part of the HTTP contract test")


class FailingClient:
    def fetch_snapshot(self):
        raise GatewayError("simulated")


def _config(tmp_path: Path) -> GatewayConfig:
    token = tmp_path / "token"
    token.write_text("g" * 64)
    token.chmod(0o600)
    snapshot_file = tmp_path / "portfolio.json"
    save_snapshot(
        snapshot_file,
        PortfolioSnapshot(
            generated_at=datetime.now(timezone.utc).replace(microsecond=0),
            positions=(
                Position("A1XB5U", "ETF One", Decimal("123.45"), instrument_type="ETF"),
            ),
        ),
    )
    secret = tmp_path / "placeholder"
    secret.write_text("x")
    secret.chmod(0o600)
    return GatewayConfig(
        server=ServerConfig(
            bind="127.0.0.1",
            port=0,
            api_token_file=token,
            snapshot_file=snapshot_file,
            max_cached_snapshot_age_seconds=3600,
            tls_cert_file=None,
            tls_key_file=None,
            health_endpoint_enabled=True,
        ),
        comdirect=ComdirectConfig(
            base_url="https://api.comdirect.de",
            client_id_file=secret,
            client_secret_file=secret,
            username_file=secret,
            password_file=secret,
            session_file=tmp_path / "session.json",
        investment_account_file=tmp_path / "investment-account.json",
            poll_interval_seconds=900,
            request_timeout_seconds=20,
            mfa_timeout_seconds=180,
            depot_ids=(),
        ),
    )


def _start(tmp_path: Path):
    config = _config(tmp_path)
    state = GatewayState(config, NoNetworkClient())
    server = GatewayHttpServer(
        ("127.0.0.1", 0), state, "g" * 64, health_endpoint_enabled=True
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_gateway_requires_bearer_and_supports_etag(tmp_path: Path) -> None:
    server, thread = _start(tmp_path)
    try:
        port = server.server_address[1]
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", "/api/v1/portfolio")
        response = connection.getresponse()
        assert response.status == 401
        response.read()

        connection.request(
            "GET",
            "/api/v1/portfolio",
            headers={"Authorization": f"Bearer {'g' * 64}"},
        )
        response = connection.getresponse()
        body = response.read()
        assert response.status == 200
        assert b'"schema_version":1' in body
        etag = response.getheader("ETag")
        assert etag

        connection.request(
            "GET",
            "/api/v1/portfolio",
            headers={
                "Authorization": f"Bearer {'g' * 64}",
                "If-None-Match": etag,
            },
        )
        response = connection.getresponse()
        assert response.status == 304
        assert response.read() == b""
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_gateway_rejects_every_write_method(tmp_path: Path) -> None:
    server, thread = _start(tmp_path)
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )
        connection.request(
            "POST",
            "/api/v1/portfolio",
            headers={"Authorization": f"Bearer {'g' * 64}"},
        )
        response = connection.getresponse()
        assert response.status == 405
        assert response.getheader("Allow") == "GET"
        response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_gateway_publishes_snapshot_integrity_metadata(tmp_path: Path) -> None:
    import hashlib
    import json

    server, thread = _start(tmp_path)
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )
        auth = {"Authorization": f"Bearer {'g' * 64}"}
        connection.request("GET", "/api/v1/portfolio", headers=auth)
        response = connection.getresponse()
        body = response.read()
        digest = response.getheader("X-Portfolio-Snapshot-SHA256")
        count = response.getheader("X-Portfolio-Position-Count")
        etag = response.getheader("ETag")
        assert response.status == 200
        assert digest == hashlib.sha256(body).hexdigest()
        assert count == "1"
        assert etag == f'"sha256-{digest}"'

        connection.request(
            "GET",
            "/api/v1/portfolio",
            headers={**auth, "If-None-Match": etag},
        )
        response = connection.getresponse()
        assert response.status == 304
        assert response.getheader("X-Portfolio-Snapshot-SHA256") == digest
        assert response.getheader("X-Portfolio-Position-Count") == "1"
        assert response.read() == b""

        connection.request("GET", "/healthz", headers=auth)
        response = connection.getresponse()
        legacy = json.loads(response.read())
        assert response.status == 200
        assert "health_schema_version" not in legacy
        assert "snapshot_sha256" not in legacy

        connection.request(
            "GET",
            "/healthz",
            headers={
                **auth,
                "Accept": (
                    "application/vnd.portfolio-architect.health+json;version=2"
                ),
            },
        )
        response = connection.getresponse()
        health = json.loads(response.read())
        assert response.status == 200
        assert response.getheader("Content-Type").startswith(
            "application/vnd.portfolio-architect.health+json;version=2"
        )
        assert health["health_schema_version"] == 2
        assert health["snapshot_sha256"] == digest
        assert health["snapshot_position_count"] == 1
        assert health["poll_interval_seconds"] == 900
        assert health["max_cached_snapshot_age_seconds"] == 3600

        connection.request(
            "GET",
            "/healthz",
            headers={
                **auth,
                "Accept": (
                    "application/vnd.portfolio-architect.health+json;version=3"
                ),
            },
        )
        response = connection.getresponse()
        health_v3 = json.loads(response.read())
        assert response.status == 200
        assert response.getheader("Content-Type").startswith(
            "application/vnd.portfolio-architect.health+json;version=3"
        )
        assert health_v3["health_schema_version"] == 3
        assert health_v3["operating_mode"] == "last_known_good"
        assert health_v3["status"] == "degraded"
        assert health_v3["consecutive_refresh_failures"] == 0
        assert health_v3["snapshot_age_seconds"] >= 0
        assert 0 <= health_v3["snapshot_expires_in_seconds"] <= 3600
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_gateway_tracks_last_known_good_after_refresh_failure(tmp_path: Path) -> None:
    config = _config(tmp_path)
    state = GatewayState(config, FailingClient())
    before = state.health_document(version=3)
    assert before["operating_mode"] == "last_known_good"
    assert before["consecutive_refresh_failures"] == 0
    assert state.refresh() is False
    after = state.health_document(version=3)
    assert after["status"] == "degraded"
    assert after["operating_mode"] == "last_known_good"
    assert after["snapshot_available"] is True
    assert after["consecutive_refresh_failures"] == 1
    assert after["last_refresh_attempt"] is not None
    assert after["last_error"] == "GatewayError"


class BlockingClient:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def fetch_snapshot(self):
        self.started.set()
        assert self.release.wait(5)
        return PortfolioSnapshot(
            generated_at=datetime.now(timezone.utc).replace(microsecond=0),
            positions=(
                Position("A1XB5U", "ETF One", Decimal("124.00"), instrument_type="ETF"),
            ),
        )


def test_gateway_health_v4_reports_refresh_telemetry(tmp_path: Path) -> None:
    import json

    server, thread = _start(tmp_path)
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1], timeout=5
        )
        connection.request(
            "GET",
            "/healthz",
            headers={
                "Authorization": f"Bearer {'g' * 64}",
                "Accept": "application/vnd.portfolio-architect.health+json;version=4",
            },
        )
        response = connection.getresponse()
        health = json.loads(response.read())
        assert response.status == 200
        assert response.getheader("Content-Type").startswith(
            "application/vnd.portfolio-architect.health+json;version=4"
        )
        assert health["health_schema_version"] == 4
        assert health["refresh_in_progress"] is False
        assert health["last_refresh_duration_ms"] is None
        assert health["last_refresh_trigger"] is None
        assert health["next_refresh_due_at"] is None
        assert health["manual_refresh_min_interval_seconds"] == 60
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_manual_refresh_is_non_overlapping_and_rate_limited(tmp_path: Path) -> None:
    config = _config(tmp_path)
    client = BlockingClient()
    state = GatewayState(config, client)

    accepted, retry_after = state.request_manual_refresh()
    assert accepted is True
    assert retry_after is None
    assert client.started.wait(5)

    during = state.health_document(version=4)
    assert during["refresh_in_progress"] is True
    assert during["last_refresh_trigger"] == "manual"
    assert during["last_refresh_attempt"] is not None

    accepted, retry_after = state.request_manual_refresh()
    assert accepted is False
    assert retry_after == 1

    client.release.set()
    deadline = __import__("time").time() + 5
    while state.health_document(version=4)["refresh_in_progress"] and __import__("time").time() < deadline:
        __import__("time").sleep(0.01)

    completed = state.health_document(version=4)
    assert completed["refresh_in_progress"] is False
    assert completed["last_refresh_duration_ms"] is not None
    assert completed["last_refresh_duration_ms"] >= 0
    assert completed["last_refresh_trigger"] == "manual"
    assert completed["operating_mode"] == "live"

    accepted, retry_after = state.request_manual_refresh()
    assert accepted is False
    assert retry_after is not None
    assert 1 <= retry_after <= 60


def test_next_scheduled_refresh_timestamp_is_published(tmp_path: Path) -> None:
    config = _config(tmp_path)
    state = GatewayState(config, NoNetworkClient())
    due = datetime.now(timezone.utc).replace(microsecond=0)
    state.set_next_refresh_due_at(due)
    health = state.health_document(version=4)
    assert health["next_refresh_due_at"] == due.isoformat(timespec="seconds")


def test_refresh_loop_keeps_fixed_cadence_after_request_duration(monkeypatch) -> None:
    import portfolio_architect_gateway.server as server_module

    class RecordingState:
        def __init__(self) -> None:
            self.triggers: list[str] = []
            self.due_values = []

        def refresh(self, *, trigger: str = "scheduled") -> bool:
            self.triggers.append(trigger)
            return True

        def set_next_refresh_due_at(self, value) -> None:
            self.due_values.append(value)

    class StopAfterSecondWait:
        def __init__(self) -> None:
            self.waits: list[float] = []

        def is_set(self) -> bool:
            return False

        def wait(self, delay: float) -> bool:
            self.waits.append(delay)
            return len(self.waits) == 2

    monotonic_values = iter((100.0, 100.0, 103.0, 103.0))
    monkeypatch.setattr(server_module.time, "monotonic", lambda: next(monotonic_values))
    state = RecordingState()
    stop = StopAfterSecondWait()

    server_module.run_refresh_loop(state, 10, stop)

    assert state.triggers == ["startup", "scheduled"]
    assert stop.waits == [10.0, 17.0]
    assert state.due_values[0] is None
    assert state.due_values[-1] is None


def test_gateway_health_v5_reports_classified_recovery_guidance(tmp_path: Path) -> None:
    from portfolio_architect_gateway.errors import RemoteApiError

    class RateLimitedClient:
        def fetch_snapshot(self):
            raise RemoteApiError(
                429,
                "simulated",
                retry_after=120,
                operation="get_positions",
            )

    config = _config(tmp_path)
    state = GatewayState(config, RateLimitedClient())
    assert state.refresh(trigger="scheduled") is False
    health = state.health_document(version=5)
    assert health["health_schema_version"] == 5
    assert health["status"] == "degraded"
    assert health["operating_mode"] == "last_known_good"
    assert health["last_refresh_failure_at"] is not None
    assert health["last_refresh_failure_class"] == "rate_limited"
    assert health["recommended_action"] == "wait"
    assert health["retry_after_seconds"] == 120


def test_gateway_health_v5_clears_failure_guidance_after_success(tmp_path: Path) -> None:
    class ToggleClient:
        def __init__(self) -> None:
            self.fail = True

        def fetch_snapshot(self):
            if self.fail:
                raise GatewayError("simulated")
            return PortfolioSnapshot(
                generated_at=datetime.now(timezone.utc).replace(microsecond=0),
                positions=(
                    Position(
                        "A1XB5U",
                        "ETF One",
                        Decimal("125.00"),
                        instrument_type="ETF",
                    ),
                ),
            )

    config = _config(tmp_path)
    client = ToggleClient()
    state = GatewayState(config, client)
    assert state.refresh(trigger="scheduled") is False
    failed = state.health_document(version=5)
    assert failed["last_refresh_failure_class"] == "gateway_error"
    assert failed["recommended_action"] == "inspect_logs"

    client.fail = False
    assert state.refresh(trigger="manual") is True
    recovered = state.health_document(version=5)
    assert recovered["status"] == "ok"
    assert recovered["last_refresh_failure_at"] is None
    assert recovered["last_refresh_failure_class"] is None
    assert recovered["recommended_action"] == "none"
    assert recovered["retry_after_seconds"] is None
