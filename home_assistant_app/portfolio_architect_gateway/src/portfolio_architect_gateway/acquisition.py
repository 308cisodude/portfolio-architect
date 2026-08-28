"""Explicit Comdirect acquisition-mode arbitration."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Callable, Final

from .acquisition_control import (
    CHANGE_REASON_OPERATOR,
    METHOD_NOT_READY,
    METHOD_READY,
    AcquisitionControl,
    AcquisitionMethod,
    method_inventory,
)
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
PENDING_STATE_FILE_NAME: Final = "comdirect-acquisition-pending.json"
HOLDINGS_STATE_FILE_NAME: Final = "comdirect-csv-holdings.json"


class ComdirectAcquisitionProvider:
    """Expose exactly one active Comdirect acquisition method to the common server."""

    def __init__(
        self,
        live_client: ComdirectClient,
        data_directory: Path,
        cash_policy_file: Path,
        canonical_snapshot_file: Path | None = None,
    ) -> None:
        self.live_client = live_client
        self._data_directory = Path(data_directory)
        self._cash_policy_file = Path(cash_policy_file)
        self._mode_file = self._data_directory / MODE_STATE_FILE_NAME
        self._pending_file = self._data_directory / PENDING_STATE_FILE_NAME
        self._holdings_file = self._data_directory / HOLDINGS_STATE_FILE_NAME
        self._cash_file = self._data_directory / "comdirect-csv-cash.json"
        self._canonical_snapshot_file = (
            Path(canonical_snapshot_file)
            if canonical_snapshot_file is not None
            else self._data_directory / "portfolio.json"
        )
        self._lock = threading.RLock()
        self._recover_interrupted_activation()
        self._state_document = self._load_state_document()
        self._state_persisted = self._mode_file.is_file()
        self._mode = str(self._state_document["mode"])

    @property
    def provider_id(self) -> str:
        return "comdirect"

    @property
    def acquisition_mode(self) -> str:
        with self._lock:
            return self._mode

    @property
    def acquisition_control(self) -> AcquisitionControl:
        """Return bounded local readiness and the last explicit operator switch."""
        with self._lock:
            active = self._mode
            holdings = self.holdings_snapshot()
            cash = self.cash_snapshot()
            # An already-active legacy CSV installation remains valid with holdings-only
            # evidence.  Switching *to* CSV from another method requires the complete
            # current static path (holdings + cash), matching the v1.53 control-plane UX.
            csv_ready = active == MODE_CSV or (holdings is not None and cash is not None)
            live_ready = active == MODE_LIVE_API or bool(getattr(self.live_client, "session_state_available", False))
            previous = self._state_document.get("previous_mode")
            changed_at_raw = self._state_document.get("last_method_change_at")
            changed_at = (
                datetime.fromisoformat(str(changed_at_raw).replace("Z", "+00:00"))
                if changed_at_raw is not None
                else None
            )
            reason = self._state_document.get("last_method_change_reason")
            return AcquisitionControl(
                active_method=active,
                methods=method_inventory(
                    AcquisitionMethod(
                        MODE_LIVE_API,
                        METHOD_READY if live_ready else METHOD_NOT_READY,
                        active == MODE_LIVE_API,
                        live_ready,
                    ),
                    AcquisitionMethod(
                        MODE_CSV,
                        METHOD_READY if csv_ready else METHOD_NOT_READY,
                        active == MODE_CSV,
                        csv_ready,
                    ),
                ),
                previous_method=str(previous) if previous is not None else None,
                last_method_change_at=changed_at,
                last_method_change_reason=str(reason) if reason is not None else None,
            )

    @contextmanager
    def migration_guard(self):
        """Hold acquisition authority stable while long-lived state is exported."""
        with self._lock:
            if self._pending_file.exists():
                raise ConfigurationError(
                    "A Comdirect acquisition switch is still pending"
                )
            yield

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
        with self._lock:
            if self._mode == MODE_LIVE_API:
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
        with self._lock:
            if snapshot is None:
                self._holdings_file.unlink(missing_ok=True)
                return
            save_snapshot(self._holdings_file, _holdings_only(snapshot))

    def persist_cash(self, snapshot: ComdirectCashSnapshot | None) -> None:
        with self._lock:
            save_cash_snapshot(self._cash_file, snapshot)

    def holdings_snapshot(self) -> PortfolioSnapshot | None:
        """Return staged holdings evidence without letting corruption affect another active method."""
        with self._lock:
            try:
                return load_snapshot(self._holdings_file)
            except ProtocolError:
                return None

    def cash_snapshot(self) -> ComdirectCashSnapshot | None:
        """Return staged cash evidence without letting corruption affect another active method."""
        with self._lock:
            try:
                return load_cash_snapshot(self._cash_file)
            except ProtocolError:
                return None

    def activate_mode(self, mode: str, publish: Callable[[], bool]) -> None:
        """Crash-safely validate, switch, and publish one explicit acquisition method.

        A private pending marker records the exact pre-switch control state before the
        candidate mode is persisted.  The acquisition lock spans validation, state
        transition and canonical publication, so concurrent refreshes cannot observe
        an intermediate mode.  If the process stops mid-switch, startup recovery rolls
        the control plane back to the recorded prior state and discards the ambiguous
        cached canonical snapshot before the Gateway server can load it.
        """
        if mode not in SUPPORTED_MODES:
            raise ValueError("Unsupported Comdirect acquisition mode")
        with self._lock:
            if self._pending_file.exists():
                raise ConfigurationError(
                    "A previous Comdirect acquisition activation requires restart recovery"
                )
            if mode == self._mode:
                return
            self._validate_candidate(mode)
            previous_document = dict(self._state_document)
            previous_persisted = self._state_persisted
            previous_mode = self._mode
            changed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            candidate_document = {
                "schema_version": 2,
                "mode": mode,
                "previous_mode": previous_mode,
                "last_method_change_at": changed_at,
                "last_method_change_reason": CHANGE_REASON_OPERATOR,
            }
            self._write_pending_activation(previous_document, previous_persisted)
            try:
                save_json_state(self._mode_file, candidate_document)
                self._state_document = candidate_document
                self._state_persisted = True
                self._mode = mode
                if not publish():
                    raise ValueError(
                        "Requested Comdirect acquisition mode could not be activated"
                    )
                self._clear_pending_activation()
                return
            except Exception:
                self._state_document = previous_document
                self._state_persisted = previous_persisted
                self._mode = previous_mode
                rollback_state_ok = self._restore_persisted_state(
                    previous_document, previous_persisted
                )
                rollback_publish_ok = False
                try:
                    rollback_publish_ok = bool(publish())
                except Exception:
                    rollback_publish_ok = False
                if rollback_state_ok and rollback_publish_ok:
                    try:
                        self._clear_pending_activation()
                    except ProtocolError:
                        # Leaving the marker is fail-safe: startup recovery will discard
                        # the cached snapshot and restore the same previous state again.
                        pass
                raise

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

    def _validate_candidate(self, mode: str) -> None:
        if mode == MODE_LIVE_API:
            # A real read is the activation gate.  Persisted local session state is only
            # a readiness hint; stale/rejected OAuth cannot become authoritative.
            self.live_client.fetch_snapshot()
            return
        if self.holdings_snapshot() is None or self.cash_snapshot() is None:
            raise ConfigurationError(
                "Comdirect CSV activation requires both holdings and cash evidence"
            )
        self.csv_snapshot()

    def _write_pending_activation(
        self, previous_document: dict[str, object], previous_persisted: bool
    ) -> None:
        save_json_state(
            self._pending_file,
            {
                "schema_version": 1,
                "previous_state": previous_document,
                "previous_state_persisted": previous_persisted,
            },
        )

    def _clear_pending_activation(self) -> None:
        try:
            self._pending_file.unlink(missing_ok=True)
        except OSError as err:
            raise ProtocolError("Cannot finalize Comdirect acquisition activation") from err

    def _restore_persisted_state(
        self, previous_document: dict[str, object], previous_persisted: bool
    ) -> bool:
        try:
            if previous_persisted:
                save_json_state(self._mode_file, previous_document)
            else:
                self._mode_file.unlink(missing_ok=True)
        except (OSError, ProtocolError):
            return False
        return True

    def _recover_interrupted_activation(self) -> None:
        pending = load_json_state(self._pending_file)
        if pending is None:
            return
        if set(pending) != {
            "schema_version",
            "previous_state",
            "previous_state_persisted",
        } or pending.get("schema_version") != 1:
            raise ProtocolError("Stored Comdirect acquisition activation marker is invalid")
        previous = pending.get("previous_state")
        previous_persisted = pending.get("previous_state_persisted")
        if not isinstance(previous, dict) or not isinstance(previous_persisted, bool):
            raise ProtocolError("Stored Comdirect acquisition activation marker is invalid")
        previous_document = self._validate_state_document(previous)
        try:
            if previous_persisted:
                save_json_state(self._mode_file, previous_document)
            else:
                self._mode_file.unlink(missing_ok=True)
            # The canonical snapshot may have been replaced by the candidate immediately
            # before the process stopped.  Remove it before GatewayState is constructed;
            # the normal startup refresh will repopulate the restored authoritative mode.
            self._canonical_snapshot_file.unlink(missing_ok=True)
            self._pending_file.unlink()
        except OSError as err:
            raise ProtocolError(
                "Cannot recover interrupted Comdirect acquisition activation"
            ) from err

    def _load_state_document(self) -> dict[str, object]:
        raw = load_json_state(self._mode_file)
        if raw is None:
            return {"schema_version": 1, "mode": MODE_LIVE_API}
        return self._validate_state_document(raw)

    @staticmethod
    def _validate_state_document(raw: dict[str, object]) -> dict[str, object]:
        schema = raw.get("schema_version")
        if schema == 1:
            if set(raw) != {"schema_version", "mode"}:
                raise ProtocolError("Stored Comdirect acquisition mode has an unexpected schema")
        elif schema == 2:
            if set(raw) != {
                "schema_version",
                "mode",
                "previous_mode",
                "last_method_change_at",
                "last_method_change_reason",
            }:
                raise ProtocolError("Stored Comdirect acquisition mode has an unexpected schema")
            previous = raw.get("previous_mode")
            if previous not in SUPPORTED_MODES or previous == raw.get("mode"):
                raise ProtocolError("Stored Comdirect previous acquisition mode is invalid")
            changed_at = raw.get("last_method_change_at")
            if not isinstance(changed_at, str):
                raise ProtocolError("Stored Comdirect acquisition change time is invalid")
            try:
                parsed = datetime.fromisoformat(changed_at.replace("Z", "+00:00"))
            except ValueError as err:
                raise ProtocolError("Stored Comdirect acquisition change time is invalid") from err
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ProtocolError("Stored Comdirect acquisition change time is invalid")
            if raw.get("last_method_change_reason") != CHANGE_REASON_OPERATOR:
                raise ProtocolError("Stored Comdirect acquisition change reason is invalid")
        else:
            raise ProtocolError("Stored Comdirect acquisition mode has an unexpected schema")
        mode = raw.get("mode")
        if mode not in SUPPORTED_MODES:
            raise ProtocolError("Stored Comdirect acquisition mode is invalid")
        return dict(raw)



def _holdings_only(snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
    return validate_snapshot(
        PortfolioSnapshot(generated_at=snapshot.generated_at, positions=snapshot.positions)
    )
