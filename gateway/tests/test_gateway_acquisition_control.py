from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from portfolio_architect_gateway.acquisition import (
    MODE_CSV,
    MODE_LIVE_API,
    ComdirectAcquisitionProvider,
)
from portfolio_architect_gateway.acquisition_control import (
    METHOD_NOT_READY,
    METHOD_READY,
    AcquisitionControl,
    AcquisitionMethod,
)
from portfolio_architect_gateway.comdirect_cash_csv import ComdirectCashSnapshot
from portfolio_architect_gateway.errors import ConfigurationError
from portfolio_architect_gateway.models import PortfolioSnapshot, Position
from portfolio_architect_gateway.store import load_json_state, save_json_state, save_snapshot


def _snapshot(value: str = "100") -> PortfolioSnapshot:
    return PortfolioSnapshot(
        generated_at=datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc),
        positions=(
            Position(
                identifier="TEST0001",
                name="Synthetic holding",
                market_value_eur=Decimal(value),
            ),
        ),
    )


class FakeLiveClient:
    poll_interval_seconds = 900

    def __init__(self, *, session_ready: bool = True) -> None:
        self.session_state_available = session_ready
        self.calls = 0

    def fetch_snapshot(self) -> PortfolioSnapshot:
        self.calls += 1
        return _snapshot("101")

    def run_session_maintenance_iteration(self) -> None:
        return None


def _provider(tmp_path: Path, *, session_ready: bool = True) -> ComdirectAcquisitionProvider:
    return ComdirectAcquisitionProvider(
        FakeLiveClient(session_ready=session_ready),
        tmp_path,
        tmp_path / "cash-policy.json",
    )


def test_control_model_rejects_automatic_fallback_and_nonready_activation() -> None:
    with pytest.raises(ConfigurationError):
        AcquisitionControl(
            active_method="csv",
            methods=(AcquisitionMethod("csv", METHOD_READY, True, True),),
            fallback_policy="automatic",
        )
    with pytest.raises(ConfigurationError):
        AcquisitionMethod("csv", METHOD_NOT_READY, False, True)


def test_comdirect_inactive_csv_requires_complete_static_candidate(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    control = provider.acquisition_control
    methods = {item.method_id: item for item in control.methods}
    assert control.active_method == MODE_LIVE_API
    assert control.fallback_policy == "none"
    assert methods[MODE_LIVE_API].state == METHOD_READY
    assert methods[MODE_CSV].state == METHOD_NOT_READY
    assert methods[MODE_CSV].can_activate is False

    provider.persist_holdings(_snapshot())
    methods = {item.method_id: item for item in provider.acquisition_control.methods}
    assert methods[MODE_CSV].state == METHOD_NOT_READY

    provider.persist_cash(
        ComdirectCashSnapshot(Decimal("50"), datetime(2026, 8, 25, tzinfo=timezone.utc))
    )
    methods = {item.method_id: item for item in provider.acquisition_control.methods}
    assert methods[MODE_CSV].state == METHOD_READY
    assert methods[MODE_CSV].can_activate is True


def test_comdirect_activation_is_explicit_atomic_and_records_bounded_history(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.persist_holdings(_snapshot())
    provider.persist_cash(
        ComdirectCashSnapshot(Decimal("50"), datetime(2026, 8, 25, tzinfo=timezone.utc))
    )
    published: list[str] = []

    def publish() -> bool:
        published.append(provider.acquisition_mode)
        provider.fetch_snapshot()
        return True

    provider.activate_mode(MODE_CSV, publish)
    assert provider.acquisition_mode == MODE_CSV
    assert published == [MODE_CSV]
    control = provider.acquisition_control
    assert control.active_method == MODE_CSV
    assert control.previous_method == MODE_LIVE_API
    assert control.last_method_change_reason == "operator"
    assert control.last_method_change_at is not None
    persisted = load_json_state(tmp_path / "comdirect-acquisition.json")
    assert persisted is not None
    assert persisted["schema_version"] == 2
    assert persisted["mode"] == MODE_CSV
    assert persisted["previous_mode"] == MODE_LIVE_API


def test_failed_publication_restores_exact_pre_switch_control_state(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.persist_holdings(_snapshot())
    provider.persist_cash(
        ComdirectCashSnapshot(Decimal("50"), datetime(2026, 8, 25, tzinfo=timezone.utc))
    )
    calls = 0

    def publish() -> bool:
        nonlocal calls
        calls += 1
        return calls == 2

    with pytest.raises(ValueError):
        provider.activate_mode(MODE_CSV, publish)
    assert provider.acquisition_mode == MODE_LIVE_API
    # The mode file did not exist before the attempted switch, so exact rollback
    # restores that persisted absence rather than materializing a default document.
    assert load_json_state(tmp_path / "comdirect-acquisition.json") is None
    assert not (tmp_path / "comdirect-acquisition-pending.json").exists()
    assert calls == 2


def test_csv_activation_fails_closed_until_both_static_evidence_families_exist(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.persist_holdings(_snapshot())
    with pytest.raises(ConfigurationError):
        provider.activate_mode(MODE_CSV, lambda: True)
    assert provider.acquisition_mode == MODE_LIVE_API


def test_corrupt_inactive_csv_candidate_cannot_disrupt_active_live_method(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.holdings_file.write_bytes(b"{not-a-valid-snapshot")
    provider.cash_file.write_bytes(b"{not-valid-json")

    control = provider.acquisition_control
    methods = {item.method_id: item for item in control.methods}
    assert control.active_method == MODE_LIVE_API
    assert methods[MODE_LIVE_API].state == METHOD_READY
    assert methods[MODE_CSV].state == METHOD_NOT_READY
    assert methods[MODE_CSV].can_activate is False
    assert provider.fetch_snapshot().positions[0].market_value_eur == Decimal("101")


def test_interrupted_activation_recovery_discards_ambiguous_canonical_snapshot(tmp_path: Path) -> None:
    previous = {"schema_version": 1, "mode": MODE_LIVE_API}
    candidate = {
        "schema_version": 2,
        "mode": MODE_CSV,
        "previous_mode": MODE_LIVE_API,
        "last_method_change_at": "2026-08-25T17:00:00+00:00",
        "last_method_change_reason": "operator",
    }
    save_json_state(tmp_path / "comdirect-acquisition.json", candidate)
    save_json_state(
        tmp_path / "comdirect-acquisition-pending.json",
        {
            "schema_version": 1,
            "previous_state": previous,
            "previous_state_persisted": False,
        },
    )
    save_snapshot(tmp_path / "portfolio.json", _snapshot("999"))

    recovered = _provider(tmp_path)
    assert recovered.acquisition_mode == MODE_LIVE_API
    assert load_json_state(tmp_path / "comdirect-acquisition.json") is None
    assert not (tmp_path / "comdirect-acquisition-pending.json").exists()
    assert not (tmp_path / "portfolio.json").exists()
