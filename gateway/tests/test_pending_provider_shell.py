from pathlib import Path

import pytest

from portfolio_architect_gateway.errors import ConfigurationError
from portfolio_architect_gateway.pending_app import PendingProvider
from portfolio_architect_gateway.runtime_config import ServerConfig
from portfolio_architect_gateway.server import GatewayState


def _server_config(tmp_path: Path) -> ServerConfig:
    return ServerConfig(
        bind="127.0.0.1",
        port=0,
        api_token_file=tmp_path / "gateway-api-token",
        snapshot_file=tmp_path / "portfolio.json",
        max_cached_snapshot_age_seconds=604800,
        tls_cert_file=None,
        tls_key_file=None,
        health_endpoint_enabled=True,
    )


def test_pending_provider_has_bounded_identity_and_never_returns_portfolio() -> None:
    provider = PendingProvider("trade_republic")
    assert provider.provider_id == "trade_republic"
    assert provider.poll_interval_seconds == 86400
    with pytest.raises(ConfigurationError, match="not implemented"):
        provider.fetch_snapshot()


def test_pending_provider_state_is_explicitly_degraded_without_snapshot(tmp_path: Path) -> None:
    state = GatewayState(_server_config(tmp_path), PendingProvider("dkb"))
    assert state.refresh(trigger="startup") is False
    health = state.health_document(version=6)
    assert health["health_schema_version"] == 6
    assert health["provider_id"] == "dkb"
    assert health["status"] == "degraded"
    assert health["snapshot_available"] is False
    assert health["operating_mode"] == "unavailable"
    assert health["last_refresh_failure_class"] == "configuration_error"
    assert health["recommended_action"] == "fix_configuration"
