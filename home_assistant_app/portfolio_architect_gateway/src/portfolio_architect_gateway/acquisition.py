"""Explicit Comdirect acquisition-mode arbitration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Final

from .cash_policy import load_investment_cash_policy
from .comdirect import ComdirectClient, SESSION_MAINTENANCE_INTERVAL_SECONDS
from .comdirect_cash_csv import ComdirectCashSnapshot, load_cash_snapshot, save_cash_snapshot
from .errors import ConfigurationError, ProtocolError
from .models import PortfolioSnapshot, validate_snapshot
from .store import load_json_state, load_snapshot, save_json_state, save_snapshot

MODE_LIVE_API: Final = "live_api"
MODE_CSV: Final = "csv"
SUPPORTED_MODES: Final = frozenset({MODE_LIVE_API, MODE_CSV})
MODE_STATE_FILE_NAME: Final = "comdirect-acquisition.json"
HOLDINGS_STATE_FILE_NAME: Final = "comdirect-csv-holdings.json"


class ComdirectAcquisitionProvider:
    """Expose exactly one active Comdirect acquisition method to the common server."""

    def __init__(self, live_client: ComdirectClient, data_directory: Path, cash_policy_file: Path) -> None:
        self.live_client = live_client
        self._data_directory = Path(data_directory)
        self._cash_policy_file = Path(cash_policy_file)
        self._mode_file = self._data_directory / MODE_STATE_FILE_NAME
        self._holdings_file = self._data_directory / HOLDINGS_STATE_FILE_NAME
        self._cash_file = self._data_directory / "comdirect-csv-cash.json"
        self._lock = threading.RLock()
        self._mode = self._load_mode()

    @property
    def provider_id(self) -> str:
        return "comdirect"

    @property
    def acquisition_mode(self) -> str:
        with self._lock:
            return self._mode

    @property
    def poll_interval_seconds(self) -> int:
        return self.live_client.poll_interval_seconds

    @property
    def holdings_file(self) -> Path:
        return self._holdings_file

    @property
    def cash_file(self) -> Path:
        return self._cash_file

    def fetch_snapshot(self) -> PortfolioSnapshot:
        """Fetch only from the explicitly active method; never cross-fallback."""
        if self.acquisition_mode == MODE_LIVE_API:
            return self.live_client.fetch_snapshot()
        return self.csv_snapshot()

    def csv_snapshot(self) -> PortfolioSnapshot:
        holdings = load_snapshot(self._holdings_file)
        if holdings is None:
            raise ConfigurationError("No Comdirect depot CSV has been imported")
        cash = load_cash_snapshot(self._cash_file)
        if cash is None:
            return _holdings_only(holdings)
        policy = load_investment_cash_policy(self._cash_policy_file)
        investment_cash = cash.investment_cash(policy)
        return validate_snapshot(
            PortfolioSnapshot(
                generated_at=holdings.generated_at,
                positions=holdings.positions,
                investment_reserve_eur=investment_cash.authorized_eur,
                investment_reserve_as_of=investment_cash.as_of,
                investment_cash=investment_cash,
            )
        )

    def persist_holdings(self, snapshot: PortfolioSnapshot | None) -> None:
        if snapshot is None:
            self._holdings_file.unlink(missing_ok=True)
            return
        save_snapshot(self._holdings_file, _holdings_only(snapshot))

    def persist_cash(self, snapshot: ComdirectCashSnapshot | None) -> None:
        save_cash_snapshot(self._cash_file, snapshot)

    def holdings_snapshot(self) -> PortfolioSnapshot | None:
        return load_snapshot(self._holdings_file)

    def cash_snapshot(self) -> ComdirectCashSnapshot | None:
        return load_cash_snapshot(self._cash_file)

    def set_mode(self, mode: str) -> None:
        if mode not in SUPPORTED_MODES:
            raise ValueError("Unsupported Comdirect acquisition mode")
        with self._lock:
            if mode == self._mode:
                return
            # Validate the requested source before persisting the switch. The live
            # branch performs an actual read; the CSV branch requires a valid local snapshot.
            if mode == MODE_LIVE_API:
                self.live_client.fetch_snapshot()
            else:
                self.csv_snapshot()
            save_json_state(self._mode_file, {"schema_version": 1, "mode": mode})
            self._mode = mode

    def restore_mode(self, mode: str) -> None:
        """Restore a previously active validated mode after activation failure."""
        if mode not in SUPPORTED_MODES:
            raise ValueError("Unsupported Comdirect acquisition mode")
        with self._lock:
            save_json_state(self._mode_file, {"schema_version": 1, "mode": mode})
            self._mode = mode

    def run_session_maintenance_loop(
        self,
        stop_event: threading.Event,
        *,
        interval_seconds: int = SESSION_MAINTENANCE_INTERVAL_SECONDS,
    ) -> None:
        """Maintain OAuth only while live_api is active; CSV mode makes no API calls."""
        if not 60 <= interval_seconds <= 900:
            raise ValueError("Comdirect session-maintenance interval is invalid")
        while not stop_event.wait(interval_seconds):
            if self.acquisition_mode != MODE_LIVE_API:
                continue
            self.live_client.run_session_maintenance_iteration()

    def _load_mode(self) -> str:
        raw = load_json_state(self._mode_file)
        if raw is None:
            return MODE_LIVE_API
        if set(raw) != {"schema_version", "mode"} or raw.get("schema_version") != 1:
            raise ProtocolError("Stored Comdirect acquisition mode has an unexpected schema")
        mode = raw.get("mode")
        if mode not in SUPPORTED_MODES:
            raise ProtocolError("Stored Comdirect acquisition mode is invalid")
        return str(mode)


def _holdings_only(snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
    return validate_snapshot(
        PortfolioSnapshot(generated_at=snapshot.generated_at, positions=snapshot.positions)
    )
