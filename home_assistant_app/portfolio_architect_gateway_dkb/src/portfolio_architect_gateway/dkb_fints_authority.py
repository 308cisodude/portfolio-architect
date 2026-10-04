"""Explicit DKB CSV/FinTS authority with private, bounded FinTS provenance."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import hmac
import threading
from typing import Any, Callable, Final

from .acquisition_control import (
    AUTHORITY_ACTIVE_METHOD, CAPABILITY_CASH, CAPABILITY_HOLDINGS,
    CHANGE_REASON_OPERATOR, METHOD_NOT_READY, METHOD_READY,
    AcquisitionControl, AcquisitionMethod, capability, method_inventory,
)
from .dkb_account_selection import SelectedAccount, load as load_selected_account
from .dkb_cash_csv import DkbCashSnapshot
from .dkb_cash_research import validate_shadow as validate_cash_shadow
from .dkb_csv import DkbCsvProvider
from .dkb_shadow import validate_shadow as validate_holdings_shadow
from .errors import ConfigurationError, ProtocolError
from .models import PortfolioSnapshot, Position, canonical_decimal, canonical_signed_decimal, validate_snapshot
from .store import load_json_state, load_snapshot, save_json_state, save_snapshot

MODE_CSV: Final = "csv"
MODE_FINTS: Final = "fints"
MAX_FINTS_AGE: Final = timedelta(days=14)
EVIDENCE_FILE_NAME: Final = "dkb-fints-authority-evidence.json"
FINTS_CANONICAL_FILE_NAME: Final = "dkb-fints-canonical.json"
CSV_HOLDINGS_FILE_NAME: Final = "dkb-csv-holdings.json"
MODE_FILE_NAME: Final = "dkb-acquisition.json"
PENDING_FILE_NAME: Final = "dkb-acquisition-pending.json"


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise ConfigurationError("DKB FinTS evidence timestamp is invalid")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as err:
        raise ConfigurationError("DKB FinTS evidence timestamp is invalid") from err
    if result.tzinfo is None or result.utcoffset() is None:
        raise ConfigurationError("DKB FinTS evidence timestamp lacks a timezone")
    return result.astimezone(timezone.utc)


def stage_evidence(path: Path, selected: SelectedAccount, holdings: dict[str, Any],
                   cash: dict[str, Any]) -> None:
    """Stage only complete normalized facts from a single combined manual read."""
    validate_holdings_shadow(holdings)
    validate_cash_shadow(cash)
    if not holdings["positions"]:
        raise ConfigurationError("DKB FinTS holdings are empty")
    document = {
        "schema_version": 1,
        "account_binding": selected.binding,
        "user_binding": selected.user_binding,
        "holdings": holdings,
        "cash": cash,
    }
    # Apply all production validators before a private file can be replaced.
    _snapshot(document, selected, None, datetime.now(timezone.utc))
    save_json_state(path, document)


def _snapshot(raw: Any, selected: SelectedAccount, provider: DkbCsvProvider | None,
              now: datetime) -> PortfolioSnapshot:
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version", "account_binding", "user_binding", "holdings", "cash"
    } or type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ConfigurationError("DKB FinTS authority evidence has an invalid schema")
    if (not isinstance(raw["account_binding"], str) or not isinstance(raw["user_binding"], str)
            or not hmac.compare_digest(raw["account_binding"], selected.binding)
            or not hmac.compare_digest(raw["user_binding"], selected.user_binding)):
        raise ConfigurationError("DKB FinTS account binding is unavailable")
    try:
        holdings = validate_holdings_shadow(raw["holdings"], now)
        cash = validate_cash_shadow(raw["cash"], now)
    except (ValueError, TypeError) as err:
        raise ConfigurationError("DKB FinTS authority evidence is invalid") from err
    holdings_at = _timestamp(holdings["observed_at"])
    cash_at = _timestamp(cash.observed_at)
    current = now.astimezone(timezone.utc)
    if any(not timedelta(0) <= current - instant < MAX_FINTS_AGE
           for instant in (holdings_at, cash_at)):
        raise ConfigurationError("DKB FinTS authority evidence is older than 14 days")
    # A bank balance date can precede the observation, but cannot justify an
    # observation of an arbitrarily old booked balance.
    if date.fromisoformat(cash.bank_date) < (current - MAX_FINTS_AGE).date():
        raise ConfigurationError("DKB FinTS bank balance date is too old")
    positions: list[Position] = []
    for row in holdings["positions"]:
        if row["currency"] != "EUR":
            raise ConfigurationError("DKB FinTS position is not denominated in EUR")
        try:
            quantity = Decimal(row["quantity"])
            value = Decimal(row["total_value"])
            canonical_decimal(quantity)
            canonical_decimal(value)
        except (ValueError, ProtocolError) as err:
            raise ConfigurationError("DKB FinTS position cannot be represented exactly") from err
        isin = row["isin"]
        positions.append(Position(isin, f"ISIN {isin}", value, quantity, isin, "other"))
    if not positions:
        raise ConfigurationError("DKB FinTS holdings are empty")
    balance = Decimal(cash.amount)
    try:
        canonical_signed_decimal(balance)
    except ProtocolError as err:
        raise ConfigurationError("DKB FinTS cash cannot be represented exactly") from err
    policy = provider.investment_cash_policy() if provider is not None else None
    investment_cash = DkbCashSnapshot(balance, cash_at, cash_at).investment_cash(policy)
    try:
        return validate_snapshot(PortfolioSnapshot(
            generated_at=holdings_at,
            positions=tuple(positions),
            investment_reserve_eur=investment_cash.authorized_eur,
            investment_reserve_as_of=cash_at,
            investment_cash=investment_cash,
        ))
    except ProtocolError as err:
        raise ConfigurationError("DKB FinTS canonical evidence is invalid") from err


class DkbAcquisitionProvider(DkbCsvProvider):
    """Select one complete source explicitly; neither mode calls the bank on poll."""

    def __init__(self, snapshot_file: Path) -> None:
        self._lock = threading.RLock()
        self._data_directory = Path(snapshot_file).parent
        self._mode_file = self._data_directory / MODE_FILE_NAME
        self._pending_file = self._data_directory / PENDING_FILE_NAME
        self.evidence_file = self._data_directory / EVIDENCE_FILE_NAME
        self._fints_canonical_file = self._data_directory / FINTS_CANONICAL_FILE_NAME
        self._csv_holdings_file = self._data_directory / CSV_HOLDINGS_FILE_NAME
        self._selection_file = self._data_directory / "dkb-fints-investment-account.json"
        self._binding_key_file = self._data_directory / "dkb-fints-account-binding-key"
        self._recover_interrupted_activation(Path(snapshot_file))
        self._state = self._load_state()
        self._mode = str(self._state["mode"])
        super().__init__(snapshot_file)
        # Before this release, the canonical file held CSV evidence. Capture it
        # once while still in CSV mode. Under FinTS authority it must never be
        # mistaken for independent CSV evidence after a restart.
        independent = load_snapshot(self._csv_holdings_file)
        if independent is not None:
            super().replace_snapshot(independent)
        elif self._mode == MODE_CSV and self.holdings_snapshot is not None:
            save_snapshot(self._csv_holdings_file, self.holdings_snapshot)
        else:
            super().replace_snapshot(None)

    @property
    def canonical_snapshot_file(self) -> Path:
        with self._lock:
            return self._fints_canonical_file if self._mode == MODE_FINTS else self._snapshot_file

    def replace_snapshot(self, snapshot: PortfolioSnapshot | None) -> None:
        """Persist independent CSV holdings even while FinTS is active."""
        with self._lock:
            super().replace_snapshot(snapshot)
            if self.holdings_snapshot is None:
                self._csv_holdings_file.unlink(missing_ok=True)
            else:
                save_snapshot(self._csv_holdings_file, self.holdings_snapshot)

    @property
    def acquisition_mode(self) -> str:
        with self._lock:
            return self._mode

    @contextmanager
    def selection_guard(self):
        """Keep authority stable while changing the bound account identity."""
        with self._lock:
            if self._mode == MODE_FINTS:
                raise ValueError("Switch DKB authority to CSV before changing account identity")
            yield

    @property
    def acquisition_control(self) -> AcquisitionControl:
        with self._lock:
            mode = self._mode
            ready = self._fints_ready()
            changed_at = self._state.get("last_method_change_at")
            return AcquisitionControl(
                active_method=mode,
                methods=method_inventory(
                    AcquisitionMethod(MODE_CSV, METHOD_READY, mode == MODE_CSV,
                                      self.holdings_snapshot is not None and self.cash_snapshot is not None),
                    AcquisitionMethod(MODE_FINTS, METHOD_READY if ready or mode == MODE_FINTS else METHOD_NOT_READY,
                                      mode == MODE_FINTS, ready),
                ),
                previous_method=self._state.get("previous_mode"),
                last_method_change_at=_timestamp(changed_at) if changed_at is not None else None,
                last_method_change_reason=self._state.get("last_method_change_reason"),
                capabilities=(
                    capability(CAPABILITY_HOLDINGS, mode, MODE_CSV, MODE_FINTS,
                               authority_reason=AUTHORITY_ACTIVE_METHOD),
                    capability(CAPABILITY_CASH, mode, MODE_CSV, MODE_FINTS,
                               authority_reason=AUTHORITY_ACTIVE_METHOD),
                ),
            )

    def _fints_snapshot(self) -> PortfolioSnapshot:
        try:
            selected = load_selected_account(self._selection_file, self._binding_key_file)
            raw = load_json_state(self.evidence_file)
            if selected is None or raw is None:
                raise ConfigurationError("DKB FinTS selection or complete evidence is missing")
            return _snapshot(raw, selected, self, datetime.now(timezone.utc))
        except (OSError, ProtocolError, ValueError) as err:
            raise ConfigurationError("DKB FinTS private evidence is unavailable") from err

    def _fints_ready(self) -> bool:
        try:
            self._fints_snapshot()
        except ConfigurationError:
            return False
        return True

    def fetch_snapshot(self) -> PortfolioSnapshot:
        with self._lock:
            return self._fints_snapshot() if self._mode == MODE_FINTS else super().fetch_snapshot()

    def snapshot_is_current(self, snapshot: PortfolioSnapshot) -> bool:
        """Guard cached publications against expiry, switches and damaged state."""
        with self._lock:
            try:
                return snapshot.to_bytes() == self.fetch_snapshot().to_bytes()
            except (ConfigurationError, ProtocolError, OSError):
                return False

    def activate_mode(self, mode: str, publish: Callable[[], bool]) -> None:
        if mode not in {MODE_CSV, MODE_FINTS}:
            raise ValueError("Unsupported DKB acquisition mode")
        with self._lock:
            if self._pending_file.exists():
                raise ConfigurationError("A DKB acquisition switch requires restart recovery")
            if mode == self._mode:
                return
            if mode == MODE_FINTS:
                self._fints_snapshot()
            elif self.holdings_snapshot is None or self.cash_snapshot is None:
                raise ConfigurationError("DKB CSV activation requires holdings and cash")
            previous_state = dict(self._state)
            previous_mode = self._mode
            candidate = {
                "schema_version": 2, "mode": mode, "previous_mode": previous_mode,
                "last_method_change_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "last_method_change_reason": CHANGE_REASON_OPERATOR,
            }
            save_json_state(self._pending_file, {"schema_version": 1, "previous_state": previous_state,
                                                 "previous_state_persisted": self._mode_file.exists()})
            try:
                save_json_state(self._mode_file, candidate)
                self._state, self._mode = candidate, mode
                if not publish():
                    raise ConfigurationError("DKB acquisition switch could not be published")
                self._pending_file.unlink()
            except Exception:
                self._state, self._mode = previous_state, previous_mode
                try:
                    if self._pending_file.exists():
                        pending = load_json_state(self._pending_file)
                        if pending and pending["previous_state_persisted"]:
                            save_json_state(self._mode_file, previous_state)
                        else:
                            self._mode_file.unlink(missing_ok=True)
                        if publish():
                            self._pending_file.unlink(missing_ok=True)
                except Exception:
                    # Keep the pending marker; startup will remove ambiguous cache.
                    pass
                raise

    def _load_state(self) -> dict[str, Any]:
        try:
            raw = load_json_state(self._mode_file)
        except ProtocolError as err:
            raise ConfigurationError("Stored DKB acquisition mode is invalid") from err
        if raw is None:
            return {"schema_version": 1, "mode": MODE_CSV}
        if not isinstance(raw, dict) or raw.get("mode") not in {MODE_CSV, MODE_FINTS}:
            raise ConfigurationError("Stored DKB acquisition mode is invalid")
        if raw.get("schema_version") == 1:
            if set(raw) != {"schema_version", "mode"}:
                raise ConfigurationError("Stored DKB acquisition mode is invalid")
        elif raw.get("schema_version") == 2:
            if set(raw) != {"schema_version", "mode", "previous_mode", "last_method_change_at",
                            "last_method_change_reason"} or raw["previous_mode"] not in {MODE_CSV, MODE_FINTS} or raw["previous_mode"] == raw["mode"] or raw["last_method_change_reason"] != CHANGE_REASON_OPERATOR:
                raise ConfigurationError("Stored DKB acquisition history is invalid")
            _timestamp(raw["last_method_change_at"])
        else:
            raise ConfigurationError("Stored DKB acquisition mode version is invalid")
        return raw

    def _recover_interrupted_activation(self, snapshot_file: Path) -> None:
        try:
            pending = load_json_state(self._pending_file)
        except ProtocolError as err:
            raise ConfigurationError("Stored DKB acquisition marker is invalid") from err
        if pending is None:
            return
        if not isinstance(pending, dict) or set(pending) != {
            "schema_version", "previous_state", "previous_state_persisted"
        } or pending["schema_version"] != 1 or type(pending["previous_state_persisted"]) is not bool:
            raise ConfigurationError("Stored DKB acquisition marker is invalid")
        previous = pending["previous_state"]
        if not isinstance(previous, dict) or previous.get("mode") not in {MODE_CSV, MODE_FINTS}:
            raise ConfigurationError("Stored DKB acquisition marker is invalid")
        if pending["previous_state_persisted"]:
            save_json_state(self._mode_file, previous)
        else:
            self._mode_file.unlink(missing_ok=True)
        snapshot_file.unlink(missing_ok=True)
        (self._data_directory / FINTS_CANONICAL_FILE_NAME).unlink(missing_ok=True)
        self._pending_file.unlink()
