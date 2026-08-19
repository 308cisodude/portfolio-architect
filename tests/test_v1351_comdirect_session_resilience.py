"""Regression coverage for the v1.35.1 Comdirect maintenance-thread resilience hotfix."""

from __future__ import annotations

import logging
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
GATEWAY_SRC = ROOT / "gateway" / "src"
if str(GATEWAY_SRC) not in sys.path:
    sys.path.insert(0, str(GATEWAY_SRC))

from portfolio_architect_gateway.comdirect import ComdirectClient  # noqa: E402
from portfolio_architect_gateway.errors import RemoteApiError  # noqa: E402
from portfolio_architect_gateway.transport import ComdirectTransport  # noqa: E402


class _ResettingOpener:
    def open(self, *_args, **_kwargs):
        raise ConnectionResetError(104, "Connection reset by peer")


class _TwoIterationStopEvent:
    def __init__(self) -> None:
        self.calls = 0

    def wait(self, timeout: int) -> bool:
        assert timeout == 60
        self.calls += 1
        return self.calls > 2


def test_connection_reset_is_classified_as_retryable_remote_api_failure() -> None:
    transport = ComdirectTransport("https://api.comdirect.de", timeout_seconds=47)
    transport._opener = _ResettingOpener()  # type: ignore[assignment]

    with pytest.raises(RemoteApiError) as captured:
        transport.oauth_refresh(
            client_id="client",
            client_secret="secret",
            refresh_token="refresh-token",
        )

    err = captured.value
    assert err.status == 0
    assert err.operation == "oauth_refresh"
    assert err.error_code is None
    assert str(err) == "Comdirect API transport failed"
    assert isinstance(err.__cause__, ConnectionResetError)


def test_maintenance_loop_contains_unexpected_iteration_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = object.__new__(ComdirectClient)
    calls = 0

    def maintain_session() -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            # Defense in depth: even if a future transport regression lets a raw
            # socket exception escape classification, the long-lived worker survives.
            raise ConnectionResetError(104, "synthetic private-looking detail")
        return True

    client.maintain_session = maintain_session  # type: ignore[method-assign]
    stop_event = _TwoIterationStopEvent()

    with caplog.at_level(logging.INFO, logger="portfolio_architect_gateway.comdirect"):
        client.run_session_maintenance_loop(stop_event, interval_seconds=60)  # type: ignore[arg-type]

    assert calls == 2
    assert stop_event.calls == 3
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        message
        == "Comdirect session maintenance contained unexpected failure: ConnectionResetError"
        for message in messages
    )
    assert "synthetic private-looking detail" not in "\n".join(messages)
    assert any(
        message == "Comdirect OAuth session refreshed by maintenance loop"
        for message in messages
    )


def test_german_allocation_charts_use_accumulating_robotics_label() -> None:
    standalone = (ROOT / "dashboard" / ".tmp_de.yaml").read_text(encoding="utf-8")
    bilingual = (ROOT / "dashboard" / "bilingual-dashboard.yaml").read_text(encoding="utf-8")

    assert "name: Robotics · Acc" not in standalone
    assert standalone.count("name: Robotik · Thes.") == 8

    start = bilingual.index("heading: Aktuelle Planallokation", len(bilingual) // 2)
    end = bilingual.index("heading: Aktuelle Portfolioallokation", start)
    german_allocation = bilingual[start:end]
    assert "name: Robotics · Acc" not in german_allocation
    assert german_allocation.count("name: Robotik · Thes.") == 2
